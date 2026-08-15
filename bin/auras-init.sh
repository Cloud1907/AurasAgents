#!/usr/bin/env bash
# Bir projeyi AurasAgents cekirdegine baglar. Idempotent: var olan dosyalari ezmez.
#
# Kullanim:  bash /yol/AurasAgents/bin/auras-init.sh [hedef-klasor]
#            (hedef verilmezse icinde bulunulan klasor)
set -euo pipefail

SOURCE=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
TARGET=$(cd "${1:-$PWD}" && pwd)

if [ "$SOURCE" = "$TARGET" ]; then
  echo "HATA: kaynak ve hedef ayni klasor." >&2
  exit 1
fi

echo "Kaynak: $SOURCE"
echo "Hedef : $TARGET"
echo ""

# Yorumlayici secimi — pre-push kancasiyla ayni sozlesme.
# PATH'teki ilk python3 dogru olan olmayabilir (2026-08-07: Homebrew python3'u
# 3.14'e tasidi, PyYAML orada yoktu, kurulum dogrulamasi kosamadi). Yetenek
# CIKTIYLA kanitlanir: yalniz cikis koduna bakmak yetmez, `/usr/bin/true -c ...`
# argumanlari yok sayip 0 doner.
py_uygun() {
  [ -n "$1" ] || return 1
  command -v "$1" >/dev/null 2>&1 || return 1
  [ "$("$1" -c 'import yaml,sys; sys.stdout.write("AURAS_PY_OK")' 2>/dev/null)" \
    = "AURAS_PY_OK" ]
}
PY=""
if [ -n "${AURAS_PYTHON:-}" ] && py_uygun "$AURAS_PYTHON"; then
  PY=$AURAS_PYTHON
  echo "NOT: AURAS_PYTHON kullaniliyor: $PY"
fi
if [ -z "$PY" ]; then
  for c in python3 python3.13 python3.12 python3.11; do
    if py_uygun "$c"; then PY=$c; break; fi
  done
fi
if [ -z "$PY" ]; then
  echo "HATA: PyYAML tasiyan python3 bulunamadi — kurulum dogrulanamaz." >&2
  echo "Duzelt: pip3 install pyyaml   ya da: AURAS_PYTHON=<yorumlayici> ..." >&2
  exit 1
fi
echo ""

# --- Kaynak tazeligi: kurulum SON surumden yapilir ------------------------
# Kurucu dosyalari kanonik CALISMA AGACINDAN kopyalar. Agac origin'in
# gerisindeyse kurulan motor eskidir ama manifest onu "guncel" damgalar —
# kapi var, koruma yok (2026-08-15 olcumu: agac e3f1ec1, origin/main
# 2d42b90; o gun kosulacak her /auras eski niyet kapisini yayacakti).
# Guvenle ileri sarilabiliyorsa sarilir, sarilamiyorsa DURULUR.
echo "Kaynak tazeligi:"
TAZELIK=$("$PY" - "$SOURCE" <<'PYTAZE'
import os
import sys

kaynak = sys.argv[1]
sys.path.insert(0, os.path.join(kaynak, "bin"))
import kernel_dosyalari as kd

durum, mesaj = kd.kaynak_tazele(kaynak)
print(durum)
print(mesaj)
PYTAZE
)
TAZE_DURUM=$(printf '%s\n' "$TAZELIK" | head -1)
TAZE_MESAJ=$(printf '%s\n' "$TAZELIK" | tail -n +2)
echo "  $TAZE_DURUM — $TAZE_MESAJ"
if [ "$TAZE_DURUM" = "engel" ]; then
  if [ -n "${AURAS_ESKI_MOTOR:-}" ]; then
    # Bilincli atlama gorunur kalir: sessiz muafiyet, kapinin oldugu ama
    # korumadigi haldir.
    echo "  UYARI: AURAS_ESKI_MOTOR=1 — ESKI motorla kuruluyor"
  else
    echo "HATA: kaynak son surumde degil; kurulum eski motoru yayardi." >&2
    echo "Duzelt: $SOURCE icinde durumu coz (pull / rebase / stash), tekrar kos." >&2
    echo "Bilincli atlama: AURAS_ESKI_MOTOR=1 bash bin/auras-init.sh <hedef>" >&2
    exit 1
  fi
fi
echo ""

