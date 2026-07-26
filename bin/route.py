#!/usr/bin/env python3
"""Skill router — istek metninden görev sınıfı + skill seçimi üretir.

UserPromptSubmit hook'u olarak çalışır: stdin'den hook JSON'unu okur,
stdout'a Claude Code hook JSON'u basar (additionalContext + systemMessage).

Elle deneme:
    echo '{"prompt":"login endpointine rate limit ekle"}' | python3 bin/route.py

Tasarım kuralı: bu betik ASLA isteği bloklamaz. Hata/eksik bağımlılık
durumunda sessizce exit 0 döner — yönlendirme yardımdır, kapı değildir.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUTING = os.path.join(ROOT, ".agents", "routing.yml")

# Türkçe küçük harf: I → ı (str.lower() bunu yapmaz).
TR_LOWER = str.maketrans("IİĞÜŞÖÇ", "iiğüşöç")


def normalize(text):
    return text.translate(TR_LOWER).lower()


def tokenize(text):
    return [t for t in re.split(r"[^0-9a-zçğıöşü_.]+", text) if t]


def matches(trigger, text, tokens):
    """Boşluklu tetik alt-dize; tek kelime tetik, kelime başı eşleşmesi."""
    if " " in trigger:
        return trigger in text
    return any(tok.startswith(trigger) for tok in tokens)


def load_rules():
    import yaml  # yoksa ImportError → main() sessizce çıkar
    with open(ROUTING, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _extras(cfg, text, tokens):
    """Risk yüzeyi eşleşmesiyle daima eklenen skill'ler."""
    out = []
    for rule in cfg.get("always_add", []):
        if any(matches(normalize(t), text, tokens)
               for t in rule.get("triggers", [])):
            out.append(rule["skill"])
    return out


def route(prompt, cfg):
    """(task_class, primary, extras, hits, explicit) döndürür."""
    text = normalize(prompt)
    tokens = tokenize(text)

    explicit = None
    m = re.match(r"^\s*/([a-z0-9-]+)", prompt.strip())
    if m:
        explicit = m.group(1)

    scored = []
    for rule in cfg.get("rules", []):
        hit = [t for t in rule.get("triggers", [])
               if matches(normalize(t), text, tokens)]
        # Açık /komut o kuralı doğrudan seçer (tetik aramaya gerek yok).
        if explicit and explicit == rule.get("skill"):
            return (rule.get("task_class", "research"), rule,
                    [s for s in _extras(cfg, text, tokens)
                     if s != rule["skill"]], hit or [f"/{explicit}"], explicit)
        if hit:
            scored.append((len(hit), rule.get("specificity", 1), rule, hit))
    # Puan → özgüllük → routing.yml sırası (kararlı sonuç).
    scored.sort(key=lambda s: (-s[0], -s[1]))

    extras = _extras(cfg, text, tokens)

    if not scored:
        fb = cfg.get("fallback", {})
        return fb.get("task_class", "research"), None, extras, [], explicit

    _score, _spec, top, hit = scored[0]
    for _s, _sp, rule, _h in scored[1:]:
        if rule["skill"] not in extras:
            extras.append(rule["skill"])
    extras = [s for s in extras if s != top["skill"]]
    return top.get("task_class", "research"), top, extras, hit, explicit


def render(prompt, cfg):
    task_class, primary, extras, hits, explicit = route(prompt, cfg)
    profile = os.path.join(".agents", "capability-profiles", f"{task_class}.yml")
    lines = ["[AurasAgents router]"]

    if explicit:
        lines.append(f"Kullanıcı açıkça /{explicit} istedi — onu yükle.")

    lines.append(f"Görev sınıfı: {task_class}  |  profil: {profile}")

    if primary:
        lines.append(
            f"ZORUNLU skill: {primary['skill']} "
            f"(ön risk: {primary.get('risk', 'auto')}; "
            f"eşleşen tetik: {', '.join(hits[:4])})")
    else:
        lines.append("Eşleşen skill yok.")
        msg = cfg.get("fallback", {}).get("message")
        if msg:
            lines.append(msg.strip())

    if extras:
        lines.append(f"Ek skill: {', '.join(extras)}")

    lines.append(
        "Kural: yönlendirilen skill'i Skill aracıyla YÜKLEMEDEN işe başlama. "
        "Yönlendirme yanlışsa tek cümleyle gerekçelendir ve kullanıcıya söyle "
        "— sessizce atlama.")

    context = "\n".join(lines)
    picked = primary["skill"] if primary else "—"
    if explicit:
        picked = f"/{explicit}"
    summary = f"router → {task_class} · {picked}"
    if extras:
        summary += f" (+{len(extras)})"
    return context, summary


def main():
    try:
        raw = sys.stdin.read()
    except Exception:
        return 0
    try:
        prompt = (json.loads(raw or "{}") or {}).get("prompt", "")
    except (ValueError, AttributeError):
        prompt = raw
    if not prompt or not prompt.strip():
        return 0
    try:
        cfg = load_rules()
        context, summary = render(prompt, cfg)
    except Exception:
        return 0  # yönlendirme yardımdır; asla isteği bloklamaz
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        },
        "systemMessage": summary,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
