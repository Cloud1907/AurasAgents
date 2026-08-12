#!/usr/bin/env python3
"""Keşif bekçisi: GÖRÜNÜR atlama ile ÇÖKME aynı şey değildir.

Ölçüm (Agent Ofis kurulumu, 2026-08-12): pytest'siz yorumlayıcıda
`raise unittest.SkipTest` ile GÖRÜNÜR hâle getirilen modül, bekçide hâlâ
"import'ta çöktü" diye raporlandı. Sistemin kendi önerdiği çare ("ortam
bağımlılığıysa koşullu atlamaya çevir") uygulanınca bile kırmızı kalıyordu
— yani çare çalışmıyordu. unittest ikisini AYRI sınıflarla işaretler:
_FailedTest (çökme) ve ModuleSkipped (görünür atlama).
"""
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class KesifAtlamaTest(unittest.TestCase):
    def kesfet(self, icerik):
        """Geçici tests/ dizininde keşfi koş, (sayim, hatali, atlanan) döndür."""
        import importlib.util
        import json
        spec = importlib.util.spec_from_file_location(
            "validate", os.path.join(ROOT, "bin", "validate.py"))
        val = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(val)
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, "tests"))
            with open(os.path.join(td, "tests", "test_ornek.py"), "w",
                      encoding="utf-8") as fh:
                fh.write(icerik)
            p = subprocess.run([sys.executable, "-c", val._KESIF_KODU],
                               capture_output=True, text=True, cwd=td)
            satir = next(s for s in reversed(p.stdout.splitlines())
                         if s.startswith(val._KESIF_ISARET))
            return json.loads(satir[len(val._KESIF_ISARET):])

    def test_gorunur_atlama_cokme_sayilmaz(self):
        veri = self.kesfet(
            "import unittest\n"
            "raise unittest.SkipTest('ortam yok — görünür atlama')\n")
        self.assertEqual(veri["hatali"], [],
                         "görünür atlama ÇÖKME olarak raporlandı")
        self.assertIn("test_ornek", veri.get("atlanan", []),
                      "atlanan modül kayda geçmedi — sessiz kalmamalı")

    def test_gercek_cokme_hala_yakalanir(self):
        veri = self.kesfet("import boyle_bir_modul_yok\n")
        self.assertIn("test_ornek", veri["hatali"],
                      "gerçek import çökmesi kaçtı")


if __name__ == "__main__":
    unittest.main()
