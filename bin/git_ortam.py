#!/usr/bin/env python3
"""Git alt süreçlerinin ortamı — miras alınan depo yönlendirmesi sökülür.

Neden: git bir kancayı koştururken depo yönlendirmesini ORTAMA koyar; linked
worktree'den push'ta GIT_DIR=<ana>/.git/worktrees/<ad> olur. Bu miras her
alt sürece geçer ve `git -C <dizin>` / `cwd=<dizin>` ile ADLANDIRILAN depoyu
sessizce ezer — GIT_DIR varken keşif hiç yapılmaz.

2026-10-15, OICommand: worktree'den push → kancanın koştuğu testler geçici
dizin yerine gerçek depoda `git init` + `git config user.*` yaptı. Paylaşılan
.git/config'e `core.bare = true` ve `[user] t <t@t.t>` yazıldı, ana checkout
"must be run in a work tree" ile kilitlendi. Kancadaki `unset` yalnız push
yolunu kapatır; validate.py'yi başka bir miras ortamda koşan aynı hasarı verir.

Kural: kernel'de depoyu ADLANDIRAN (-C / cwd) her git alt süreci ortamını
`temiz_ortam()`dan alır. Bekçisi `yem_depo`: validate.py test süitini yem bir
depoya yönlendirilmiş ortamda koşar; bu kuralı unutan tek çağrı yemi değiştirir
ve kapı kırmızı verir.
"""
import contextlib
import hashlib
import os
import subprocess
import tempfile
import types

# `git rev-parse --local-env-vars` — git'in "başka depoya geçerken sökülmeli"
# dediği küme (git-submodule de bunu söker) + kancanın ayrıca söktükleri
# (NAMESPACE, QUARANTINE_PATH). Statik: her çağrıda git'e sormak bir alt süreç
# daha demek. Git yeni bir değişken eklerse tests/test_git_ortam.py kırmızı verir.
YEREL_DEGISKENLER = (
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_CONFIG", "GIT_CONFIG_PARAMETERS",
    "GIT_CONFIG_COUNT", "GIT_OBJECT_DIRECTORY", "GIT_DIR", "GIT_WORK_TREE",
    "GIT_IMPLICIT_WORK_TREE", "GIT_GRAFT_FILE", "GIT_INDEX_FILE",
    "GIT_NO_REPLACE_OBJECTS", "GIT_REPLACE_REF_BASE", "GIT_PREFIX",
    "GIT_SHALLOW_FILE", "GIT_COMMON_DIR",
    "GIT_NAMESPACE", "GIT_QUARANTINE_PATH",
)


def temiz_ortam(taban=None):
    """`taban`ın (varsayılan os.environ) depo yönlendirmesi sökülmüş kopyası."""
    ortam = dict(os.environ if taban is None else taban)
    for ad in YEREL_DEGISKENLER:
        ortam.pop(ad, None)
    return ortam


def _iz(git_dizini):
    """{göreli yol: içerik özeti} — yemin .git'inde değişeni adıyla söylemek için."""
    iz = {}
    for kok, _dizinler, dosyalar in os.walk(git_dizini):
        for ad in dosyalar:
            yol = os.path.join(kok, ad)
            if not os.path.isfile(yol):   # soket/FIFO (fsmonitor) açılamaz
                continue
            with open(yol, "rb") as fh:
                iz[os.path.relpath(yol, git_dizini)] = hashlib.sha256(
                    fh.read()).hexdigest()
    return iz


@contextlib.contextmanager
def yem_depo():
    """Olayın birebir ortamı: GIT_DIR, yemin linked worktree'sine işaret eder.

    `yem.ortam` git'in worktree'den push'ta kancaya verdiğinin aynısıdır.
    Blok bitince `yem.degisen`, yemin .git'inde değişen yolları listeler — boş
    değilse bloktaki bir git çağrısı ortamı temizlemeden koşmuştur.
    """
    with tempfile.TemporaryDirectory() as td:
        ana = os.path.join(td, "yem")
        temiz = temiz_ortam()
        # Kurulum kullanıcının global/sistem ayarını GÖRMEZ: commit.gpgsign
        # imza ister (128 ya da her push'ta istem), core.hooksPath kancasını
        # koşar. fsmonitor yemin KENDİ ayarında kapalı: sızan çağrı global
        # ayarla gelse de .git'e daemon soketi açmasın.
        kurulum = dict(temiz, GIT_CONFIG_GLOBAL=os.devnull,
                       GIT_CONFIG_NOSYSTEM="1")
        for arg in (["init", "-q", "-b", "main", ana],
                    ["-C", ana, "config", "core.fsmonitor", "false"],
                    ["-C", ana, "commit", "-q", "--allow-empty", "-m", "yem"],
                    ["-C", ana, "worktree", "add", "-q", "-b", "yem-dal",
                     os.path.join(td, "wt")]):
            subprocess.run(["git", "-c", "user.name=yem",
                            "-c", "user.email=yem@yem.invalid", *arg],
                           check=True, capture_output=True, env=kurulum,
                           timeout=60)
        git_dizini = os.path.join(ana, ".git")
        yem = types.SimpleNamespace(
            ortam=dict(temiz, GIT_DIR=os.path.join(git_dizini, "worktrees", "wt")),
            git_dizini=git_dizini, degisen=[])
        once = _iz(git_dizini)
        try:
            yield yem
        finally:
            sonra = _iz(git_dizini)
            yem.degisen = sorted(y for y in once.keys() | sonra.keys()
                                 if once.get(y) != sonra.get(y))


def yemde_kos(argv, cwd):
    """`argv`ı yeme yönlendirilmiş ortamda koşar → (süreç, yemde değişenler)."""
    with yem_depo() as yem:
        p = subprocess.run(argv, capture_output=True, text=True, cwd=cwd,
                           env=yem.ortam)
    return p, yem.degisen
