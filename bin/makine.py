#!/usr/bin/env python3
"""Set up (or check) this machine for AurasAgents from the current clone.

Why: a clone alone is not a working system. Three pieces live OUTSIDE the
repo and do not travel with `git clone`:
  1. the global `/auras` skill      (~/.claude/skills/auras)
  2. the global router fallback     (~/.claude/settings.json UserPromptSubmit)
  3. the git pre-push gate          (.git/hooks — never versioned by git)
Measured 2026-09-30: (1) was a stale July copy, (2) was wired to a single
clone path. Both fail silently on a second machine.

Usage:
  python3 bin/makine.py            # check only, exit 1 if something is missing
  python3 bin/makine.py --install  # sync skill, register hook, install gate

Idempotent. Never overwrites a settings.json it cannot parse.
"""
import filecmp
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALLBACK_FLAG = "--global-fallback"


def _skill_paths(root, home):
    return (os.path.join(root, ".agents", "skills", "auras"),
            os.path.join(home, ".claude", "skills", "auras"))


def skill_current(root, home):
    """True when the global skill tree equals the clone's canonical copy."""
    src, dst = _skill_paths(root, home)
    if not os.path.isdir(dst):
        return False

    def same(cmp):
        if cmp.left_only or cmp.right_only or cmp.funny_files:
            return False
        _, mismatch, errors = filecmp.cmpfiles(
            cmp.left, cmp.right, cmp.common_files, shallow=False)
        if mismatch or errors:
            return False
        return all(same(sub) for sub in cmp.subdirs.values())

    return same(filecmp.dircmp(src, dst, ignore=["__pycache__", ".DS_Store"]))


def sync_skill(root, home):
    src, dst = _skill_paths(root, home)
    if os.path.islink(dst):
        os.unlink(dst)
    elif os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))


def _hook_command(root):
    return 'python3 "%s" %s' % (os.path.join(root, "bin", "route.py"), FALLBACK_FLAG)


def _is_fallback(command):
    return "route.py" in command and FALLBACK_FLAG in command


def _read_settings(path):
    """Parsed settings, {} when absent, None when present but unreadable."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def hook_current(root, home):
    data = _read_settings(os.path.join(home, ".claude", "settings.json"))
    if not data:
        return False
    commands = [h.get("command", "")
                for e in data.get("hooks", {}).get("UserPromptSubmit", [])
                for h in e.get("hooks", [])]
    fallbacks = [c for c in commands if _is_fallback(c)]
    return len(fallbacks) == 1 and _router_path(fallbacks[0], home) == \
        os.path.realpath(os.path.join(root, "bin", "route.py"))


def _router_path(command, home):
    """Resolved route.py path of a hook; "$HOME/..." and absolute are equal."""
    for token in command.replace('"', " ").split():
        if token.endswith("route.py"):
            token = token.replace("${HOME}", home).replace("$HOME", home)
            return os.path.realpath(token)
    return None


def register_hook(root, home):
    """Point the global router fallback at this clone. False if refused."""
    path = os.path.join(home, ".claude", "settings.json")
    data = _read_settings(path)
    if data is None:
        return False
    if hook_current(root, home):
        return True  # leave the user's file byte-for-byte untouched
    entries = data.setdefault("hooks", {}).setdefault("UserPromptSubmit", [])
    kept = []
    for entry in entries:
        hooks = [h for h in entry.get("hooks", [])
                 if not _is_fallback(h.get("command", ""))]
        if hooks:
            kept.append(dict(entry, hooks=hooks))
    kept.append({"hooks": [{"type": "command", "command": _hook_command(root),
                            "timeout": 10,
                            "statusMessage": "AurasAgents skill routing"}]})
    data["hooks"]["UserPromptSubmit"] = kept
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)
    return True


def gate_current(root):
    try:
        hooks = subprocess.run(["git", "rev-parse", "--git-path", "hooks"],
                               cwd=root, capture_output=True, text=True,
                               check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return False
    installed = os.path.join(root, hooks, "pre-push") if not os.path.isabs(hooks) \
        else os.path.join(hooks, "pre-push")
    return os.path.isfile(installed) and filecmp.cmp(
        installed, os.path.join(root, "bin", "hooks", "pre-push"), shallow=False)


def _has_yaml():
    try:
        import yaml  # noqa: F401
        return True
    except ImportError:
        return False


def _tool_ok(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, timeout=20).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def report(root, home):
    """(name, ok, required, hint) rows. Optional rows never fail the check."""
    return [
        ("PyYAML for python3", _has_yaml(), True,
         "python3 -m pip install --user pyyaml"),
        ("global /auras skill matches clone", skill_current(root, home), True,
         "python3 bin/makine.py --install"),
        ("global router fallback -> this clone", hook_current(root, home), True,
         "python3 bin/makine.py --install"),
        ("pre-push gate installed", gate_current(root), True,
         "python3 bin/makine.py --install"),
        ("gh authenticated (PRs, CI evidence)", _tool_ok("gh", "auth", "status"), False,
         "gh auth login"),
        ("codex CLI (independent review, bin/incele.py)",
         _tool_ok("codex", "--version"), False, "install Codex CLI and log in"),
    ]


def main(argv):
    home = os.path.expanduser("~")
    if "--install" in argv:
        sync_skill(ROOT, home)
        if not register_hook(ROOT, home):
            print("~/.claude/settings.json is not valid JSON; fix it and rerun.")
            return 1
        subprocess.run(["bash", os.path.join(ROOT, "bin", "install-hooks.sh")],
                       cwd=ROOT, check=False)
    failed = False
    for name, ok, required, hint in report(ROOT, home):
        mark = "ok  " if ok else ("MISS" if required else "opt ")
        print("  [%s] %s%s" % (mark, name, "" if ok else "  ->  " + hint))
        failed |= required and not ok
    if "--install" in argv:
        print("Restart Claude Code (or open /hooks) so the session sees the hook.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
