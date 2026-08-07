#!/usr/bin/env python3
"""Motor (kernel) dosyalarının TEK tanımı + kanonik↔proje karşılaştırması.

Neden tek tanım: liste iki yerde yaşıyordu (auras-init.sh içi + validate.py
bekçisi) ve üçüncüsü geri-taşımada gerekiyordu. Üç kopya = sürüklenme; tek
tanım + bekçi (validate.py test_onboarding_parity) ile sürüklenme yapısal
olarak imkânsızlaşır.

Neden sınıflandırma git geçmişine bakar: `.kernel-manifest.json`ın "el
değmemiş" demesi YETMEZ. 2026-08-05 bulgusu: 4cast'te manifest projenin kendi
içeriğini kaydetmişti; /auras `bin/kapi.py`'deki yerel düzeltmeyi "temiz" sanıp
sessizce ezecekti. Güvenilir ayraç şudur — hedefin içeriği kanonik geçmişte
HİÇ görülmediyse o yerel iştir; ezilemez, yukarı taşınır.

Kullanım (kütüphane):
    import kernel_dosyalari as kd
    for rel, sinif in kd.karsilastir(kanonik, hedef): ...
"""
import hashlib
import os
import re
import subprocess

# Motorun dosyaları — projenin değil. Her /auras koşumunda senkronlanır.
MOTOR = [
    "bin/validate.py", "bin/make_evidence.py", "bin/route.py",
    "bin/memory_hygiene.py", "bin/run_event.py", "bin/durum.py",
    "bin/kapi.py", "bin/araclar.py", "bin/kernel_dosyalari.py",
    "bin/kalite.py",
    "bin/auras_geri.py", "bin/incele.py", "bin/surec.py",
    "bin/codex-review.sh",
    "bin/install-hooks.sh", "bin/hooks/pre-push",
    "schemas/evidence.schema.json",
    ".github/workflows/evidence.yml",
    ".github/ISSUE_TEMPLATE/work-contract.yml",
    ".agents/routing.yml",
    # Motorun kendi kapsamı hakkındaki beyanı. Her projeye gitmeli: kullanıcı
    # hangi aşamada kapı OLMADIĞINI bilmeden korunduğunu sanır. Ayrıca
    # tests/test_evidence_workflow.py bu belgeyi şart koşuyor ve o test her
    # projeye taşınıyor — belge gitmezse kurulum kırmızı başlar (4Flow, 2026-08-07).
    "docs/yasam-dongusu-kapsami.md",
]
# Dizin olarak senkronlananlar (içerik tamamen motorun)
MOTOR_DIZIN = [".agents/skills", ".agents/capability-profiles", "tests",
               ".claude/rules"]

SINIFLAR = ("yok", "ayni", "geride", "yerel")

# Motorla senkronlanmaz ama kurulumdan SONRA projede bulunur:
# bir kez yazılan proje dosyaları (copy_new) ve kurucunun ürettikleri.
PROJE_DOSYASI = ("AGENTS.md", "CLAUDE.md")
URETILEN = (".agents/kalite-baseline.json",)

# tests/ içinde `os.path.join(ROOT, "a", "b")` biçimindeki dosya bağımlılığı
_ROOT_YOLU = re.compile(r"os\.path\.join\(\s*ROOT\s*,\s*((?:\"[^\"]+\"\s*,?\s*)+)\)")
# Test taşıyan dosyanın iki bağımsız imzası. Yalnız birincisine bakmak KÖR
# BEKÇİ üretir: taban sınıf takma adla gelirse (`Taban = unittest.TestCase;
# class X(Taban)`) `class` satırında `TestCase` sözcüğü hiç geçmez. İkinci
# imza (unittest + `def test_*(self`) o boşluğu kapatır; `tests/ortam.py`
# gibi test metodu OLMAYAN yardımcılar ikisine de uymaz.
_TESTCASE = re.compile(r"^class\s+\w+\s*\([^)]*\bTestCase\b", re.M)
_UNITTEST = re.compile(r"^\s*(?:import\s+unittest|from\s+unittest\b)", re.M)
_TEST_METODU = re.compile(r"^\s+(?:async\s+)?def\s+test\w*\s*\(\s*self\b", re.M)


def kurulumda_bulunur(rel):
    """Bu göreli yol, taze bir kurulumdan sonra projede bulunur mu?"""
    if rel in MOTOR or rel in PROJE_DOSYASI or rel in URETILEN:
        return True
    return any(rel == d or rel.startswith(d + "/") for d in MOTOR_DIZIN)


