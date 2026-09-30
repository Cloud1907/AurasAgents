#!/usr/bin/env python3
# kanonik-özel: bin/makine.py sets up a machine from the canonical clone;
# connected projects do not carry it and skip these tests.
"""New-machine setup — the system must work the same after a fresh clone.

Measured 2026-09-30: the global `/auras` skill in ~/.claude/skills was a
stale July copy (missing `references/`), and the global router fallback was
hard-wired to one clone path. On a second machine both fail silently: the
old skill installs an old kernel, the missing path makes every prompt's
hook error out. `bin/makine.py` syncs both from the clone it runs in.

Canonical-only tool: connected projects do not carry it (see auras-init).
"""
import importlib.util
import json
import os
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "bin", "makine.py")


def _load():
    spec = importlib.util.spec_from_file_location("_makine", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(os.path.isfile(os.path.join(ROOT, "bin", "auras-init.sh")),
                     "auras-init.sh yok — bağlı proje, denetlenecek şey yok")
class YeniMakine(unittest.TestCase):

    def setUp(self):
        self.m = _load()
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.realpath(self.tmp.name)
        self.settings = os.path.join(self.home, ".claude", "settings.json")

    def tearDown(self):
        self.tmp.cleanup()

    def _write_settings(self, veri):
        os.makedirs(os.path.dirname(self.settings), exist_ok=True)
        with open(self.settings, "w", encoding="utf-8") as fh:
            json.dump(veri, fh)

    def _read_settings(self):
        with open(self.settings, encoding="utf-8") as fh:
            return json.load(fh)

    def _commands(self):
        return [h["command"] for e in self._read_settings()["hooks"]["UserPromptSubmit"]
                for h in e["hooks"]]

    def test_skill_is_synced_from_clone(self):
        self.m.sync_skill(ROOT, self.home)
        hedef = os.path.join(self.home, ".claude", "skills", "auras")
        self.assertTrue(os.path.isfile(os.path.join(hedef, "SKILL.md")))
        self.assertTrue(self.m.skill_current(ROOT, self.home))

    def test_stale_skill_is_detected(self):
        hedef = os.path.join(self.home, ".claude", "skills", "auras")
        os.makedirs(hedef)
        with open(os.path.join(hedef, "SKILL.md"), "w") as fh:
            fh.write("old")
        self.assertFalse(self.m.skill_current(ROOT, self.home))

    def test_hook_points_at_this_clone(self):
        self.m.register_hook(ROOT, self.home)
        komut = self._commands()
        self.assertEqual(len(komut), 1)
        self.assertIn(os.path.join(ROOT, "bin", "route.py"), komut[0])
        self.assertIn("--global-fallback", komut[0])
        self.assertTrue(self.m.hook_current(ROOT, self.home))

    def test_stale_path_is_replaced_not_duplicated(self):
        eski = 'python3 "/nowhere/AurasAgents/bin/route.py" --global-fallback'
        self._write_settings({"hooks": {"UserPromptSubmit": [
            {"hooks": [{"type": "command", "command": eski}]}]}})
        self.assertFalse(self.m.hook_current(ROOT, self.home))
        self.m.register_hook(ROOT, self.home)
        self.m.register_hook(ROOT, self.home)  # idempotent
        komut = self._commands()
        self.assertEqual(len(komut), 1)
        self.assertNotIn("/nowhere", komut[0])

    def test_home_variable_form_counts_as_current(self):
        rel = os.path.relpath(ROOT, self.home)
        self._write_settings({"hooks": {"UserPromptSubmit": [{"hooks": [
            {"type": "command",
             "command": 'python3 "$HOME/%s/bin/route.py" --global-fallback' % rel}]}]}})
        self.assertTrue(self.m.hook_current(ROOT, self.home))

    def test_unrelated_settings_survive(self):
        self._write_settings({"model": "x", "hooks": {"UserPromptSubmit": [
            {"hooks": [{"type": "command", "command": "echo other"}]}],
            "Stop": [{"hooks": [{"type": "command", "command": "echo stop"}]}]}})
        self.m.register_hook(ROOT, self.home)
        veri = self._read_settings()
        self.assertEqual(veri["model"], "x")
        self.assertIn("Stop", veri["hooks"])
        self.assertIn("echo other", self._commands())

    def test_unreadable_settings_are_not_overwritten(self):
        os.makedirs(os.path.dirname(self.settings))
        with open(self.settings, "w") as fh:
            fh.write("{broken")
        self.assertFalse(self.m.register_hook(ROOT, self.home))
        with open(self.settings) as fh:
            self.assertEqual(fh.read(), "{broken")


if __name__ == "__main__":
    unittest.main()
