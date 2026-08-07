#!/usr/bin/env python3
"""Eksik ortam TEK yüksek sesli hataya dönüşür — sessiz kapsam kaybı yok.

Bu dosya süitin kendi dürüstlük kapısıdır. `ortam.pyyaml_gerekir` eksik
bağımlılıkta testleri atlar (sayı korunur, gerekçe görünür); buradaki tek
test o atlamanın exit 0 ile "geçti" diye okunmasını engeller.

Neden ayrı bir hata: bir kapının YOKLUĞU asla "geçti" diye okunamaz. Eksik
süit yeşil dönerse CI kanıtı yalan söyler — kapsam daraldığı hâlde
`tests=passed` yazılır.
"""
import unittest

from ortam import PYYAML_EKSIK, yaml


class OrtamTest(unittest.TestCase):
    def test_pyyaml_kurulu_degilse_suit_yesil_donmez(self):
        self.assertIsNotNone(yaml, PYYAML_EKSIK)


if __name__ == "__main__":
    unittest.main()
