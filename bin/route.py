#!/usr/bin/env python3
"""Skill router — istek metninden görev sınıfı + skill seçimi üretir.

UserPromptSubmit hook'u olarak çalışır: stdin'den hook JSON'unu okur,
stdout'a Claude Code hook JSON'u basar (additionalContext + systemMessage).

İki kurulum biçimi:
  1. Proje bazlı — projenin `.claude/settings.json`'ı kendi `bin/route.py`'sini
     çağırır (repoyla taşınır, klonlayan herkeste çalışır).
  2. Global yedek — `~/.claude/settings.json` kanonik route.py'yi
     `--global-fallback` ile çağırır: her projede çalışır, ama projenin kendi
     router hook'u varsa sessizce çekilir (çift yönlendirme olmaz).

Yönlendirme tablosu sırası: `$CLAUDE_PROJECT_DIR/.agents/routing.yml` →
CWD'den yukarı yürüyerek bulunan proje → kanonik AurasAgents tablosu.

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
CANONICAL = os.path.join(ROOT, ".agents", "routing.yml")

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


def project_dir():
    """Aktif projenin kökü: hook env'i, yoksa CWD'den yukarı arama."""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and os.path.isdir(env):
        return os.path.abspath(env)
    cur = os.getcwd()
    while True:
        if os.path.isdir(os.path.join(cur, ".agents")) or \
           os.path.isdir(os.path.join(cur, ".git")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return os.getcwd()
        cur = parent


def routing_path(pdir=None):
    """(tablo yolu, projeye mi ait) — proje tablosu kanonik olanı yener."""
    pdir = pdir or project_dir()
    local = os.path.join(pdir, ".agents", "routing.yml")
    if os.path.isfile(local):
        return local, True
    return CANONICAL, False


def load_rules(path=None):
    import yaml  # yoksa ImportError → main() sessizce çıkar
    with open(path or routing_path()[0], encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def skill_installed(skill, pdir):
    """Skill bu projede ya da kullanıcı-global dizinde kurulu mu."""
    for base in (os.path.join(pdir, ".agents", "skills"),
                 os.path.join(pdir, ".claude", "skills"),
                 os.path.expanduser("~/.claude/skills")):
        if os.path.isdir(os.path.join(base, skill)):
            return True
    return False


def project_registers_router(pdir):
    """Proje kendi router hook'unu kaydetmiş mi (global yedek geri çekilir)."""
    try:
        with open(os.path.join(pdir, ".claude", "settings.json"),
                  encoding="utf-8") as fh:
            return "route.py" in fh.read()
    except OSError:
        return False


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


def render(prompt, cfg, pdir=None, table_is_local=True):
    task_class, primary, extras, hits, explicit = route(prompt, cfg)
    pdir = pdir or project_dir()
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

    if not table_is_local:
        lines.append(
            "Not: bu proje kendi routing.yml'ini taşımıyor, kanonik AurasAgents "
            "tablosu kullanıldı.")
    eksik = [s for s in ([primary["skill"]] if primary else []) + extras
             if not skill_installed(s, pdir)]
    if eksik:
        lines.append(
            f"Uyarı: {', '.join(eksik)} bu projede kurulu değil — /auras ile "
            "bağla, ya da kurulu olmadığını kullanıcıya söyleyip skill'siz çalış.")

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


def _kaydet(prompt, cfg, pdir):
    """Yönlendirme kararını görünür kayda yaz (best-effort; asla bloklamaz).

    Böylece `bin/durum.py` "ne yönlendirildi vs ne yüklendi" karşılaştırmasını
    ajanın beyanına değil kayda dayandırır.
    """
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "_run_event", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "run_event.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        task_class, primary, extras, _hits, explicit = route(prompt, cfg)
        mod.append({
            "kind": "route",
            "task_class": task_class,
            "routed": (primary or {}).get("skill") or (explicit if explicit else None),
            "extras": extras,
            "intent": prompt,
        }, mod.log_path(pdir=pdir))
    except Exception:
        pass


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    pdir = project_dir()
    # Global yedek, projenin kendi router'ı varsa devreye girmez.
    if "--global-fallback" in argv and project_registers_router(pdir):
        return 0
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
        table, is_local = routing_path(pdir)
        cfg = load_rules(table)
        context, summary = render(prompt, cfg, pdir, is_local)
    except Exception:
        return 0  # yönlendirme yardımdır; asla isteği bloklamaz
    _kaydet(prompt, cfg, pdir)
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
