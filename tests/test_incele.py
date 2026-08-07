#!/usr/bin/env python3
"""Bağımsız inceleme kapısı — karar mantığı ve fail-closed davranışı.

Bu kapı merge yetkisi taşır; sessizce yanlış karar vermesi en pahalı hatadır.
Saf fonksiyonlar (risk_sinifi / bulgulari_ayikla / karar) dış dünya olmadan
test edilir; Codex çağrısı ve gh komutları testte KOŞMAZ.
"""
import importlib.util
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "incele", os.path.join(ROOT, "bin", "incele.py"))
incele = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(incele)

TEMIZ = {"P0": [], "P1": [], "P2": []}


class RiskSinifiTest(unittest.TestCase):
    def test_yalniz_dokuman_auto(self):
        self.assertEqual(
            incele.risk_sinifi(["docs/a.md", "README.md", "tests/test_x.py"]),
            "auto")

    def test_secret_dosyasi_deny(self):
        for yol in (".env", "apps/.env.production", "secrets/db.txt",
                    "deploy/id_rsa", "certs/server.pem"):
            with self.subTest(yol=yol):
                self.assertEqual(incele.risk_sinifi([yol]), "deny")

    def test_auth_ve_kernel_approval(self):
        for yol in ("src/auth/login.py", "backend/Migrations/001.cs",
                    "bin/route.py", ".github/workflows/deploy.yml",
                    "frontend/package.json"):
            with self.subTest(yol=yol):
                self.assertEqual(incele.risk_sinifi([yol]), "approval")

    def test_bilinmeyen_yol_yukari_eskale(self):
        # Eskalasyon yalnız yukarı: tanımadığımız yol 'auto' sayılmaz
        self.assertEqual(incele.risk_sinifi(["src/rastgele.py"]), "approval")

    def test_bos_liste_temkinli(self):
        self.assertEqual(incele.risk_sinifi([]), "approval")

    def test_tek_riskli_dosya_tumunu_yukseltir(self):
        self.assertEqual(
            incele.risk_sinifi(["docs/a.md", "src/auth/login.py"]), "approval")


class AyiklamaTest(unittest.TestCase):
    def test_bulgular_ve_sonuc_okunur(self):
        metin = ("[P0] api.py:12 — yetki kontrolü yok — başka kullanıcının "
                 "kaydı okunur\n[P2] stil notu\nSONUC: 2 bulgu (en yuksek: P0)")
        b, s, ok = incele.bulgulari_ayikla(metin)
        self.assertTrue(ok)
        self.assertEqual(len(b["P0"]), 1)
        self.assertEqual(len(b["P2"]), 1)
        self.assertIn("2 bulgu", s)

    def test_temiz_cikti(self):
        b, s, ok = incele.bulgulari_ayikla("Inceleme tamam.\nSONUC: TEMIZ")
        self.assertTrue(ok)
        self.assertEqual(b, TEMIZ)
        self.assertEqual(s.upper(), "TEMIZ")

    def test_sonuc_satiri_yoksa_okunamadi(self):
        # En tehlikeli hâl: çıktı bozuk ama "bulgu yok" diye geçmek
        _b, _s, ok = incele.bulgulari_ayikla("codex hata verdi, bağlantı yok")
        self.assertFalse(ok)

    def test_bos_cikti_okunamadi(self):
        self.assertFalse(incele.bulgulari_ayikla("")[2])


class KararTest(unittest.TestCase):
    def test_auto_temiz_yesil_merge(self):
        k, _g = incele.karar("auto", TEMIZ, True, True)
        self.assertEqual(k, "merge")

    def test_approval_temiz_olsa_bile_insana_gider(self):
        k, _g = incele.karar("approval", TEMIZ, True, True)
        self.assertEqual(k, "insan")

    def test_deny_her_zaman_engel(self):
        k, _g = incele.karar("deny", TEMIZ, True, True)
        self.assertEqual(k, "engel")

    def test_p0_auto_riskte_bile_engel(self):
        b = {"P0": ["yetki yok"], "P1": [], "P2": []}
        self.assertEqual(incele.karar("auto", b, True, True)[0], "engel")

    def test_p1_engel(self):
        b = {"P0": [], "P1": ["kaynak sızıntısı"], "P2": []}
        self.assertEqual(incele.karar("auto", b, True, True)[0], "engel")

    def test_p2_merge_engellemez(self):
        b = {"P0": [], "P1": [], "P2": ["bilgi notu"]}
        self.assertEqual(incele.karar("auto", b, True, True)[0], "merge")

    def test_ci_kirmizi_engel(self):
        self.assertEqual(incele.karar("auto", TEMIZ, False, True)[0], "engel")

    def test_okunamayan_inceleme_fail_closed(self):
        # 'Ayrıştıramadım' ASLA 'temiz' sayılmaz
        k, g = incele.karar("auto", TEMIZ, True, False)
        self.assertEqual(k, "engel")
        self.assertIn("ayrıştırılamadı", g)


class OzetTest(unittest.TestCase):
    def test_govde_karari_bastan_soyler(self):
        # Okunmayan yorum yoktur: karar ilk satırda olmalı
        g = incele.ozet_govde("auto", TEMIZ, "TEMIZ", "merge", "gerekçe", "3/3")
        self.assertIn("MERGE", g.splitlines()[0])
        self.assertIn("risk sinyali", g)

    def test_bulgular_govdede_gorunur(self):
        b = {"P0": ["api.py:12 yetki yok"], "P1": [], "P2": []}
        g = incele.ozet_govde("approval", b, "1 bulgu", "engel", "P0 var", "3/3")
        self.assertIn("api.py:12", g)
        self.assertIn("⛔", g)


if __name__ == "__main__":
    unittest.main()
