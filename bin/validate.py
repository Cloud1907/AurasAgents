#!/usr/bin/env python3
"""Kernel conformance testleri — skill, profil, form, şema ve evidence tutarlılığı.

Koşum: python3 bin/validate.py   (exit 0 = geçti)
"""
import json
import os
import re
import subprocess
import sys
import tempfile

try:
    import yaml
except ImportError:
    print("HATA: PyYAML gerekli (pip install pyyaml)")
    sys.exit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ERRORS = []


def err(msg):
    ERRORS.append(msg)


def check(cond, msg):
    if not cond:
        err(msg)


def frontmatter(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    return yaml.safe_load(m.group(1))


def test_skills():
    skills_dir = os.path.join(ROOT, ".agents", "skills")
    names = []
    for d in sorted(os.listdir(skills_dir)):
        full = os.path.join(skills_dir, d)
        if not os.path.isdir(full):
            continue
        md = os.path.join(full, "SKILL.md")
        check(os.path.isfile(md), f"skill '{d}': SKILL.md yok")
        if not os.path.isfile(md):
            continue
        fm = frontmatter(md)
        check(fm is not None, f"skill '{d}': frontmatter yok/bozuk")
        if fm:
            check(fm.get("name") == d,
                  f"skill '{d}': frontmatter name '{fm.get('name')}' dizinle uyuşmuyor")
            desc = fm.get("description", "")
            check(len(desc) >= 40,
                  f"skill '{d}': description çok kısa (seçim sinyali zayıf)")
            check("kullan" in desc.lower(),
                  f"skill '{d}': description ne zaman kullanılacağını söylemiyor")
        body = open(md, encoding="utf-8").read()
        for section in ("## Prosedür", "## Gotcha", "## Eval"):
            check(section in body, f"skill '{d}': '{section}' bölümü eksik")
        names.append(d)
    check(len(names) >= 4, f"en az 4 çekirdek skill bekleniyor, {len(names)} var")
    return set(names)


def test_profiles(skill_names):
    prof_dir = os.path.join(ROOT, ".agents", "capability-profiles")
    required_classes = {"code-change", "research", "incident"}
    seen = set()
    for f in sorted(os.listdir(prof_dir)):
        if not f.endswith(".yml"):
            continue
        path = os.path.join(prof_dir, f)
        data = yaml.safe_load(open(path, encoding="utf-8"))
        tc = data.get("task_class")
        seen.add(tc)
        check(f == f"{tc}.yml", f"profil {f}: dosya adı task_class ile uyuşmuyor")
        for key in ("schema_version", "skills", "tools", "network",
                    "evidence_required", "risk"):
            check(key in data, f"profil {f}: '{key}' alanı eksik")
        for s in data.get("skills", []):
            check(s in skill_names,
                  f"profil {f}: tanımsız skill '{s}' (kayıtlı: {sorted(skill_names)})")
        risk = data.get("risk", {})
        check(risk.get("escalation") == "upward_only",
              f"profil {f}: risk.escalation 'upward_only' olmalı")
        net = data.get("network", {})
        check(net.get("mode") in ("allowlist", "open-web", "none"),
              f"profil {f}: geçersiz network.mode '{net.get('mode')}'")
    check(seen >= required_classes,
          f"eksik profil sınıfı: {required_classes - seen}")


def test_issue_form():
    path = os.path.join(ROOT, ".github", "ISSUE_TEMPLATE", "work-contract.yml")
    check(os.path.isfile(path), "work-contract.yml issue form yok")
    if not os.path.isfile(path):
        return
    data = yaml.safe_load(open(path, encoding="utf-8"))
    ids = {b.get("id") for b in data.get("body", []) if isinstance(b, dict)}
    for needed in ("hedef", "gorev-sinifi", "kriterler", "kapsam",
                   "on-risk", "kanit"):
        check(needed in ids, f"issue form: '{needed}' alanı eksik")
    dropdowns = {b.get("id"): b for b in data.get("body", [])
                 if isinstance(b, dict) and b.get("type") == "dropdown"}
    if "gorev-sinifi" in dropdowns:
        opts = set(dropdowns["gorev-sinifi"]["attributes"]["options"])
        check(opts == {"code-change", "research", "incident"},
              f"issue form: görev sınıfı seçenekleri profillere uymuyor: {opts}")
    required_flags = [b.get("validations", {}).get("required")
                      for b in data.get("body", []) if isinstance(b, dict)]
    check(all(required_flags), "issue form: tüm alanlar zorunlu olmalı")


def test_workflow():
    path = os.path.join(ROOT, ".github", "workflows", "evidence.yml")
    check(os.path.isfile(path), "evidence.yml workflow yok")
    if not os.path.isfile(path):
        return
    data = yaml.safe_load(open(path, encoding="utf-8"))
    check("pull_request" in data.get(True, data.get("on", {})),
          "workflow: pull_request tetikleyicisi yok")
    text = open(path, encoding="utf-8").read()
    check("validate.py" in text, "workflow: kernel doğrulaması koşmuyor")
    check("make_evidence.py" in text, "workflow: evidence üretimi yok")
    check("upload-artifact" in text, "workflow: evidence artifact yüklenmiyor")


def test_evidence_roundtrip():
    schema = json.load(open(os.path.join(ROOT, "schemas",
                                         "evidence.schema.json"),
                            encoding="utf-8"))
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "evidence.json")
        digest_src = os.path.join(td, "report.txt")
        open(digest_src, "w").write("ornek rapor")
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "bin", "make_evidence.py"),
             "--out", out, "--contract", "#0", "--task-class", "code-change",
             "--skill", "implement-change",
             "--check", "tests=passed", "--check", "lint=passed",
             "--digest", f"report={digest_src}",
             "--risk-provisional", "auto", "--risk-final", "auto"],
            capture_output=True, text=True, cwd=ROOT)
        check(proc.returncode == 0,
              f"make_evidence başarısız: {proc.stderr or proc.stdout}")
        if proc.returncode != 0:
            return
        ev = json.load(open(out, encoding="utf-8"))
        for key in schema["required"]:
            check(key in ev, f"evidence: zorunlu alan eksik '{key}'")
        check(re.match(r"^[0-9a-f]{7,40}$", ev["commit_sha"]),
              "evidence: commit_sha biçimi geçersiz")
        for name, dig in ev.get("digests", {}).items():
            check(re.match(r"^sha256:[0-9a-f]{64}$", dig),
                  f"evidence: digest biçimi geçersiz ({name})")
        for c in ev["checks"]:
            check(c["status"] in ("passed", "failed", "skipped"),
                  f"evidence: geçersiz check durumu {c}")
        proc2 = subprocess.run(
            [sys.executable, os.path.join(ROOT, "bin", "make_evidence.py"),
             "--out", out, "--check", "tests=failed"],
            capture_output=True, text=True, cwd=ROOT)
        check(proc2.returncode == 1,
              "make_evidence: failed check'te non-zero dönmeli")


