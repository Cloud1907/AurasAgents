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
    "bin/skill_kayit.py", "bin/davranis.py", "bin/secim.py",   # route.py'nin bağımlılığı — birlikte taşınmalı
    "bin/niyet.py",         # route.py'nin niyet kapısı — taşınmazsa kapı susar
    "bin/memory_hygiene.py", "bin/hatirla.py", "bin/run_event.py", "bin/durum.py",
    "bin/kapi.py", "bin/araclar.py", "bin/kernel_dosyalari.py",
    "bin/anlik.py",         # kapı'nın worktree ölçüsü — taşınmazsa kabuk
                            # yazımları bağlı projede yine görünmez olur
    "bin/kapsam_bekcisi.py",
    "bin/kalite.py",
    "bin/auras_geri.py", "bin/incele.py", "bin/hukum.py",
    "bin/surec.py",
    "bin/tur.py", "bin/risk.py",   # incele.py'nin bağımlılıkları — birlikte taşınmalı
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


def yol_coz(kok, rel):
    """Göreli yolu diskte BÜYÜK/küçük harf duyarsız çözer (yoksa None).

    Neden gerekli: projelerin dizin adlandırması farklı (4cast `Docs/`
    kullanıyor, motor `docs/` yazıyor). macOS/Windows dosya sistemi
    duyarsız olduğu için yerelde sorun çıkmıyor ama git yolu YAZILDIĞI
    gibi saklıyor; Linux CI'da dosya "yok" görünüyor ve kapı yanlış yere
    kırmızı yanıyor (4cast, 2026-08-07). Aynı repo platforma göre farklı
    davranıyorsa, bu taşınabilirlik hatasıdır.
    """
    tam = os.path.join(kok, rel)
    if os.path.exists(tam):
        return tam
    parcalar = rel.replace("\\", "/").split("/")
    simdi = kok
    for parca in parcalar:
        try:
            girisler = os.listdir(simdi)
        except OSError:
            return None
        esles = [g for g in girisler if g.lower() == parca.lower()]
        if not esles:
            return None
        simdi = os.path.join(simdi, esles[0])
    return simdi


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
description = "AurasAgents kernel dosyalari — sir degil, kapinin kendi malzemesi"
paths = [
  # Manifest yalniz sha256 OZETI tasir; generic-api-key kurali uzun hex'i
  # anahtar saniyor (4cast: 7 yanlis pozitif, CI bir haftadan uzun kirmizi).
  '''\\.agents/\\.kernel-manifest\\.json''',
  # Skill eval fixture'lari KASITLI sahte anahtar tasir — tarayicinin kendi
  # kabul vakalari. Bizim tarayicimiz `--exclude */eval/*` ile diliyor ama
  # gitleaks bunu bilmiyordu ve her projede ayni yanlis pozitifi uretiyordu
  # (4Flow: stripe-access-token @ security-review/eval/cases.md, 2026-08-07).
  '''\\.agents/skills/.*/eval/.*''',
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
            metin = fh.read()
        # Eval fixture muafiyeti sonradan eklendi; ikisi de olmalı yoksa
        # kurulum "muaf" sanıp CI'ı yanlış pozitifle kırmızı bırakır.
        return "kernel-manifest" in metin and "skills/.*/eval" in metin
    except OSError:
        return False


def _git(kok, *arg, girdi=None, zaman=20):
    try:
        p = subprocess.run(["git", "-C", kok, *arg], capture_output=True,
                           text=True, input=girdi, timeout=zaman)
        return p.stdout if p.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


FETCH_ZAMAN = 20


def _yukari_akim(kok):
    """Mevcut dalın upstream'i (ör. `origin/main`) ya da None.

    Dal adı sabitlenmez: `origin/main` varsayan kod, main'den başka dalda
    çalışan projede sessizce "doğrulanamadı"ya düşerdi.
    """
    ref = _git(kok, "rev-parse", "--abbrev-ref", "@{upstream}")
    return ref.strip() if ref and ref.strip() else None


def _fark(kok, upstream):
    """(ileri, geri) — HEAD upstream'e göre kaç commit önde/arkada."""
    sayim = _git(kok, "rev-list", "--left-right", "--count", f"HEAD...{upstream}")
    try:
        ileri, geri = sayim.split()[:2]
        return int(ileri), int(geri)
    except (AttributeError, ValueError):
        return None


def _kirli(kok):
    """İzlenen dosyalarda kaydedilmemiş değişiklik var mı.

    İzlenmeyen dosya sayılmaz: scratch dosyası ne ileri sarmayı bozar ne de
    kurulumu durdurmayı hak eder.
    """
    cikti = _git(kok, "status", "--porcelain", "--untracked-files=no")
    return bool(cikti and cikti.strip())


def _ileri_sar(kok, upstream, ileri, geri):
    """Geride kalan kaynağı upstream'e taşımayı dener → (durum, mesaj)."""
    geride = f"kaynak {upstream}'in {geri} commit gerisinde"
    if ileri:
        return "engel", f"{geride} ve {ileri} yerel commit var — ileri sarılamaz"
    if _kirli(kok):
        return "engel", f"{geride} ve çalışma ağacı kirli — ileri sarılamaz"
    if _git(kok, "merge", "--ff-only", upstream) is None:
        return "engel", f"{geride}; ileri sarma başarısız — elle çöz"
    return "ilerletildi", f"kaynak {geri} commit ileri sarıldı → {upstream}"


def kaynak_tazele(kok):
    """Kurulum kaynağını upstream'e ileri sarmayı dener → (durum, mesaj).

    guncel        — HEAD upstream ile aynı (fetch doğrulandı)
    ilerletildi   — geride idi, fast-forward ile upstream'e taşındı
    engel         — geride ama güvenle ileri sarılamıyor (yerel commit/kirli)
    dogrulanamadi — git yok, upstream yok ya da fetch başarısız

    Neden kapı: `/auras` dosyaları kanonik ÇALIŞMA AĞACINDAN kopyalar. Ağaç
    origin'in gerisindeyse kurulan motor eskidir ama manifest onu "güncel"
    diye damgalar — kapı var, koruma yok. 2026-08-15 ölçümü: ağaç e3f1ec1'de,
    origin/main 2d42b90'daydı; o gün koşulacak her /auras eski niyet kapısını
    yayacaktı. Fast-forward seçilmesi bilinçli: iş kaybettiremeyen tek
    ilerletme biçimidir; sarılamıyorsa kararı insan verir.
    """
    if _git(kok, "rev-parse", "--git-dir") is None:
        return "dogrulanamadi", "git deposu değil — kaynak sürümü bilinmiyor"
    upstream = _yukari_akim(kok)
    if upstream is None:
        return "dogrulanamadi", "dalın upstream'i yok — karşılaştıracak uzak sürüm yok"
    taze = _git(kok, "fetch", "--quiet", upstream.split("/", 1)[0],
                zaman=FETCH_ZAMAN) is not None
    fark = _fark(kok, upstream)
    if fark is None:
        return "dogrulanamadi", f"{upstream} okunamadı — karşılaştırma yapılamadı"
    ileri, geri = fark
    if geri:
        return _ileri_sar(kok, upstream, ileri, geri)
    if not taze:
        return "dogrulanamadi", f"fetch başarısız — {upstream} tazeliği doğrulanamadı"
    # Push edilmemiş commit ve kaydedilmemiş değişiklik engel DEĞİLDİR —
    # kernel burada geliştirilir. Ama sessiz de kalamaz: ikisi de bağlı
    # repolara İNCELENMEMİŞ içerik taşır ve "guncel" onu görünmez kılar.
    uyari = []
    if ileri:
        uyari.append(f"{ileri} yerel commit henüz uzakta yok")
    if _kirli(kok):
        uyari.append("çalışma ağacı kirli — kaydedilmemiş içerik kurulur")
    ek = f" (uyarı: {'; '.join(uyari)})" if uyari else ""
    return "guncel", f"kaynak {upstream} ile aynı{ek}"


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
