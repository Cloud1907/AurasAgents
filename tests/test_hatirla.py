#!/usr/bin/env python3
"""bin/hatirla.py — hafıza çağrısı aracının testleri."""
import importlib.util
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_spec = importlib.util.spec_from_file_location(
    "hatirla", os.path.join(ROOT, "bin", "hatirla.py"))
hatirla = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hatirla)


class EslesmeTest(unittest.TestCase):
    def test_turkce_kucuk_harf_ve_kelime_basi(self):
        self.assertTrue(hatirla.eslesiyor(["ratchet"], "Kalite RATCHET'i eklendi"))
        self.assertTrue(hatirla.eslesiyor(["kalite"], "kaliteyi ölçen kapı"))
        self.assertFalse(hatirla.eslesiyor(["ratchet"], "kalite kapısı"))

    def test_tum_kelimeler_gerekli(self):
        self.assertTrue(hatirla.eslesiyor(["kalite", "kapı"], "kalite kapısı"))
        self.assertFalse(hatirla.eslesiyor(["kalite", "ratchet"], "kalite kapısı"))


class KaynakTest(unittest.TestCase):
    def test_adr_kayitlari_tarihli_gelir(self):
        # ADR-0004 kod kalitesi ratchet'i — repoda gerçek kayıt
        hits = hatirla.hatirla("ratchet")
        self.assertTrue(hits, "ratchet için hiçbir kayıt bulunamadı")
        self.assertTrue(any("ADR" in satir for _t, satir in hits))

    def test_git_kayitlari_tarihli_gelir(self):
        hits = hatirla.hatirla("grilling")
        self.assertTrue(any(satir.startswith("commit") for _t, satir in hits),
                        f"grilling için commit kaydı yok: {hits}")
        # her kayıt tarihli — 'tarihiyle hatırlat' sözleşmesi
        for tarih, _s in hits:
            self.assertRegex(tarih, r"^(\d{4}-\d{2}-\d{2}|\?{4}-\?{2}-\?{2})$")

    def test_bos_sonuc_yokluk_kaniti_degildir(self):
        hits = hatirla.hatirla("boyle-bir-konu-hic-olmadi-xyzq")
        self.assertEqual(hits, [])
