#!/usr/bin/env python3
"""incele — merge'ün tek yolu: bağımsız inceleme + risk sınıfına göre karar.

2026-08-07 ölçümü: `bin/codex-review.sh` kurulu ve `codex` CLI çalışır
durumdaydı ama HİÇBİR yerden çağrılmıyordu — açılan 3 PR'da 0 inceleme
yorumu. Kullanıcı da PR'ları okumadığını söyledi. Sonuç: "insan merge"
satırı en güçlü duran ama fiilen boş çalışan halkaydı — ne insan ne makine
incelemesi vardı. Bu araç o boşluğu kapatır.

Neden Codex: farklı SATICI, farklı kör nokta. İkinci bir Claude aynı hataları
yapardı; bağımsızlık modelin farklı olmasından gelir, sayısından değil.
İnceleme yine de RİSK SİNYALİDİR, makine kanıtı değildir (AGENTS.md) —
bu yüzden CI yeşili ayrıca aranır.

Karar tablosu:
  inceleme okunamadı      → ENGEL (fail-closed: sessiz "temiz" yok)
  P0/P1 bulgu var         → ENGEL
  risk = deny             → ENGEL (break-glass insanın)
  risk = approval         → İNSAN (5 satır özet, karar kullanıcının)
  risk = auto + CI yeşil  → MERGE
  diğer                   → İNSAN (bilinmeyen yukarı eskale olur)

Kullanım:
  python3 bin/incele.py 13              # incele, PR'a yorum düş, karar bas
  python3 bin/incele.py 13 --merge      # karar MERGE ise birleştir
  python3 bin/incele.py 13 --kuru       # yorum atma (deneme)
  python3 bin/incele.py 13 --json
"""
import argparse
import json
import os
import re
import signal
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# İnceleme bütçesi `gh` çağrılarınınkinden AYRIDIR (önce ikisi de `_kos`'un
# genel varsayılanına bağlıydı). Ölçüm (2026-08-07): 4.4KB→147s, 9.0KB→156s —
# boyut baskın değil, ~140s sabit taban var. Bu yüzden diff boyutuna göre
# ÖLÇEKLENMİYOR: ölçeklenecek değişken sürücü değil.
INCELEME_BUTCESI = int(os.environ.get("INCELE_BUTCE", "900"))

# --- Risk sınıflandırma (AGENTS.md risk politikası, path kuralı) -----------
# Eskalasyon YALNIZ yukarı: bilinmeyen yol `approval` sayılır, `auto` değil.
DENY = re.compile(
    r"(^|/)(\.env($|\.)|secrets?/|credentials?/|id_rsa|.*\.pem$|.*\.key$)", re.I)
APPROVAL = re.compile(
    r"(auth|kimlik|oturum|session|payment|odeme|ödeme|migration|permission"
    r"|/hooks/|settings\.json|token|deploy|^bin/|^\.agents/|^\.github/"
    r"|package(-lock)?\.json$|\.csproj$|requirements\.txt$)", re.I)
AUTO = re.compile(r"(^docs/|\.md$|^tests?/|^\.agents/reports/)", re.I)


def risk_sinifi(dosyalar):
    """Değişen yollardan nihai risk sınıfı. Boş liste → approval (temkinli)."""
    if not dosyalar:
        return "approval"
    if any(DENY.search(d) for d in dosyalar):
        return "deny"
    if any(APPROVAL.search(d) for d in dosyalar):
        return "approval"
    if all(AUTO.search(d) for d in dosyalar):
        return "auto"
    return "approval"


# --- Codex çıktısını ayrıştır ---------------------------------------------
BULGU = re.compile(r"\[\s*(P[012])\s*\]\s*(.+)")
SONUC = re.compile(r"SONU[CÇ]\s*:\s*(.+)", re.I)


def bulgulari_ayikla(metin):
    """(bulgular, sonuc_satiri, okunabildi).

    okunabildi=False ise karar ENGEL olur: "ayrıştıramadım" ile "temiz"
    aynı şey DEĞİLDİR. Sessiz geçiş bu sistemin en sık hatası.
    """
    bulgular = {"P0": [], "P1": [], "P2": []}
    for satir in (metin or "").splitlines():
        m = BULGU.search(satir)
        if m:
            bulgular[m.group(1)].append(m.group(2).strip()[:160])
    s = SONUC.search(metin or "")
    return bulgular, (s.group(1).strip() if s else ""), bool(s)


# --- Codex bulgularına yanıt (2026-08-07, kapı kendi PR'ını bloklad) -------

