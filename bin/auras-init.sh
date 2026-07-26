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

echo "Cekirdek dosyalar:"
copy_new "AGENTS.md" "AGENTS.md"
copy_new "CLAUDE.md" "CLAUDE.md"
copy_new ".agents/skills" ".agents/skills"
copy_new ".agents/capability-profiles" ".agents/capability-profiles"
copy_new ".agents/routing.yml" ".agents/routing.yml"
copy_new ".claude/rules" ".claude/rules"
copy_new ".github/ISSUE_TEMPLATE/work-contract.yml" ".github/ISSUE_TEMPLATE/work-contract.yml"
copy_new ".github/workflows/evidence.yml" ".github/workflows/evidence.yml"
copy_new "schemas/evidence.schema.json" "schemas/evidence.schema.json"
copy_new "bin/validate.py" "bin/validate.py"
copy_new "bin/make_evidence.py" "bin/make_evidence.py"
copy_new "bin/route.py" "bin/route.py"
copy_new "bin/memory_hygiene.py" "bin/memory_hygiene.py"
copy_new "tests" "tests"
copy_new "bin/codex-review.sh" "bin/codex-review.sh"
copy_new "bin/install-hooks.sh" "bin/install-hooks.sh"
copy_new "bin/hooks" "bin/hooks"

chmod +x "$TARGET"/bin/*.sh "$TARGET"/bin/hooks/* 2>/dev/null || true

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
echo "Skill router hook'u (.claude/settings.json):"
python3 - "$TARGET" <<'PY'
import json
import os
import sys

target = sys.argv[1]
path = os.path.join(target, ".claude", "settings.json")
data = {}
if os.path.exists(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except ValueError:
        print("  UYARI: settings.json bozuk JSON — router hook'u elle eklenmeli")
        sys.exit(0)

entries = data.setdefault("hooks", {}).setdefault("UserPromptSubmit", [])
if any("route.py" in h.get("command", "")
       for e in entries for h in e.get("hooks", [])):
    print("  atlandi (zaten var): UserPromptSubmit router hook")
else:
    entries.append({"hooks": [{
        "type": "command",
        "command": 'python3 "${CLAUDE_PROJECT_DIR:-.}/bin/route.py"',
        "timeout": 10,
        "statusMessage": "Skill yonlendirmesi",
    }]})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("  eklendi: UserPromptSubmit router hook")
PY

echo ""
echo "Dogrulama:"
python3 bin/validate.py
