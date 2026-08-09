#!/usr/bin/env python3
"""Eksik ortam TEK yüksek sesli hataya dönüşür — sessiz kapsam kaybı yok.

Bu dosya süitin kendi dürüstlük kapısıdır. `ortam.pyyaml_gerekir` eksik
bağımlılıkta testleri atlar (sayı korunur, gerekçe görünür); buradaki tek
test o atlamanın exit 0 ile "geçti" diye okunmasını engeller.

Neden ayrı bir hata: bir kapının YOKLUĞU asla "geçti" diye okunamaz. Eksik
süit yeşil dönerse CI kanıtı yalan söyler — kapsam daraldığı hâlde
`tests=passed` yazılır.
"""
import os
import sys
import unittest

# Keşif `tests/`i sys.path'e koyar, `python3 -m unittest tests.test_x` koymaz.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortam import PYYAML_EKSIK, yaml  # noqa: E402


class OrtamTest(unittest.TestCase):
    def test_pyyaml_kurulu_degilse_suit_yesil_donmez(self):
        self.assertIsNotNone(yaml, PYYAML_EKSIK)


if __name__ == "__main__":
    unittest.main()