def tutarli_mi(bulgular, sonuc):
    """P1 · Hüküm satırı ile ayrıştırılan bulgular birbirini tutuyor mu.

    Önce herhangi bir `SONUC:` metni geçerli inceleme sayılıyordu; bozuk ya da
    uydurulmuş bir hüküm sessizce kabul ediliyordu.
    """
    sayi = sum(len(v) for v in bulgular.values())
    temiz_diyor = "TEMIZ" in (sonuc or "").upper()
    if temiz_diyor:
        return sayi == 0
    m = re.search(r"(\d+)\s*bulgu", sonuc or "", re.I)
    if m:
        return int(m.group(1)) == sayi
    return sayi > 0


# Diff, inceleyiciye TALİMAT veriyorsa hüküm güvenilmez. Yalnız EKLENEN
# satırlara bakılır; doğal dil kalıbı aranır (kod/regex tanımı değil).
ENJEKSIYON = re.compile(
    r"(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above)\s+"
    r"(instruction|rule|prompt)"
    r"|(?:sen|you)\s+bir\s+incele|you\s+are\s+(a\s+)?review"
    r"|TEM[İI]Z\s+(olarak\s+)?(yaz|raporla|d[öo]n)"
    r"|(output|report|respond)\s+(with\s+)?(TEMIZ|CLEAN|APPROVE)"
    r"|(approve|onayla)\s+(this|bu)\s+(pr|diff|change)", re.I)


def enjeksiyon_var_mi(diff):
    """Eklenen satırlarda inceleyiciye yönelik talimat var mı."""
    for satir in (diff or "").splitlines():
        if satir.startswith("+") and ENJEKSIYON.search(satir):
            return True
    return False


# CI "yeşil" sayılması için KANIT üreten check'in varlığı şart. Önceden
# alakasız bir yeşil check (vercel/render) yeterliydi; evidence workflow'u
# hiç oluşmasa bile kapı geçiyordu.
ZORUNLU_CHECK = re.compile(r"kernel|evidence|gate", re.I)


def _check_kayitlari(satirlar):
    """gh pr checks satırlarını (ad, durum) çiftlerine çevirir."""
    kayit = []
    for s in satirlar:
        if not s.strip():
            continue
        parca = s.split("\t")
        kayit.append((parca[0].strip(),
                      parca[1].strip() if len(parca) > 1 else "?"))
    return kayit


def ci_karari(satirlar):
    """(yesil, ozet) — gh pr checks çıktı satırlarından."""
    kayit = _check_kayitlari(satirlar)
    if not kayit:
        return False, "hiç check yok"
    kanit = [d for a, d in kayit if ZORUNLU_CHECK.search(a)]
    gecen = sum(1 for _a, d in kayit if d == "pass")
    ozet = f"{gecen}/{len(kayit)} pass"
    if not kanit:
        return False, (f"{len(kayit)} check var ama kanıt check'i "
                       "(kernel/evidence/gate) yok")
    if not all(d == "pass" for d in kanit):
        return False, f"kanıt check'i geçmedi ({ozet})"
    return gecen == len(kayit), ozet


def merge_komutu(pr, head_sha):
    """P0 · Merge İNCELENEN commit'e sabitlenir.

    İnceleme bittikten sonra dala yeni commit itilirse --match-head-commit
    olmadan `gh pr merge` incelenmemiş kodu birleştirirdi.
    """
    if not head_sha:
        raise ValueError("head SHA yok — merge incelenen commit'e sabitlenemez")
    return ["gh", "pr", "merge", str(pr), "--merge",
            "--match-head-commit", head_sha]


def karar(risk, bulgular, ci_yesil, okunabildi, tutarli=True,
          enjeksiyon=False):
    """(karar, gerekçe) — merge | insan | engel."""
    if not okunabildi:
        return "engel", ("inceleme çıktısı ayrıştırılamadı — 'okunamadı' "
                         "'temiz' demek değildir")
    if not tutarli:
        return "engel", ("inceleme hükmü bulgularla tutarsız — hüküm "
                         "güvenilmez")
    if bulgular["P0"]:
        return "engel", f"{len(bulgular['P0'])} adet P0 (merge engelleyici)"
    if bulgular["P1"]:
        return "engel", f"{len(bulgular['P1'])} adet P1 (merge öncesi düzeltilmeli)"
    if risk == "deny":
        return "engel", "deny sınıfı — break-glass gerekir, kararı agent veremez"
    if not ci_yesil:
        return "engel", "CI yeşil değil"
    if enjeksiyon:
        # Güvenlik gereği: enjekte edilmiş diff OTOMATİK merge ettiremesin.
        # ENGEL değil İNSAN — aracın kendi format dizesini içeren meşru
        # PR'lar da eşleşir; ENGEL kalıcı öz-blok üretirdi.
        return "insan", ("diff inceleyiciye talimat veriyor olabilir "
                         "(enjeksiyon şüphesi) — hüküm otomatik merge için "
                         "yeterli sayılmaz")
    if risk == "auto":
        return "merge", "auto risk · inceleme temiz · CI yeşil"
    return "insan", f"{risk} sınıfı — karar kullanıcının"