def test_agents_md():
    path = os.path.join(ROOT, "AGENTS.md")
    check(os.path.isfile(path), "AGENTS.md yok")
    if not os.path.isfile(path):
        return
    lines = open(path, encoding="utf-8").read().splitlines()
    check(len(lines) <= 200, f"AGENTS.md {len(lines)} satır (>200 — kısalt)")
    claude = os.path.join(ROOT, "CLAUDE.md")
    check(os.path.isfile(claude), "CLAUDE.md adapter yok")
    if os.path.isfile(claude):
        check("@AGENTS.md" in open(claude, encoding="utf-8").read(),
              "CLAUDE.md: @AGENTS.md importu yok")
    link = os.path.join(ROOT, ".claude", "skills")
    check(os.path.islink(link) and
          os.path.realpath(link) == os.path.realpath(
              os.path.join(ROOT, ".agents", "skills")),
          ".claude/skills → .agents/skills symlink'i yok/yanlış")


def test_mechanisms():
    """Deterministik kapılar ve risk sinyali araçları yerinde mi."""
    for rel in ("bin/hooks/pre-push", "bin/install-hooks.sh",
                "bin/codex-review.sh"):
        path = os.path.join(ROOT, rel)
        check(os.path.isfile(path), f"mekanizma eksik: {rel}")
        if os.path.isfile(path):
            check(os.access(path, os.X_OK), f"{rel}: çalıştırma izni yok")
    hook = os.path.join(ROOT, "bin", "hooks", "pre-push")
    if os.path.isfile(hook):
        check("validate.py" in open(hook, encoding="utf-8").read(),
              "pre-push kancası kernel doğrulamasını koşmuyor")
    # Kurulu kanca makineye özel durumdur; CI'da .git/hooks yoktur ve CI
    # zaten aynı doğrulamayı doğrudan koşar.
    installed = os.path.join(ROOT, ".git", "hooks", "pre-push")
    if os.path.isdir(os.path.join(ROOT, ".git")) and not os.environ.get("CI"):
        check(os.path.isfile(installed) and os.access(installed, os.X_OK),
              "pre-push kancası kurulu değil (bash bin/install-hooks.sh)")


def main():
    skill_names = test_skills()
    test_profiles(skill_names)
    test_issue_form()
    test_workflow()
    test_evidence_roundtrip()
    test_agents_md()
    test_mechanisms()
    if ERRORS:
        print(f"KERNEL DOĞRULAMA: {len(ERRORS)} hata")
        for e in ERRORS:
            print(f"  ✗ {e}")
        return 1
    print("KERNEL DOĞRULAMA: tüm kontroller geçti ✓")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
