#!/usr/bin/env python3
"""Run olay yazıcısı — hook'lardan gelen aktiviteyi görünür kayda çevirir.

Amaç: "hangi skill çağrıldı, ne yapıldı" sorusu ajanın BEYANINDAN değil,
makine kaydından cevaplanabilsin.

Hook kullanımı (.claude/settings.json):
  PostToolUse/Skill  → run_event.py --kind skill      (hangi skill yüklendi)
  SubagentStop       → run_event.py --kind subagent   (hangi rol çağrıldı)
  Stop               → run_event.py --kind stop       (tur kapandı)
  (route olayını bin/route.py kendisi yazar)

Kayıt yeri: `.agents/runtime/events.jsonl` — gitignore'lu, **disposable**.
Hafıza otoritesinin 3. katmanı gibi davranır: hiçbir iş doğru çalışmak için
buna bağımlı olamaz (AGENTS.md hafıza otoritesi).

Tasarım kuralı: hook asla bloklamaz. Her hata yolunda exit 0.
"""
import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_LOG = os.path.join(".agents", "runtime", "events.jsonl")
INTENT_MAX = 80

# Diske yazılmasına izin verilen alanlar (allowlist — prompt/araç çıktısı yok).
ALLOWED = ("kind", "skill", "agent", "routed", "extras", "task_class",
           "intent", "session", "file", "cmd", "ok", "sig")

_FALLBACK_SECRET = re.compile(
    r"(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}"
    r"|xox[baprs]-[0-9A-Za-z-]{10,}"
    r"|eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,})", re.I)


