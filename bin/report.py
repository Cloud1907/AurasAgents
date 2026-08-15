#!/usr/bin/env python3
"""Sistem hafızası raporunu CANLI veriden üretir → docs/sistem-hafizasi.html

Donmuş ekran görüntüsü değil: her koşuda git geçmişi, dosya sayıları ve
(varsa) CI durumu yeniden okunur. Kanıt > beyan — rapor o anki gerçeği gösterir.

Kullanım:
  python3 bin/report.py               # docs/sistem-hafizasi.html üret
  python3 bin/report.py --open        # üret ve tarayıcıda aç (macOS)
"""
import argparse
import glob
import html
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "sistem-hafizasi.html")

CHIP = {  # skill → (etiket, sınıf)
    "implement-change": ("kod", "g"),
    "security-review": ("güvenlik", "g"),
    "designing-interfaces": ("tasarım", "g"),
    "research-with-evidence": ("araştırma", "g"),
    "auras": ("global", "v"),
}


def sh(args):
    try:
        return subprocess.check_output(args, cwd=ROOT, text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def counts():
    sk = glob.glob(os.path.join(ROOT, ".agents/skills/*/SKILL.md"))
    return {
        "skill": len(sk),
        "referans": len(glob.glob(os.path.join(ROOT, ".agents/skills/*/references/*.md"))),
        "validator": len(glob.glob(os.path.join(ROOT, ".agents/skills/*/scripts/*.py"))),
        "kural": len(glob.glob(os.path.join(ROOT, ".claude/rules/*.md"))),
        "profil": len(glob.glob(os.path.join(ROOT, ".agents/capability-profiles/*.yml"))),
        "commit": sh(["git", "rev-list", "--count", "HEAD"]) or "0",
        "dosya": len([x for x in sh(["git", "ls-files"]).splitlines() if x]),
    }


def ci_status():
    """displayTitle → conclusion (best-effort; gh yoksa boş)."""
    raw = sh(["gh", "run", "list", "--limit", "40",
              "--json", "conclusion,displayTitle"])
    out = {}
    if raw:
        try:
            for r in json.loads(raw):
                out.setdefault(r["displayTitle"], r["conclusion"])
        except Exception:
            pass
    return out


def timeline(ci):
    log = sh(["git", "log", "--format=%h|%ad|%s", "--date=format:%H:%M"])
    rows = []
    for line in log.splitlines():
        parts = line.split("|", 2)
        if len(parts) != 3:
            continue
        sha, tm, msg = parts
        concl = ci.get(msg)
        if concl == "success":
            badge = ('<div class="badge pass">CI ✓</div>')
        elif concl == "failure":
            badge = ('<div class="badge fail">CI ✗</div>')
        else:
            badge = ('<div class="badge neutral">—</div>')
        rows.append(
            f'<div class="row"><div class="t">{html.escape(tm)}</div>'
            f'<div class="body"><div class="msg">{html.escape(msg)}</div>'
            f'<div class="meta mono">{html.escape(sha)}</div></div>{badge}</div>')
    return "\n".join(reversed(rows))  # kronolojik (eski→yeni)


def first_sentence(desc):
    desc = re.sub(r"\s+", " ", desc).strip()
    # frontmatter description'ın ilk cümlesi (— veya . öncesi)
    m = re.split(r"[—.]", desc, 1)
    return m[0].strip()[:90]


def skill_cards():
    cards = []
    for d in sorted(glob.glob(os.path.join(ROOT, ".agents/skills/*"))):
        name = os.path.basename(d)
        md = os.path.join(d, "SKILL.md")
        if not os.path.isfile(md):
            continue
        text = open(md, encoding="utf-8").read()
        m = re.search(r"description:\s*(.+)", text)
        desc = first_sentence(m.group(1)) if m else ""
        scripts = glob.glob(os.path.join(d, "scripts/*.py"))
        foot = ("✓ " + os.path.basename(scripts[0])) if scripts else "↳ kernel"
        label, cls = CHIP.get(name, ("skill", "g"))
        cards.append(
            f'<div class="card"><div class="top">'
            f'<span class="name">{html.escape(name)}</span>'
            f'<span class="chip {cls}">{label}</span></div>'
            f'<div class="desc">{html.escape(desc)}.</div>'
            f'<div class="foot">{html.escape(foot)}</div></div>')
    return "\n".join(cards)


def render():
    c = counts()
    ci = ci_status()
    stat_cells = "".join(
        f'<div class="stat"><div class="n">{c[k]}</div>'
        f'<div class="l">{lbl}</div></div>'
        for k, lbl in [("skill", "skill"), ("referans", "referans"),
                       ("validator", "validator"), ("kural", "domain kuralı"),
                       ("profil", "profil"), ("commit", "commit"),
                       ("dosya", "dosya")])
    tpl = open(os.path.join(os.path.dirname(__file__),
                            "report_template.html"), encoding="utf-8").read()
    return (tpl
            .replace("{{STATS}}", stat_cells)
            .replace("{{SKILLS}}", skill_cards())
            .replace("{{TIMELINE}}", timeline(ci)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--open", action="store_true")
    args = ap.parse_args()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(render())
    print(f"rapor üretildi: {os.path.relpath(OUT, ROOT)}")
    if args.open and sys.platform == "darwin":
        subprocess.run(["open", OUT])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
