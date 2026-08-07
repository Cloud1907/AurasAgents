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
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

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


def karar(risk, bulgular, ci_yesil, okunabildi):
    """(karar, gerekçe) — merge | insan | engel."""
    if not okunabildi:
        return "engel", ("inceleme çıktısı ayrıştırılamadı — 'okunamadı' "
                         "'temiz' demek değildir")
    if bulgular["P0"]:
        return "engel", f"{len(bulgular['P0'])} adet P0 (merge engelleyici)"
    if bulgular["P1"]:
        return "engel", f"{len(bulgular['P1'])} adet P1 (merge öncesi düzeltilmeli)"
    if risk == "deny":
        return "engel", "deny sınıfı — break-glass gerekir, kararı agent veremez"
    if not ci_yesil:
        return "engel", "CI yeşil değil"
    if risk == "auto":
        return "merge", "auto risk · inceleme temiz · CI yeşil"
    return "insan", f"{risk} sınıfı — karar kullanıcının"


# --- Dış dünya -------------------------------------------------------------
def _kos(*arg, girdi=None, timeout=600):
    try:
        p = subprocess.run(arg, capture_output=True, text=True,
                           input=girdi, timeout=timeout, cwd=ROOT)
        return p.returncode, p.stdout, p.stderr
    except (OSError, subprocess.SubprocessError) as e:
        return 1, "", str(e)


def pr_dosyalari(pr):
    kod, out, _e = _kos("gh", "pr", "view", str(pr), "--json", "files",
                        "-q", ".files[].path")
    return [s for s in out.splitlines() if s.strip()] if kod == 0 else []


def ci_durumu(pr):
    """(yesil, ozet) — hiçbir check yoksa yeşil SAYILMAZ."""
    kod, out, _e = _kos("gh", "pr", "checks", str(pr))
    satirlar = [s for s in out.splitlines() if s.strip()]
    if kod != 0 and not satirlar:
        return False, "check okunamadı"
    if not satirlar:
        return False, "hiç check yok"
    durumlar = [s.split("\t")[1] if "\t" in s else "?" for s in satirlar]
    return all(d == "pass" for d in durumlar), \
        f"{durumlar.count('pass')}/{len(durumlar)} pass"


def codex_incele(pr):
    kod, out, err = _kos("bash", os.path.join(HERE, "codex-review.sh"),
                         str(pr), "--dry-run")
    return out if kod == 0 else (out + "\n" + err)


def yorum_dus(pr, govde):
    kod, _o, err = _kos("gh", "pr", "comment", str(pr), "--body-file", "-",
                        girdi=govde)
    return kod == 0, err


def ozet_govde(risk, bulgular, sonuc, k, gerekce, ci_ozet):
    """PR yorumu — duvar değil, KARAR biçiminde. Okunmayan yorum yoktur."""
    simge = {"merge": "✅", "insan": "👤", "engel": "⛔"}[k]
    satir = [f"## {simge} Bağımsız inceleme — {k.upper()}",
             "",
             f"**Karar:** {gerekce}",
             f"**Risk sınıfı:** `{risk}` · **CI:** {ci_ozet} · "
             f"**Codex:** {sonuc or '—'}",
             ""]
    for sev in ("P0", "P1", "P2"):
        for b in bulgular[sev]:
            satir.append(f"- `{sev}` {b}")
    if not any(bulgular.values()):
        satir.append("Bulgu yok.")
    satir += ["", "---",
              "Çapraz-vendor risk sinyali (Codex), makine kanıtı değil. "
              "Merge koşulu: CI yeşil **ve** bu inceleme temiz."]
    return "\n".join(satir)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("pr")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--kuru", action="store_true", help="PR'a yorum atma")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    dosyalar = pr_dosyalari(a.pr)
    risk = risk_sinifi(dosyalar)
    ci_yesil, ci_ozet = ci_durumu(a.pr)
    ham = codex_incele(a.pr)
    bulgular, sonuc, okunabildi = bulgulari_ayikla(ham)
    k, gerekce = karar(risk, bulgular, ci_yesil, okunabildi)

    govde = ozet_govde(risk, bulgular, sonuc, k, gerekce, ci_ozet)
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
        kod, _o, err = _kos("gh", "pr", "merge", str(a.pr), "--merge")
        if kod != 0:
            print(f"merge başarısız: {err[:200]}")
            return 1
        print(f"\nPR #{a.pr} merge edildi (auto risk · inceleme temiz · CI yeşil)")
    return 0 if k != "engel" else 1


if __name__ == "__main__":
    raise SystemExit(main())