# --- Dış dünya -------------------------------------------------------------
def _agaci_oldur(p):
    """Süreç GRUBUNU öldürür. `p.kill()` yalnız doğrudan çocuğu (bash) alır;
    altındaki ask-codex.sh ve `codex exec` yaşar ve PPID 1'e düşer."""
    try:
        os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    except OSError:
        p.kill()
    try:
        p.communicate(timeout=10)
    except (OSError, subprocess.SubprocessError):
        pass


def _kos(*arg, girdi=None, timeout=600):
    """Alt süreci KENDİ oturumunda başlatır; zaman aşımında tüm ağacı öldürür.
    `subprocess.run(timeout=)` yalnız beklemeyi sınırlar, ağacı öldürmez.
    Gerekçe ve ölçüm: tests/test_incele.py · SurecSizintisiTest."""
    try:
        p = subprocess.Popen(
            arg, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.PIPE if girdi is not None else None,
            text=True, cwd=ROOT, start_new_session=True)
    except OSError as e:
        return 1, "", str(e)
    try:
        out, err = p.communicate(girdi, timeout=timeout)
        return p.returncode, out, err
    except (OSError, subprocess.SubprocessError) as e:
        _agaci_oldur(p)  # TimeoutExpired dahil: ağacı bırakma
        return 1, "", str(e)


def pr_dosyalari(pr):
    kod, out, _e = _kos("gh", "pr", "view", str(pr), "--json", "files",
                        "-q", ".files[].path")
    return [s for s in out.splitlines() if s.strip()] if kod == 0 else []


def pr_head_sha(pr):
    kod, out, _e = _kos("gh", "pr", "view", str(pr), "--json", "headRefOid",
                        "-q", ".headRefOid")
    return out.strip() if kod == 0 else ""


def pr_diff(pr):
    kod, out, _e = _kos("gh", "pr", "diff", str(pr))
    return out if kod == 0 else ""


def ci_durumu(pr):
    """(yesil, ozet) — hiçbir check yoksa yeşil SAYILMAZ."""
    kod, out, _e = _kos("gh", "pr", "checks", str(pr))
    satirlar = [s for s in out.splitlines() if s.strip()]
    if kod != 0 and not satirlar:
        return False, "check okunamadı"
    return ci_karari(satirlar)


def zaman_asimi_notu(butce):
    """Zaman aşımında kullanıcının önüne EYLEM koyar — önünde yol olmayan
    kapı `gh pr merge` ile atlanır, kural belgede kalır sistemde kalmaz."""
    return (
        f"İnceleme {butce}s bütçesinde bitmedi. Karar ENGEL — 'okunamadı' "
        "'temiz' demek değildir. Sırayla dene:\n"
        "1. Asılı süreç var mı: `pgrep -fl 'codex exec'` — varsa öldür. "
        "Sızan inceleme sonrakini yavaşlatır (ölçüm: 155.8s → 45.5s).\n"
        f"2. Bütçeyi yükseltip tekrar koş: "
        f"`INCELE_BUTCE={butce * 2} python3 bin/incele.py <pr>`\n"
        "3. PR'ı böl — tek amaçlı küçük diff hem hızlı hem doğru incelenir "
        "(AGENTS.md: ilgisiz işleri tek PR'da toplama).")


def codex_incele(pr, butce=None):
    """(ham_cikti, hata_notu) — hata notu boşsa çağrı sorunsuz.

    Neden ayrı dönüyor: kapı "ayrıştıramadım" dediğinde SEBEBİ görünmeli —
    teşhis edilemeyen kırmızı, kapalı kapıdan farksızdır.
    """
    butce = INCELEME_BUTCESI if butce is None else butce
    kod, out, err = _kos("bash", os.path.join(HERE, "codex-review.sh"),
                         str(pr), "--dry-run", timeout=butce)
    if kod != 0:
        hata = f"codex-review.sh exit {kod}: {(err or '').strip()[:200]}"
        if "timed out" in (err or "").lower():
            hata = f"zaman aşımı ({butce}s)\n\n{zaman_asimi_notu(butce)}"
        return out, hata
    if not (out or "").strip():
        return "", "codex boş yanıt döndürdü"
    return out, ""


def yorum_dus(pr, govde):
    kod, _o, err = _kos("gh", "pr", "comment", str(pr), "--body-file", "-",
                        girdi=govde)
    return kod == 0, err