# Proje dosyalari: bir kez yazilir, ASLA ezilmez (AGENTS.md, CLAUDE.md...)
copy_new() {  # kaynak_rel hedef_rel — hedefte varsa dokunmaz
  local src="$SOURCE/$1" dst="$TARGET/$2"
  if [ -e "$dst" ]; then
    echo "  atlandi (zaten var): $2"
  else
    mkdir -p "$(dirname "$dst")"
    cp -R "$src" "$dst"
    echo "  eklendi: $2"
  fi
}

echo "Proje dosyalari (bir kez yazilir, ezilmez):"
copy_new "AGENTS.md" "AGENTS.md"
copy_new "CLAUDE.md" "CLAUDE.md"

chmod +x "$TARGET"/bin/*.sh "$TARGET"/bin/hooks/* 2>/dev/null || true


# --- Motor (kernel) dosyaları: her koşumda GÜNCELLENİR --------------------
# Ayrım: bunlar AurasAgents'ın dosyalarıdır, projenin değil. Ama projede yerel
# iş yapıldıysa EZİLMEZ — korunur ve geri-taşımaya yönlendirilir.
# Ezme kararı .kernel-manifest.json'a DEĞİL kanonik git geçmişine dayanır:
# manifest yanılabiliyordu (2026-08-05 bulgusu — 4cast'te projenin kendi
# içeriğini "el değmemiş" sanıp yerel düzeltmeyi ezmek üzereydi).
echo ""
echo "Motor dosyalari (guncelleme):"
"$PY" - "$SOURCE" "$TARGET" <<'PYSYNC'
import json
import os
import shutil
import sys

kaynak, hedef = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(kaynak, "bin"))
import kernel_dosyalari as kd      # motor listesinin TEK tanımı

manifest_yol = os.path.join(hedef, ".agents", ".kernel-manifest.json")
try:
    with open(manifest_yol, encoding="utf-8") as fh:
        manifest = json.load(fh)
except (OSError, ValueError):
    manifest = {}

eklendi, guncellendi, korundu, ayni = [], [], [], 0
for rel in kd.motor_dosyalari(kaynak):
    src, dst = os.path.join(kaynak, rel), os.path.join(hedef, rel)
    yeni_hash = kd.sha(src)
    if not os.path.exists(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        manifest[rel] = yeni_hash
        eklendi.append(rel)
        continue
    if kd.sha(dst) == yeni_hash:
        manifest[rel] = yeni_hash
        ayni += 1
    elif kd.sinifla(kaynak, hedef, rel) == "geride":
        # İçerik kanoniğin ESKİ bir sürümü → yerel iş yok, güvenle güncelle
        shutil.copy2(src, dst)
        manifest[rel] = yeni_hash
        guncellendi.append(rel)
    else:
        # Kanonik geçmişte hiç görülmemiş içerik = yerel iş → EZME
        korundu.append(rel)

os.makedirs(os.path.dirname(manifest_yol), exist_ok=True)
with open(manifest_yol, "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, indent=2, sort_keys=True)

for r in eklendi:
    print(f"  eklendi:     {r}")
for r in guncellendi:
    print(f"  guncellendi: {r}")
for r in korundu:
    print(f"  KORUNDU:     {r}  (yerel is — kanonige tasinmadi)")
print(f"  ({ayni} dosya zaten guncel)")
if korundu:
    print("")
    print(f"  {len(korundu)} dosyada yerel kernel isi var ve kanonige "
          "tasinmadi.")
    print(f"  Gor:  python3 bin/auras_geri.py {hedef} --diff")
    print(f"  Al :  python3 bin/auras_geri.py {hedef} --al {korundu[0]}")
PYSYNC

echo ""
echo "Git ve kancalar:"
cd "$TARGET"
if [ ! -d .git ]; then
  git init -b main -q
  echo "  git deposu olusturuldu"
else
  echo "  git deposu zaten var"
fi

if [ ! -e .gitignore ]; then
  printf '__pycache__/\n.DS_Store\nevidence.json\n' > .gitignore
  echo "  .gitignore eklendi"
fi

mkdir -p .claude
if [ ! -e .claude/skills ]; then
  ln -s ../.agents/skills .claude/skills
  echo "  .claude/skills baglantisi kuruldu"
fi

bash bin/install-hooks.sh

echo ""
echo "Hook'lar (.claude/settings.json — kaynaktan birlestirilir):"
"$PY" - "$SOURCE" "$TARGET" <<'PYHOOK'
import json
import os
import sys

kaynak, hedef = sys.argv[1], sys.argv[2]
# Motorun kendi hook kumesi tek dogruluk kaynagi: elle liste tutulmaz,
# kernel yeni hook eklediginde bagli projeler /auras ile onu da alir.
with open(os.path.join(kaynak, ".claude", "settings.json"), encoding="utf-8") as fh:
    kernel = json.load(fh).get("hooks", {})

yol = os.path.join(hedef, ".claude", "settings.json")
try:
    with open(yol, encoding="utf-8") as fh:
        veri = json.load(fh)
except (OSError, ValueError):
    veri = {}
if not isinstance(veri, dict):
    print("  UYARI: settings.json okunamadi, hook'lar elle eklenmeli")
    sys.exit(0)

hedef_hooks = veri.setdefault("hooks", {})
eklenen = 0
for olay, girisler in kernel.items():
    mevcut = hedef_hooks.setdefault(olay, [])
    var_komutlar = {h.get("command") for e in mevcut for h in e.get("hooks", [])}
    for giris in girisler:
        komutlar = {h.get("command") for h in giris.get("hooks", [])}
        if komutlar - var_komutlar:      # bu komut henuz kayitli degil
            mevcut.append(giris)
            eklenen += 1
os.makedirs(os.path.dirname(yol), exist_ok=True)
with open(yol, "w", encoding="utf-8") as fh:
    json.dump(veri, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
print(f"  {eklenen} hook eklendi, {sum(len(v) for v in hedef_hooks.values())} hook kayitli")
PYHOOK

# Disposable kayit repoya sizmasin (auras tekrar kosuldugunda da garanti).
if ! grep -q "^\.agents/runtime" "$TARGET/.gitignore" 2>/dev/null; then
  printf '.agents/runtime/\n' >> "$TARGET/.gitignore"
  echo "  .gitignore: .agents/runtime/ eklendi"
fi

# gitleaks kullanan projede kernel manifest'ini muaf tut. Manifest yalniz
# sha256 ozeti tasir ama generic-api-key kurali uzun hex'i anahtar sanar;
# 4cast'te bu 7 yanlis pozitif uretip CI'i bir haftadan uzun kirmizida
# tuttu. Dosyayi kernel URETTIGI icin sorun her projede tekrarlanir.
"$PY" - "$SOURCE" "$TARGET" <<'PYGL'
import os
import sys
kaynak, hedef = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(kaynak, "bin"))
import kernel_dosyalari as kd

if kd.gitleaks_kullaniyor(hedef) and not kd.manifest_muaf_mi(hedef):
    yol = os.path.join(hedef, kd.GITLEAKS_CFG)
    try:
        mevcut = open(yol, encoding="utf-8").read() if os.path.isfile(yol) else ""
    except OSError:
        mevcut = ""
    if "[allowlist]" in mevcut:
        print("  UYARI: .gitleaks.toml zaten [allowlist] tasiyor — kernel "
              "manifest muafiyetini ELLE ekle (tek [allowlist] tablosu olur)")
    else:
        with open(yol, "a", encoding="utf-8") as fh:
            fh.write(mevcut and "\n" or "")
            fh.write(kd.MUAFIYET_BLOGU)
        print("  .gitleaks.toml: kernel manifest muafiyeti eklendi")
PYGL

# Kalite tabani PROJENIN dosyasidir, motorun degil: her repo kendi mevcut
# borcuyla baslar, ratchet o noktadan itibaren buyumeyi engeller. Kurucu
# uretmezse yeni proje kurulumdan KIRMIZI cikar (4Flow, 2026-08-07) ve
# kutudan kirmizi cikan kurulum insana kapiyi bastan yok saymayi ogretir.
# VAR OLANI EZMEZ — taban yukseltmek bilincli karardir (ADR-0004).
if [ -f bin/kalite.py ] && [ ! -f .agents/kalite-baseline.json ]; then
  echo ""
  echo "Kalite tabani (mevcut borc donduruluyor):"
  "$PY" bin/kalite.py --baseline 2>&1 | tail -3
fi

echo ""
echo "Dogrulama:"
"$PY" bin/validate.py
