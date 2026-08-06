#!/usr/bin/env python3
"""Deterministik kod kalitesi ölçümü + ratchet (kötüleşemez) kapısı.

Neden: "temiz kod" yazılı bir tavsiyeydi, ölçülmüyordu. Ölçülmeyen kuralın
standardı yoktur, tercihi vardır. Bu araç LLM yorumu ÜRETMEZ — yalnız sayar.
Sayılar ratchet ile kilitlenir: mevcut borç kabul edilir ama BÜYÜYEMEZ.

Dürüstlük sınırı: fonksiyon analizi Python (girinti) ve süslü-parantezli
diller için yapılır; diğerlerinde yalnız dosya satırı sayılır. Kapsam her
raporda yazılır — ölçülmeyen şeyi ölçülmüş gibi göstermez.

Kullanım:
  python3 bin/kalite.py                 # insan raporu
  python3 bin/kalite.py --json          # makine çıktısı
  python3 bin/kalite.py --baseline      # mevcut durumu ratchet tabanı yap
  python3 bin/kalite.py --check         # eşik + ratchet; regresyonda exit 1

Eşikler: .agents/kalite.yml (proje sahibi; yoksa aşağıdaki varsayılanlar).
Taban  : .agents/kalite-baseline.json (proje sahibi; motor ezmez).
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABAN_YOL = os.path.join(ROOT, ".agents", "kalite-baseline.json")
AYAR_YOL = os.path.join(ROOT, ".agents", "kalite.yml")

VARSAYILAN = {
    "max_dosya_satir": 400,
    "max_fonksiyon_satir": 50,
    "max_dal": 10,
}

KOD_UZANTI = {".py", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte",
              ".cs", ".go", ".java", ".rb", ".php", ".kt", ".swift", ".rs"}
# Fonksiyon gövdesi süslü parantezle sınırlanan diller. Ruby (def…end) ve
# Python burada DEĞİL — "hepsi analiz edildi" demek dürüst olmazdı; analiz
# edilmeyen dosya kapsam raporunda 'yalnız satır sayılan' olarak görünür.
SUSLU = {".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".cs", ".go",
         ".java", ".php", ".kt", ".swift", ".rs"}
ATLA = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist",
        "build", ".next", "obj", "coverage", "vendor", "Pods", ".mypy_cache",
        ".pytest_cache", "site-packages", ".agents/runtime"}

PY_FONK = re.compile(r"^(\s*)(?:async\s+)?def\s+\w+")
JS_FONK = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:function\s+\w+|"
    r"(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?\([^)]*\)\s*=>|"
    r"(?:public|private|protected|internal|static|\s)*[\w<>\[\],\s]+\s+\w+\s*\([^;]*\)\s*\{)")
DAL = re.compile(r"(?<![\w.])(if|elif|else\s+if|for|while|case|catch|except)"
                 r"(?![\w])|&&|\|\||\?\?|\?[^.:]")
BORC = re.compile(r"(?<![\w])(TODO|FIXME|XXX|HACK)(?![\w])")
# Desen parçalı kurulur: düz yazılırsa bu dosyanın KENDİSİ bulgu üretir
# (tarayıcının kendini yakalaması — tests/test_skill_validators.py'deki
# secret konvansiyonuyla aynı).
DEBUG = re.compile(r"console\.(log|debug)\s*\(|(?<![\w])" + "debug" + r"ger(?![\w])")


def ayarlar():
    esik = dict(VARSAYILAN)
    if os.path.isfile(AYAR_YOL):
        try:
            import yaml
            veri = yaml.safe_load(open(AYAR_YOL, encoding="utf-8")) or {}
            for k in VARSAYILAN:
                if isinstance(veri.get(k), int):
                    esik[k] = veri[k]
        except Exception:
            pass          # ayar okunamazsa varsayılan; ölçüm durmaz
    return esik


def kod_dosyalari(kok):
    for dizin, altlar, isimler in os.walk(kok):
        altlar[:] = [d for d in altlar if d not in ATLA and not
                     os.path.join(os.path.relpath(dizin, kok), d)
                     .replace(os.sep, "/").startswith(".agents/runtime")]
        for i in isimler:
            if os.path.splitext(i)[1] in KOD_UZANTI:
                yield os.path.join(dizin, i)


def py_fonksiyonlar(satirlar):
    """(ad_satiri, uzunluk, dal_sayisi) — girinti tabanlı, Python."""
    sonuc = []
    for i, s in enumerate(satirlar):
        m = PY_FONK.match(s)
        if not m:
            continue
        girinti = len(m.group(1))
        son = i
        for j in range(i + 1, len(satirlar)):
            t = satirlar[j]
            if not t.strip():
                continue
            mevcut = len(t) - len(t.lstrip())
            if mevcut <= girinti:
                break
            son = j
        govde = satirlar[i:son + 1]
        sonuc.append((i + 1, len(govde), len(DAL.findall("\n".join(govde)))))
    return sonuc


def suslu_fonksiyonlar(satirlar):
    """(ad_satiri, uzunluk, dal_sayisi) — süslü parantez eşleme."""
    sonuc = []
    for i, s in enumerate(satirlar):
        if not JS_FONK.match(s) or s.strip().endswith(";"):
            continue
        derinlik, basladi, son = 0, False, i
        for j in range(i, len(satirlar)):
            derinlik += satirlar[j].count("{") - satirlar[j].count("}")
            if "{" in satirlar[j]:
                basladi = True
            son = j
            if basladi and derinlik <= 0:
                break
        govde = satirlar[i:son + 1]
        if len(govde) > 1:
            sonuc.append((i + 1, len(govde),
                          len(DAL.findall("\n".join(govde)))))
    return sonuc


def olc(kok=ROOT, esik=None):
    esik = esik or ayarlar()
    sayac = {"buyuk_dosya": 0, "uzun_fonksiyon": 0, "karmasik_fonksiyon": 0,
             "borc_isareti": 0, "debug_artigi": 0}
    bulgular = []
    dosya_sayisi = fonk_analizli = 0
    for yol in sorted(kod_dosyalari(kok)):
        rel = os.path.relpath(yol, kok)
        try:
            with open(yol, encoding="utf-8", errors="replace") as fh:
                metin = fh.read()
        except OSError:
            continue
        satirlar = metin.splitlines()
        dosya_sayisi += 1

        if len(satirlar) > esik["max_dosya_satir"]:
            sayac["buyuk_dosya"] += 1
            bulgular.append((rel, 1, "buyuk_dosya",
                             f"{len(satirlar)} satır (> {esik['max_dosya_satir']})"))
        n = len(BORC.findall(metin))
        sayac["borc_isareti"] += n
        d = len(DEBUG.findall(metin))
        sayac["debug_artigi"] += d
        if d:
            bulgular.append((rel, 1, "debug_artigi", f"{d} adet"))

        uzanti = os.path.splitext(yol)[1]
        if uzanti == ".py":
            fonklar = py_fonksiyonlar(satirlar)
        elif uzanti in SUSLU:
            fonklar = suslu_fonksiyonlar(satirlar)
        else:
            continue
        fonk_analizli += 1
        for satir, uzunluk, dal in fonklar:
            if uzunluk > esik["max_fonksiyon_satir"]:
                sayac["uzun_fonksiyon"] += 1
                bulgular.append((rel, satir, "uzun_fonksiyon",
                                 f"{uzunluk} satır (> {esik['max_fonksiyon_satir']})"))
            if dal > esik["max_dal"]:
                sayac["karmasik_fonksiyon"] += 1
                bulgular.append((rel, satir, "karmasik_fonksiyon",
                                 f"{dal} dal (> {esik['max_dal']})"))
    return {
        "sayaclar": sayac,
        "esikler": esik,
        "kapsam": {"kod_dosyasi": dosya_sayisi,
                   "fonksiyon_analizli": fonk_analizli,
                   "yalniz_satir_sayilan": dosya_sayisi - fonk_analizli},
        "bulgular": [{"dosya": d, "satir": s, "tur": t, "detay": x}
                     for d, s, t, x in bulgular],
    }


def taban_oku():
    try:
        with open(TABAN_YOL, encoding="utf-8") as fh:
            return json.load(fh).get("sayaclar", {})
    except (OSError, ValueError):
        return None


def regresyonlar(sayac, taban):
    """Ratchet: hiçbir sayaç tabandan BÜYÜK olamaz."""
    return [(k, taban.get(k, 0), v) for k, v in sorted(sayac.items())
            if v > taban.get(k, 0)]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--baseline", action="store_true",
                    help="mevcut ölçümü ratchet tabanı olarak yaz")
    ap.add_argument("--check", action="store_true",
                    help="ratchet regresyonunda exit 1")
    ap.add_argument("--path", default=ROOT)
    args = ap.parse_args(argv)

    rapor = olc(args.path)
    taban = taban_oku()

    if args.baseline:
        os.makedirs(os.path.dirname(TABAN_YOL), exist_ok=True)
        with open(TABAN_YOL, "w", encoding="utf-8") as fh:
            json.dump({"sayaclar": rapor["sayaclar"],
                       "not": "Ratchet tabanı: sayaçlar bunun üstüne çıkamaz. "
                              "Düşürmek serbest ve teşvik edilir."},
                      fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n")
        print(f"kalite: taban yazıldı → {os.path.relpath(TABAN_YOL, ROOT)}")
        return 0

    kotu = regresyonlar(rapor["sayaclar"], taban) if taban is not None else []
    rapor["taban"] = taban
    rapor["regresyon"] = [{"sayac": k, "taban": a, "simdi": b}
                          for k, a, b in kotu]

    if args.json:
        print(json.dumps(rapor, ensure_ascii=False, indent=2))
        return 1 if (args.check and kotu) else 0

    kap = rapor["kapsam"]
    print(f"KALİTE: {kap['kod_dosyasi']} kod dosyası "
          f"({kap['fonksiyon_analizli']} fonksiyon-analizli, "
          f"{kap['yalniz_satir_sayilan']} yalnız satır sayıldı)")
    for k, v in sorted(rapor["sayaclar"].items()):
        t = "—" if taban is None else taban.get(k, 0)
        isaret = "✗" if (taban is not None and v > taban.get(k, 0)) else " "
        print(f"  {isaret} {k:20} {v:4}   (taban: {t})")
    if taban is None:
        print("\n  Taban yok — ratchet kapalı. Kur: python3 bin/kalite.py --baseline")
    elif kotu:
        print("\n  RATCHET İHLALİ — sayaç tabanın üstüne çıktı:")
        for k, a, b in kotu:
            print(f"    {k}: {a} → {b}")
        print("  Ya borcu geri al ya da tabanı bilinçli yükselt "
              "(gerekçesini commit mesajına yaz).")
    for b in rapor["bulgular"][:12]:
        print(f"    {b['dosya']}:{b['satir']}  [{b['tur']}]  {b['detay']}")
    if len(rapor["bulgular"]) > 12:
        print(f"    … {len(rapor['bulgular']) - 12} bulgu daha (--json)")
    return 1 if (args.check and kotu) else 0


if __name__ == "__main__":
    raise SystemExit(main())