def eksik_test_bagimliliklari(kok):
    """[(test_dosyasi, rel)] — taşınan testin istediği ama taşınmayan yollar.

    Neden: `tests/` bir motor dizinidir, yani her test her projeye gider.
    Test ROOT'a göre bir dosya şart koşuyorsa o dosya da gitmeli. 2026-08-07'de
    4Flow kurulumunda bizzat oldu: KapsamSiniriTest her projeye taşındı ama
    şart koştuğu `docs/yasam-dongusu-kapsami.md` motor listesinde yoktu —
    yeni proje kurulumdan KIRMIZI çıktı. Kutudan kırmızı çıkan kurulum,
    insana kapıyı baştan yok saymayı öğretir.

    Yalnız kanonikte GERÇEKTEN var olan ve dosya olan yollar denetlenir:
    üretilen/geçici yollar ile yol kökü olarak kullanılan dizinler (ör. "bin")
    bir kurulum bağımlılığı değildir.

    Çıkış yolu: dosyanın başına `# kanonik-özel: <sebep>` yazan test denetim
    dışıdır. Bazı testlerin bağlı projede karşılığı YOKTUR (ör. kurucunun
    kendisi projeye taşınmaz) — o testler bağlı projede atlanmalı, kırmızı
    vermemeli. İşaret gerekçesiyle birlikte GÖRÜNÜR olsun diye zorunlu.
    """
    tests_dir = os.path.join(kok, "tests")
    if not os.path.isdir(tests_dir):
        return []
    eksik = []
    for f in sorted(os.listdir(tests_dir)):
        if not f.endswith(".py"):
            continue
        with open(os.path.join(tests_dir, f), encoding="utf-8") as fh:
            icerik = fh.read()
        if "kanonik-özel:" in icerik:
            continue
        for m in _ROOT_YOLU.finditer(icerik):
            rel = "/".join(re.findall(r"\"([^\"]+)\"", m.group(1)))
            tam = os.path.join(kok, rel)
            if not os.path.isfile(tam):
                continue
            if not kurulumda_bulunur(rel):
                eksik.append((f, rel))
    return eksik


def toplanmayan_testler(kok, toplanan):
    """[dosya_adi] — TestCase tanımlayan ama keşfe HİÇ girmeyen tests/*.py.

    Neden bekçi: eksilen test, kırmızı testten daha tehlikelidir. Kırmızı test
    bağırır; keşfe girmeyen test hiç sayılmaz, çıkış kodu 0 kalır ve "Ran N"
    daralmasını hiçbir satır söylemez. 2026-08-07 ölçümü: PyYAML'sız
    yorumlayıcıda üç modül import'ta çöktü, süite 220 yerine 186 test saydı —
    34 test yok olmuştu ama çıktıda yalnız "3 hata" yazıyordu.

    `toplanan`: keşfin GERÇEKTEN test ürettiği modül adları (uzantısız).
    TestCase taşımayan yardımcı dosyalar (ör. tests/ortam.py) denetim dışıdır.
    """
    tests_dir = os.path.join(kok, "tests")
    if not os.path.isdir(tests_dir):
        return []
    eksik = []
    for f in sorted(os.listdir(tests_dir)):
        if not f.endswith(".py") or f[:-3] in toplanan:
            continue
        with open(os.path.join(tests_dir, f), encoding="utf-8",
                  errors="replace") as fh:
            metin = fh.read()
        if _TESTCASE.search(metin) or (_UNITTEST.search(metin) and
                                       _TEST_METODU.search(metin)):
            eksik.append(f)
    return eksik


