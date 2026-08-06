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
import subprocess

# Motorun dosyaları — projenin değil. Her /auras koşumunda senkronlanır.
MOTOR = [
    "bin/validate.py", "bin/make_evidence.py", "bin/route.py",
    "bin/memory_hygiene.py", "bin/run_event.py", "bin/durum.py",
    "bin/kapi.py", "bin/araclar.py", "bin/kernel_dosyalari.py",
    "bin/kalite.py",
    "bin/auras_geri.py", "bin/codex-review.sh",
    "bin/install-hooks.sh", "bin/hooks/pre-push",
    "schemas/evidence.schema.json",
    ".github/workflows/evidence.yml",
    ".github/ISSUE_TEMPLATE/work-contract.yml",
    ".agents/routing.yml",
]
# Dizin olarak senkronlananlar (içerik tamamen motorun)
MOTOR_DIZIN = [".agents/skills", ".agents/capability-profiles", "tests",
               ".claude/rules"]

SINIFLAR = ("yok", "ayni", "geride", "yerel")


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