def ozet_govde(risk, bulgular, sonuc, k, gerekce, ci_ozet,
               enjeksiyon=False, tani=""):
    """PR yorumu — duvar değil, KARAR biçiminde. Okunmayan yorum yoktur."""
    simge = {"merge": "✅", "insan": "👤", "engel": "⛔"}[k]
    satir = [f"## {simge} Bağımsız inceleme — {k.upper()}",
             "",
             f"**Karar:** {gerekce}",
             f"**Risk sınıfı:** `{risk}` · **CI:** {ci_ozet} · "
             f"**Codex:** {sonuc or '—'}",
             ""]
    if tani:
        satir += ["<details><summary>Ayrıştırılamayan çıktının sonu</summary>",
                  "", "```", tani, "```", "</details>", ""]
    if enjeksiyon:
        satir += ["> ⚠️ Diff, inceleyiciye talimat veriyor olabilir "
                  "(enjeksiyon şüphesi). Hüküm otomatik merge için yeterli "
                  "sayılmadı.", ""]
    for sev in ("P0", "P1", "P2"):
        for b in bulgular[sev]:
            satir.append(f"- `{sev}` {b}")
    if not any(bulgular.values()):
        satir.append("Bulgu yok.")
    satir += ["", "---",
              "Çapraz-vendor risk sinyali (Codex), makine kanıtı değil. "
              "Merge koşulu: CI yeşil **ve** bu inceleme temiz."]
    return "\n".join(satir)


def topla(pr):
    """PR'a dair tüm dış bilgiyi tek yerde toplar (main sade kalsın)."""
    ci_yesil, ci_ozet = ci_durumu(pr)
    ham, hata = codex_incele(pr)
    bulgular, sonuc, okunabildi = bulgulari_ayikla(ham)
    return {
        "risk": risk_sinifi(pr_dosyalari(pr)),
        "ci_yesil": ci_yesil, "ci_ozet": ci_ozet,
        # İncelenen commit BURADA sabitlenir; merge sonra bunu doğrular.
        "head_sha": pr_head_sha(pr),
        "enjeksiyon": enjeksiyon_var_mi(pr_diff(pr)),
        "bulgular": bulgular, "sonuc": sonuc, "okunabildi": okunabildi,
        "hata": hata,
        # Ayrıştırılamayan çıktının kuyruğu: teşhis için tek ipucu.
        "ham_kuyruk": "\n".join((ham or "").strip().splitlines()[-6:]),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("pr")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--kuru", action="store_true", help="PR'a yorum atma")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    d = topla(a.pr)
    risk, ci_ozet, head_sha = d["risk"], d["ci_ozet"], d["head_sha"]
    bulgular, sonuc, enjeksiyon = d["bulgular"], d["sonuc"], d["enjeksiyon"]
    k, gerekce = karar(risk, bulgular, d["ci_yesil"], d["okunabildi"],
                       tutarli=tutarli_mi(bulgular, sonuc),
                       enjeksiyon=enjeksiyon)
    if not d["okunabildi"]:
        gerekce += f" — {d['hata'] or 'SONUC satırı yok'}"

    govde = ozet_govde(risk, bulgular, sonuc, k, gerekce, ci_ozet,
                       enjeksiyon,
                       tani="" if d["okunabildi"] else d["ham_kuyruk"])
    if not a.kuru:
        ok, err = yorum_dus(a.pr, govde)
        if not ok:
            print(f"UYARI: PR yorumu düşülemedi: {err[:120]}", file=sys.stderr)

    if a.json:
        print(json.dumps({"pr": a.pr, "risk": risk, "ci": ci_ozet,
                          "karar": k, "gerekce": gerekce,
                          "bulgular": bulgular, "sonuc": sonuc},
                         ensure_ascii=False, indent=2))
    else:
        print(govde)

    if a.merge:
        if k != "merge":
            print(f"\nMERGE YAPILMADI — karar '{k}': {gerekce}")
            return 1
        try:
            komut = merge_komutu(a.pr, head_sha)
        except ValueError as e:
            print(f"\nMERGE YAPILMADI — {e}")
            return 1
        kod, _o, err = _kos(*komut)
        if kod != 0:
            # --match-head-commit uyuşmazsa: inceleme sonrası yeni commit
            # gelmiş demektir; İNCELENMEMİŞ kod birleşmez.
            print(f"merge başarısız (head değişmiş olabilir): {err[:200]}")
            return 1
        print(f"\nPR #{a.pr} merge edildi — incelenen commit {head_sha[:8]}")
    return 0 if k != "engel" else 1


if __name__ == "__main__":
    raise SystemExit(main())
