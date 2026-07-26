#!/usr/bin/env python3
"""Tur sonu muhatap kapısı — kanıt yoksa "bitti" yok.

Stop hook'u olarak çalışır. Bu turda ne değiştiğine bakar ve kanıt arar:
kaynak kod değiştiyse SON DÜZENLEMEDEN SONRA koşmuş ve GEÇMİŞ bir test;
risk yüzeyi değiştiyse güvenlik incelemesi. Eksikse turu bloklar ve ajanı
işe geri gönderir.

Codex eleştirisi (2026-07-26) doğrudan buraya işlendi:
- "test dosyası değişti" test kanıtı DEĞİLDİR → testin koştuğu ve geçtiği aranır.
- "skill yüklendi" inceleme kanıtı DEĞİLDİR → risk yüzeyinde skill yüklenmesi
  asgari koşuldur, yeterli değil; kullanıcıya da bu ayrım söylenir.
- Uyarmak yetmez, bloklamak gerekir; yoksa gerekçe yazdırmak bürokrasidir.
- Aynı diff imzası için tek blok: kullanıcı/ajan kapana kısılmaz.

Kullanım (Stop hook):
    python3 bin/kapi.py
Elle deneme:
    echo '{}' | python3 bin/kapi.py --log /tmp/events.jsonl
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# Kaynak kod uzantıları (doküman/metin hariç — .md değişikliği test istemez).
KAYNAK_UZANTI = (".py", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".cs", ".go",
                 ".rb", ".java", ".kt", ".php", ".swift", ".sql", ".sh")
# Test dosyası imzaları.
TEST_YOL = re.compile(r"(^|/)tests?/|(^|/)test_|_test\.|\.test\.|\.spec\.")
# Risk yüzeyi: dokunulursa güvenlik incelemesi ister (AGENTS.md risk politikası).
RISK_YOL = re.compile(
    r"(auth|kimlik|oturum|session|secret|credential|\.env|migration|payment"
    r"|odeme|ödeme|upload|permission|settings\.json|/hooks/|token)", re.I)
# Görünür yüzey: değişirse birim testi yetmez, TIKLAMA kanıtı istenir.
UI_UZANTI = (".tsx", ".jsx", ".vue", ".svelte", ".cshtml", ".razor", ".html",
             ".css", ".scss")
UI_YOL = re.compile(r"(components?|pages?|views?|screens?|web|ui|frontend)/", re.I)

# Büyük değişim eşikleri (Codex: 300 satır kaba; dosya sayısı + net satır).
E2E_CMD_RE = re.compile(r"(playwright|cypress|selenium|puppeteer|e2e)", re.I)
BUYUK_DOSYA = 5
BUYUK_SATIR = 150


def _run_event():
    spec = importlib.util.spec_from_file_location(
        "_re", os.path.join(HERE, "run_event.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def bu_turun_olaylari(olaylar):
    """Son 'stop'tan sonraki olaylar = içinde bulunduğumuz tur."""
    son_stop = -1
    for i, o in enumerate(olaylar):
        if o.get("kind") == "stop":
            son_stop = i
    return olaylar[son_stop + 1:]


def degisen_satir_sayisi():
    """git ile net değişen satır — olay sayımından daha güvenilir kanıt."""
    try:
        p = subprocess.run(["git", "diff", "--numstat", "HEAD"],
                           capture_output=True, text=True, cwd=ROOT, timeout=10)
        if p.returncode != 0:
            return 0
        toplam = 0
        for satir in p.stdout.splitlines():
            parca = satir.split("\t")
            if len(parca) >= 2 and parca[0].isdigit() and parca[1].isdigit():
                toplam += int(parca[0]) + int(parca[1])
        return toplam
    except Exception:
        return 0


def degerlendir(olaylar, satir_sayisi=0):
    """(bulgular, imza) — bulgu listesi boşsa tur temiz demektir."""
    tur = bu_turun_olaylari(olaylar)

    duzenlenen, son_edit_idx = [], -1
    test_olaylari, skiller = [], []
    for i, o in enumerate(tur):
        kind = o.get("kind")
        if kind == "edit" and o.get("file"):
            duzenlenen.append(o["file"])
            son_edit_idx = i
        elif kind == "test":
            test_olaylari.append((i, o))
        elif kind == "skill" and o.get("skill"):
            skiller.append(o["skill"])

    ui = [f for f in duzenlenen
          if f.lower().endswith(UI_UZANTI) or UI_YOL.search(f)]
    kaynak = [f for f in duzenlenen
              if f.lower().endswith(KAYNAK_UZANTI) and not TEST_YOL.search(f)]
    riskli = [f for f in duzenlenen if RISK_YOL.search(f)]

    imza = hashlib.sha256(
        "|".join(sorted(set(duzenlenen))).encode("utf-8")).hexdigest()[:12]

    bulgular = []
    if kaynak:
        sonrakiler = [o for i, o in test_olaylari if i > son_edit_idx]
        if not sonrakiler:
            bulgular.append((
                "BLOK", "test kanıtı yok",
                f"{len(kaynak)} kaynak dosyası değişti ama son düzenlemeden "
                f"sonra test/doğrulama koşmadı: {', '.join(kaynak[:4])}"))
        elif any(o.get("ok") is False for o in sonrakiler):
            bulgular.append((
                "BLOK", "testler kırmızı",
                "Son koşan test/doğrulama başarısız sonuç işareti taşıyor."))
        elif all(o.get("ok") is None for o in sonrakiler):
            bulgular.append((
                "UYARI", "test sonucu belirsiz",
                "Test komutu koştu ama çıktısından geçti/kaldı okunamadı."))

    if ui:
        tiklama = [o for i, o in enumerate(tur)
                   if o.get("kind") == "ui" or
                   (o.get("kind") == "test" and E2E_CMD_RE.search(o.get("cmd") or ""))]
        if not tiklama:
            bulgular.append((
                "BLOK", "tıklama kanıtı yok",
                f"Görünür yüzey değişti ({', '.join(ui[:3])}) ama kimse "
                "tıklamadı. E2E koştur ya da tarayıcıda aç-tıkla-ekran görüntüsü "
                "al. Projede E2E aracı yoksa bunu SÖYLE ve kurulum öner "
                "(python3 bin/araclar.py)."))

    if riskli and "security-review" not in skiller:
        bulgular.append((
            "BLOK", "risk yüzeyi incelenmedi",
            f"Risk yüzeyine dokunuldu ({', '.join(riskli[:3])}) ama "
            "security-review yüklenmedi. Not: skill'i yüklemek inceleme "
            "KANITI değildir; bulgular dosya:satır ile raporlanmalı."))

    if (len(kaynak) >= BUYUK_DOSYA or satir_sayisi >= BUYUK_SATIR) and kaynak:
        bulgular.append((
            "UYARI", "bağımsız inceleme önerilir",
            f"{len(kaynak)} kaynak dosyası / ~{satir_sayisi} satır değişti — "
            "bu boyut tek yazarın kendi denetimini aşar."))

    return bulgular, imza


def zaten_bloklandi(olaylar, imza):
    """Aynı diff imzası daha önce bloklandıysa tekrar bloklama (kapan yok)."""
    return any(o.get("kind") == "gate" and o.get("sig") == imza
               for o in olaylar)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=None)
    args = ap.parse_args(argv)

    try:
        payload = json.loads(sys.stdin.read() or "{}") or {}
    except (ValueError, AttributeError):
        payload = {}

    try:
        re_mod = _run_event()
        yol = args.log or re_mod.log_path()
        olaylar = []
        try:
            with open(yol, encoding="utf-8") as fh:
                for satir in fh:
                    satir = satir.strip()
                    if satir:
                        try:
                            olaylar.append(json.loads(satir))
                        except ValueError:
                            continue
        except OSError:
            olaylar = []

        bulgular, imza = degerlendir(olaylar, degisen_satir_sayisi())
        bloklar = [b for b in bulgular if b[0] == "BLOK"]
        # Sonsuz döngü koruması: hook zaten blokladıysa ya da aynı imza daha
        # önce bloklandıysa yalnız bilgi ver.
        tekrar = payload.get("stop_hook_active") or zaten_bloklandi(olaylar, imza)

        re_mod.append({"kind": "stop"}, yol)
        if bulgular:
            re_mod.append({"kind": "gate", "sig": imza,
                           "cmd": ";".join(b[1] for b in bulgular)}, yol)

        if bloklar and not tekrar:
            gerekce = "\n".join(f"[{b[0]}] {b[1]} — {b[2]}" for b in bulgular)
            print(json.dumps({
                "decision": "block",
                "reason": ("AurasAgents kapısı: kanıt olmadan tur kapanmaz.\n"
                           + gerekce +
                           "\nYap: eksik kanıtı üret (testi koştur / incelemeyi "
                           "yap), sonra bitir. Gerçekten gereksizse kullanıcıya "
                           "tek cümleyle gerekçesini söyle."),
                "systemMessage": f"⛔ kapı: {', '.join(b[1] for b in bloklar)}",
            }, ensure_ascii=False))
            return 0
        if bulgular:
            print(json.dumps({
                "systemMessage": "⚠️ kapı: " + ", ".join(b[1] for b in bulgular),
            }, ensure_ascii=False))
    except Exception:
        return 0  # kapı çökerse tur bloklanmaz — mekanizma kullanıcıyı kilitlemez
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
