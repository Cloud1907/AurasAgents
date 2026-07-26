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
           "intent", "session")

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


def temizle(text):
    """Secret'ı gizle, uzunluğu kırp — kayıt yerel ama yine de veri sızdırmaz."""
    if not text:
        return text
    text = secret_re().sub("[gizlendi]", str(text)).strip()
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
    return os.path.join(base, DEFAULT_LOG)


def append(event, path=None):
    """Olayı JSONL'e ekle. Hata yutulmaz — çağıran karar verir (main yutar)."""
    path = path or log_path()
    rec = {k: v for k, v in event.items() if k in ALLOWED and v is not None}
    if "intent" in rec:
        rec["intent"] = temizle(rec["intent"])
    rec["ts"] = dt.datetime.now().isoformat(timespec="seconds")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def hook_payload():
    try:
        return json.loads(sys.stdin.read() or "{}") or {}
    except (ValueError, AttributeError):
        return {}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True,
                    choices=("route", "skill", "subagent", "stop"))
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
        elif args.kind == "subagent":
            event["agent"] = (ti.get("subagent_type") or ti.get("agentType")
                              or data.get("subagent_type"))
        append(event, args.log)
    except Exception:
        return 0  # hook asla bloklamaz
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