def sha(yol):
    with open(yol, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def dosyalar(kok, rel):
    """rel bir dosyaysa kendisini, dizinse altındaki dosyaları verir."""
    tam = os.path.join(kok, rel)
    if os.path.isfile(tam):
        yield rel
    elif os.path.isdir(tam):
        for dizin, _alt, isimler in os.walk(tam):
            for i in isimler:
                if i.endswith(".pyc") or "__pycache__" in dizin:
                    continue
                yield os.path.relpath(os.path.join(dizin, i), kok)


def motor_dosyalari(kok):
    """Bir kökteki tüm motor dosyalarının göreli yolları (sıralı, tekrarsız)."""
    bulunan = set()
    for giris in MOTOR + MOTOR_DIZIN:
        bulunan.update(dosyalar(kok, giris))
    return sorted(bulunan)


MANIFEST_REL = ".agents/.kernel-manifest.json"
GITLEAKS_CFG = ".gitleaks.toml"
# Manifest yalnız sha256 özeti taşır; gitleaks'in generic-api-key kuralı
# uzun hex bloklarını anahtar sanar. 4cast'te bu 7 yanlış pozitif üretip
# CI'ı bir haftadan uzun kırmızıda tuttu (2026-08-07). Dosyayı kernel
# ÜRETTİĞİ için sorun bağlı HER projede tekrarlanır — kurulumda çözülmeli.
MUAFIYET_BLOGU = """
[allowlist]
description = "AurasAgents kernel manifest'i — yalnız sha256 özeti taşır, kimlik bilgisi değil"
paths = [
  '''\\.agents/\\.kernel-manifest\\.json''',
]
"""


def gitleaks_kullaniyor(kok):
    """Proje gitleaks koşuyor mu (config'i var ya da workflow'da anılıyor)."""
    if os.path.isfile(os.path.join(kok, GITLEAKS_CFG)):
        return True
    wf = os.path.join(kok, ".github", "workflows")
    if not os.path.isdir(wf):
        return False
    for ad in sorted(os.listdir(wf)):
        try:
            with open(os.path.join(wf, ad), encoding="utf-8",
                      errors="replace") as fh:
                if "gitleaks" in fh.read():
                    return True
        except OSError:
            continue
    return False


def manifest_muaf_mi(kok):
    """Manifest gitleaks allowlist'inde mi (yoksa yanlış pozitif üretir).

    'kernel-manifest' aranır, '.kernel-manifest.json' DEĞİL: gitleaks yol
    desenleri regex'tir ve nokta kaçışlıdır (`\\.kernel-manifest\\.json`).
    Düz nokta aramak kendi şablonumuzu bile eşleştirmiyordu (test yakaladı).
    """
    try:
        with open(os.path.join(kok, GITLEAKS_CFG), encoding="utf-8") as fh:
            return "kernel-manifest" in fh.read()
    except OSError:
        return False


def _git(kok, *arg, girdi=None):
    try:
        p = subprocess.run(["git", "-C", kok, *arg], capture_output=True,
                           text=True, input=girdi, timeout=20)
        return p.stdout if p.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def gecmis_blob_idler(kanonik, rel):
    """rel için kanonik git geçmişindeki TÜM sürümlerin blob id'leri.

    None döner = geçmiş okunamadı (git yok / dosya hiç izlenmemiş). Çağıran
    bunu 'bilinmiyor' sayıp temkinli davranmalı (yerel kabul et).
    """
    log = _git(kanonik, "log", "--format=%H", "--", rel)
    if log is None:
        return None
    commitler = [c for c in log.split() if c]
    if not commitler:
        return set()
    istek = "".join(f"{c}:{rel}\n" for c in commitler)
    cikti = _git(kanonik, "cat-file", "--batch-check=%(objectname)",
                 girdi=istek)
    if cikti is None:
        return None
    return {s for s in cikti.split() if len(s) == 40}


def blob_id(yol):
    """Bir dosyanın git blob id'si (repo gerektirmez)."""
    try:
        p = subprocess.run(["git", "hash-object", yol], capture_output=True,
                           text=True, timeout=20)
        return p.stdout.strip() if p.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def sinifla(kanonik, hedef, rel):
    """Hedefteki motor dosyasının kanoniğe göre durumu.

    yok    — hedefte dosya yok (kurulacak)
    ayni   — içerik kanonikle birebir
    geride — içerik kanoniğin ESKİ bir sürümü (güvenle güncellenebilir)
    yerel  — içerik kanonik geçmişte hiç görülmedi → YEREL İŞ, ezilemez
    """
    k_yol, h_yol = os.path.join(kanonik, rel), os.path.join(hedef, rel)
    if not os.path.isfile(h_yol):
        return "yok"
    if os.path.isfile(k_yol) and sha(k_yol) == sha(h_yol):
        return "ayni"
    gecmis = gecmis_blob_idler(kanonik, rel)
    if gecmis is None:
        return "yerel"          # geçmiş bilinmiyor → temkinli: koru
    return "geride" if blob_id(h_yol) in gecmis else "yerel"


def karsilastir(kanonik, hedef):
    """[(rel, sinif)] — iki kökün motor dosyalarının birleşimi üstünde."""
    rel_ler = set(motor_dosyalari(kanonik)) | set(motor_dosyalari(hedef))
    return [(rel, sinifla(kanonik, hedef, rel)) for rel in sorted(rel_ler)]