def secret_re():
    """Secret deseni memory_hygiene'den paylaşılır (tek tanım, DRY)."""
    try:
        spec = importlib.util.spec_from_file_location(
            "_mh", os.path.join(HERE, "memory_hygiene.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.SECRET_RE
    except Exception:
        return _FALLBACK_SECRET


# Düz metin kimlik bilgisi/PII — sohbette geçebilir, diske GİRMEMELİ.
# (security-review bulgusu: memory_hygiene regex'i yalnız tırnaklı parolayı
# ve bilinen token biçimlerini yakalıyordu; "password: hunter2", "şifre X",
# TC kimlik no ve e-posta sızıyordu.)
PII_RE = re.compile(
    r"("
    # Türkçe ek alabilir: parola/parolam/parolası, şifre/şifresi/şifremiz…
    r"(?:parola|şifre|sifre|password|passwd|pwd|secret|api[\s_-]?key|token)\w*"
    r"\s*(?:[:=]|\s)\s*['\"]?\S{4,}"          # anahtar kelime + değer
    r"|\b\d{11}\b"                             # TC kimlik no
    r"|\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b"        # e-posta
    r"|\b(?:\d[ -]?){13,19}\b"                # kart numarası benzeri dizi
    r")", re.I)


def temizle(text):
    """Secret + düz metin kimlik bilgisini gizle, uzunluğu kırp.

    Kayıt yerel ve gitignore'lu olsa bile veri sızdırmaz: makineye erişen
    biri bu dosyadan kimlik bilgisi toplayamamalı.
    """
    if not text:
        return text
    text = secret_re().sub("[gizlendi]", str(text))
    text = PII_RE.sub("[gizlendi]", text).strip()
    text = " ".join(text.split())
    return text[:INTENT_MAX] + "…" if len(text) > INTENT_MAX else text


def log_path(explicit=None, pdir=None):
    """Kayıt yolu: açık argüman > AURAS_EVENT_LOG env > proje varsayılanı.

    Env override'ın nedeni izolasyon: test ve `bin/validate.py` router'ı gerçek
    isteklerle koşturur; bu koşumlar kullanıcının aktivite kaydını KİRLETMEMELİ.
    """
    if explicit:
        return explicit
    env = os.environ.get("AURAS_EVENT_LOG")
    if env:
        return env
    base = pdir or os.environ.get("CLAUDE_PROJECT_DIR") or ROOT
    # YABANCI REPOYA YAZMA. Global router her projede çalışır; sisteme bağlı
    # olmayan bir repoya kayıt bırakmak orada untracked dosya üretir ve
    # sohbet metni yanlışlıkla commit'lenebilir (gerçek vaka: 4cast/4Flow).
    # Bağlı proje = kendi routing.yml'ini taşıyan proje.
    if os.path.isfile(os.path.join(base, ".agents", "routing.yml")):
        return os.path.join(base, DEFAULT_LOG)
    slug = re.sub(r"[^A-Za-z0-9]+", "-", os.path.abspath(base)).strip("-")[-60:]
    return os.path.expanduser(os.path.join(
        "~", ".claude", "auras", "runtime", f"{slug or 'bilinmeyen'}.jsonl"))


def append(event, path=None):
    """Olayı JSONL'e ekle. Hata yutulmaz — çağıran karar verir (main yutar)."""
    path = path or log_path()
    rec = {k: v for k, v in event.items() if k in ALLOWED and v is not None}
    if "intent" in rec:
        # AURAS_LOG_INTENT=0 → istek metni hiç yazılmaz (en katı gizlilik);
        # skill/sınıf kaydı yine tutulur, tablo çalışmaya devam eder.
        if os.environ.get("AURAS_LOG_INTENT") == "0":
            rec.pop("intent")
        else:
            rec["intent"] = temizle(rec["intent"])
    rec["ts"] = dt.datetime.now().isoformat(timespec="seconds")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


# Test/doğrulama komutu imzaları (koştu mu?) ve sonuç göstergeleri (geçti mi?).
TEST_CMD_RE = re.compile(
    r"(unittest|pytest|\bnpm (run )?test|yarn test|dotnet test|go test|vitest"
    r"|jest|playwright|cypress|selenium|puppeteer|validate\.py|scan_secrets\.py|check_citations\.py)", re.I)
BASARISIZ_RE = re.compile(r"(FAILED|Traceback|✗|AssertionError|ERROR:|hata)", re.I)
BASARILI_RE = re.compile(r"(\bOK\b|passed|geçti|✓|SONUÇ: TEMİZ)", re.I)


def test_gecti(tool_response):
    """Test çıktısından sonuç çıkar: True/False/None(belirsiz).

    Heuristik ve bilinçli olarak muhafazakâr: belirsizse None döner, kapı da
    belirsizi 'kanıt yok' saymaz ama 'geçti' de saymaz — kullanıcıya söyler.
    """
    if not isinstance(tool_response, dict):
        return None
    metin = " ".join(str(tool_response.get(k, "")) for k in
                     ("stdout", "stderr", "output", "content"))[-4000:]
    if not metin.strip():
        return None
    if BASARISIZ_RE.search(metin):
        return False
    if BASARILI_RE.search(metin):
        return True
    return None


def hook_payload():
    try:
        return json.loads(sys.stdin.read() or "{}") or {}
    except (ValueError, AttributeError):
        return {}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True,
                    choices=("route", "skill", "subagent", "stop", "edit",
                             "bash", "ui"))
    ap.add_argument("--log", default=None)
    args = ap.parse_args(argv)

    try:
        data = hook_payload()
        ti = data.get("tool_input") or {}
        event = {"kind": args.kind, "session": (data.get("session_id") or "")[:8]}
        if args.kind == "skill":
            event["skill"] = ti.get("skill") or ti.get("name")
            if not event["skill"]:
                return 0  # adsız skill olayı bilgi taşımaz — gürültü yazma
        elif args.kind == "edit":
            # Hangi dosya değişti — "kanıtsız bitiş" kapısının girdisi.
            event["file"] = ti.get("file_path") or ti.get("path")
            if not event["file"]:
                return 0
        elif args.kind == "bash":
            # Test/doğrulama komutu koştu mu ve GEÇTİ Mİ — beyan değil kanıt.
            cmd = (ti.get("command") or "")[:200]
            if not TEST_CMD_RE.search(cmd):
                return 0  # sıradan komut; gürültü yazma
            event["kind"] = "test"
            event["cmd"] = cmd
            event["ok"] = test_gecti(data.get("tool_response"))
        elif args.kind == "ui":
            # Tarayıcıda gerçek etkileşim (tıklama/ekran görüntüsü) = kanıt.
            event["cmd"] = (data.get("tool_name") or "")[:80]
        elif args.kind == "subagent":
            event["agent"] = (ti.get("subagent_type") or ti.get("agentType")
                              or data.get("subagent_type"))
        append(event, args.log)
    except Exception:
        return 0  # hook asla bloklamaz
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
