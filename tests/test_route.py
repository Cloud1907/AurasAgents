#!/usr/bin/env python3
"""bin/route.py yönlendirme testleri — istek → beklenen skill eşlemesi."""
import importlib.util
import os
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_spec = importlib.util.spec_from_file_location(
    "route", os.path.join(ROOT, "bin", "route.py"))
route = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(route)


class RouteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = route.load_rules()

    def pick(self, prompt):
        task_class, primary, extras, _hits, explicit = route.route(
            prompt, self.cfg)
        return task_class, (primary or {}).get("skill"), extras, explicit

    def test_kod_istegi_implement_change(self):
        for prompt in ("kullanıcı listesi endpoint'i ekle",
                       "şu bug'ı düzelt",
                       "bu servisi refactor edelim"):
            with self.subTest(prompt=prompt):
                tc, skill, _e, _x = self.pick(prompt)
                self.assertEqual(tc, "code-change")
                self.assertEqual(skill, "implement-change")

    def test_arastirma_istegi_research(self):
        for prompt in ("bu metrik nerede hesaplanıyor",
                       "iki yaklaşımı karşılaştır",
                       "cache stratejilerini araştır"):
            with self.subTest(prompt=prompt):
                tc, skill, _e, _x = self.pick(prompt)
                self.assertEqual(tc, "research")
                self.assertEqual(skill, "research-with-evidence")

    def test_guvenlik_ozgul_kural_geneli_yener(self):
        # "incele" research tetiği, "güvenlik/auth" security tetiği: özgül kazanır
        _tc, skill, _e, _x = self.pick("login akışını güvenlik açısından incele")
        self.assertEqual(skill, "security-review")

    def test_risk_yuzeyi_ek_skill_ekler(self):
        _tc, skill, extras, _x = self.pick(
            "ödeme servisine yeni alan ekle ve migration yaz")
        self.assertEqual(skill, "implement-change")
        self.assertIn("security-review", extras)

    def test_kernel_isi_kernel_work(self):
        _tc, skill, _e, _x = self.pick("validate.py'ye yeni bekçi testi ekle")
        self.assertEqual(skill, "kernel-work")

    def test_tasarim_istegi(self):
        _tc, skill, _e, _x = self.pick("dashboard ekranını premium tasarla")
        self.assertEqual(skill, "designing-interfaces")

    def test_acik_slash_komut_her_seyi_yener(self):
        tc, skill, _e, explicit = self.pick("/auras bu projeyi bağla")
        self.assertEqual(explicit, "auras")
        self.assertEqual(skill, "auras")
        self.assertEqual(tc, "code-change")

    def test_eslesmezse_fallback_ve_primary_yok(self):
        tc, skill, _e, _x = self.pick("merhaba")
        self.assertIsNone(skill)
        self.assertEqual(tc, "research")

    def test_turkce_ek_ve_buyuk_harf(self):
        _tc, skill, _e, _x = self.pick("BU SERVİSE CACHE EKLEYELİM")
        self.assertEqual(skill, "implement-change")

    def test_hook_ciktisi_gecerli_json_sozlesmesi(self):
        context, summary = route.render("cache ekle", self.cfg)
        self.assertIn("implement-change", context)
        self.assertIn("router", summary)

    def test_proje_tablosu_kanonigi_yener(self):
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, ".agents"))
            local = os.path.join(td, ".agents", "routing.yml")
            open(local, "w").close()
            path, is_local = route.routing_path(td)
            self.assertEqual(path, local)
            self.assertTrue(is_local)

    def test_tablosuz_projede_kanonige_duser(self):
        with tempfile.TemporaryDirectory() as td:
            path, is_local = route.routing_path(td)
            self.assertEqual(path, route.CANONICAL)
            self.assertFalse(is_local)

    def test_global_yedek_proje_hooku_varsa_cekilir(self):
        # AurasAgents'ın kendisi router hook'unu kaydeder → global yedek susar
        os.environ["CLAUDE_PROJECT_DIR"] = ROOT
        try:
            self.assertTrue(route.project_registers_router(ROOT))
            self.assertEqual(route.main(["--global-fallback"]), 0)
        finally:
            os.environ.pop("CLAUDE_PROJECT_DIR", None)

    def test_kurulu_olmayan_skill_uyarisi(self):
        with tempfile.TemporaryDirectory() as td:
            context, _s = route.render("cache ekle", self.cfg, pdir=td,
                                       table_is_local=False)
            self.assertIn("kurulu değil", context)
            self.assertIn("kanonik", context)

    def test_kurulu_skill_uyari_uretmez(self):
        context, _s = route.render("cache ekle", self.cfg, pdir=ROOT)
        self.assertNotIn("kurulu değil", context)

    def test_gorunurluk_basligi_dayatilir(self):
        # Kullanıcı yazışmada ne olduğunu görmeli — bu bir temenni değil,
        # her turda enjekte edilen zorunlu biçim.
        context, _s = route.render("cache ekle", self.cfg, pdir=ROOT)
        self.assertIn("🧭", context)
        self.assertIn("🔧", context)
        self.assertIn("Cevabına", context)

    def test_baslik_sohbet_turunda_da_istenir(self):
        context, _s = route.render("merhaba nasılsın", self.cfg, pdir=ROOT)
        self.assertIn("🧭", context)

    def test_bos_istek_ciktisiz(self):
        # main() stdin okur; boş istek yönlendirme üretmemeli
        self.assertEqual(route.route("", self.cfg)[1], None)


if __name__ == "__main__":
    unittest.main()
