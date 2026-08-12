#!/usr/bin/env python3
"""bin/route.py yönlendirme testleri — istek → beklenen skill eşlemesi."""
import importlib.util
import os
import sys
import tempfile
import unittest

# Keşif `tests/`i sys.path'e koyar, `python3 -m unittest tests.test_x` koymaz.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortam import pyyaml_gerekir  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_spec = importlib.util.spec_from_file_location(
    "route", os.path.join(ROOT, "bin", "route.py"))
route = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(route)


# Sınıfın TAMAMI yönlendirme tablosunu okur; tablo yaml'dır. PyYAML yoksa
# setUpClass çökerdi ve sınıfın tüm testleri süitten YOK OLURDU (tek hata
# satırı, sayıda 26 test eksik). Atlama sayıyı korur, gerekçeyi gösterir.
@pyyaml_gerekir
class RouteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = route.load_rules()

    def pick(self, prompt):
        task_class, primary, extras, _hits, explicit = route.route(
            prompt, self.cfg)
        return task_class, (primary or {}).get("skill"), extras, explicit

    # --- soru turu vs iş emri (2026-08-07 bulgusu) ---
    # Bir oturumda 12+ tur yanlış sınıflandı: soru sorulduğunda router
    # `code-change` + `approval` ilan edip zorunlu skill dayattı. Türkçe
    # önek eşleşmesi DOĞRU çalışıyordu ("yapmalıyız" → "yap" aynı fiil);
    # kusur tur TİPİNİN okunmamasıydı. Soru ≠ iş emri.

    def test_soru_turu_zorunlu_skill_dayatmaz(self):
        for prompt in ("bizim hafıza tarafı başarılı mı?",
                       "sonuç anlayacağım dilde ne yapmalıyız?",
                       "gerçekten dürüst önerin var mı?",
                       "kodlamada nasıl bir standartta teslim ediyorsun?",
                       "sence bu sistem iyi mi"):
            with self.subTest(prompt=prompt):
                tc, skill, _e, _x = self.pick(prompt)
                self.assertIsNone(
                    skill, f"soru turuna zorunlu skill dayatıldı: {skill}")
                self.assertEqual(tc, "research", "soru turu salt-okunur profil almalı")

    def test_is_emri_soru_kelimesi_tasisa_bile_yonlendirilir(self):
        # "neden"/"nasıl" geçen ama EMİR olan turlar iş olarak kalmalı.
        for prompt in ("actions'a bak neden koşmadı",
                       "bu bug neden oluyor bul ve düzelt"):
            with self.subTest(prompt=prompt):
                _tc, skill, _e, _x = self.pick(prompt)
                self.assertIsNotNone(skill, "emir turu skill'siz kaldı")

    def test_acik_slash_komut_soruda_bile_kazanir(self):
        # Kullanıcı açıkça /auras dediyse soru biçimi bunu ezmemeli.
        _tc, skill, _e, explicit = self.pick("/auras bunu bağlar mısın?")
        self.assertEqual(explicit, "auras")
        self.assertEqual(skill, "auras")

    # --- niyet ayrımı: salt-okunur inceleme vs mutasyon (2026-08-12) ---
    # Bağımsız inceleme (Codex) iki turda da doğruladı: tek aşamalı kelime
    # puanlaması salt-okunur inceleme isteğini ALAN ADLARI yüzünden yazma
    # yetkili işe çeviriyordu. İki ölçülen vaka kalıcı regresyon:

    def test_salt_okunur_inceleme_alan_adlariyla_yazma_isine_donmez(self):
        # Ölçülen vaka 1: kernel-work tetikleri (router, kanıt, hafıza)
        # 3 puanla "incele"yi (1 puan) ezip code-change/approval üretiyordu.
        tc, skill, extras, _x = self.pick(
            "AurasAgents router, AurasPrime, kanıt kapıları ve hafıza "
            "sistemini eleştirel incele")
        self.assertEqual(tc, "research")
        self.assertEqual(skill, "research-with-evidence")
        # Yazma kuralı kaybolmaz, öneriye düşer: iş gerçekten mutasyona
        # dönerse ajan kernel-work'ü oradan yükler.
        self.assertIn("kernel-work", extras)

    def test_inceleme_istemi_duzelt_kelimesiyle_mutasyona_donmez(self):
        # Ölçülen vaka 2: Codex'in kendi inceleme istemi içindeki "düzelt"
        # implement-change'i zorunlu kılıyordu. Türkçe emir cümle SONUNDADIR:
        # son niyet işareti okuma ise istek okumadır; "kod yazma" olumsuz
        # emirdir, yazma işareti sayılmaz.
        tc, skill, _e, _x = self.pick(
            "route.py yönlendirmesini eleştirel incele; neyi düzeltmemiz "
            "gerektiğini bulgu olarak raporla, kod yazma")
        self.assertEqual(tc, "research")
        self.assertNotEqual(skill, "implement-change")

    def test_mutasyon_dogrulaninca_yazma_kurali_kalir(self):
        # Niyet çiti iş emrini yutmamalı: son işaret yazma ise mutasyondur.
        _tc, skill, _e, _x = self.pick(
            "raporda bulduğun bug'ı incele ve düzelt")
        self.assertEqual(skill, "implement-change")

    def test_okunur_niyette_okunur_kural_yoksa_zorunlu_skill_yok(self):
        # Düşük güven: niyet okuma ama hiçbir okuma kuralı eşleşmedi —
        # zorunlu skill üretilmez, eşleşen yazma kuralları öneri kalır.
        tc, skill, extras, _x = self.pick(
            "çekirdek profillerini gözden geçir")
        self.assertIsNone(skill)
        self.assertEqual(tc, "research")
        self.assertIn("kernel-work", extras)

    # --- incele.py P1 bulguları (PR #43, 2026-08-12) — kalıcı regresyon ---

    def test_yazma_emri_sonda_raporla_olsa_da_mutasyondur(self):
        # P1: "son işaret kazanır" çok-eylemli gerçek mutasyonu okumaya
        # çeviriyordu. Yalın yazma emri ("ekle") varsa tur mutasyondur.
        _tc, skill, _e, _x = self.pick(
            "kullanıcı endpoint'ini ekle ve yaptığını raporla")
        self.assertEqual(skill, "implement-change")

    def test_routing_yazma_fiili_niyet_sozlugunde(self):
        # P1: "güzelleştir" routing tetiğiydi ama niyet sözlüğünde yoktu —
        # açık değişiklik emri zorunlu skill'siz kalıyordu.
        _tc, skill, _e, _x = self.pick("dashboard ekranını güzelleştir")
        self.assertEqual(skill, "designing-interfaces")

    def test_cekimli_olumsuz_ve_edilgen_yazma_isareti_sayilmaz(self):
        # P1: yalnız tam -ma/-me eki olumsuz sayılıyordu; "düzeltmeden"
        # gibi çekimli olumsuz ve "düzeltilmesi" gibi edilgen biçimler
        # yazma işareti sayılıp turu mutasyona çeviriyordu.
        for prompt in ("önce bulgularını raporla, kodu kesinlikle "
                       "düzeltmeden bırak",
                       "düzeltilmesi gerekenleri listele"):
            with self.subTest(prompt=prompt):
                tc, skill, _e, _x = self.pick(prompt)
                self.assertNotEqual(skill, "implement-change")
                self.assertEqual(tc, "research")

    def test_okuma_niyetinde_denetim_salt_okunur_profil_alir(self):
        # P1: intent:read kuralı code-change sınıfını koruyunca salt-okunur
        # denetim yazma profili açıyordu. Skill zorunlu kalır (golden),
        # sınıf okuma profiline iner; risk etiketi kuraldan gelir.
        tc, skill, _e, _x = self.pick(
            "login akışını güvenlik açısından incele")
        self.assertEqual(skill, "security-review")
        self.assertEqual(tc, "research")

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

    def test_grilling_dogal_dille_yonlendirilmez(self):
        """grilling YALNIZ /grilling ile çağrılır — doğal dil tetiği yok.

        Denendi ve kaldırıldı (PR #39): anahtar kelime katmanı cümleyi
        anlamadığı için ret ("sorguya çekme"), alıntı, yük testi ve yemek
        anlamları yanlış-pozitif üretti. Yanlış açılan sorgu oturumunun
        bedeli, kaçırmanın bedelinden yüksek.
        """
        for istem in ("beni sorguya çek", "planımı stres testine sok",
                      "beni grill'le", "beni sorguya çeker misin?"):
            _tc, skill, extras, _x = self.pick(istem)
            self.assertNotEqual(skill, "grilling", istem)
            self.assertNotIn("grilling", extras, istem)

    def test_grilling_acik_komutla_cagrilir(self):
        _tc, _skill, _e, explicit = self.pick("/grilling planı netleştirelim")
        self.assertEqual(explicit, "grilling")

    def test_profil_sinifi_okunabiliyor(self):
        """skill_task_class GERÇEKTEN çalışıyor mu (yalnız None dönmüyor mu).

        Yönlendirme testi bunu kanıtlamaz: tetik eşleşmesi aynı sınıfı
        tesadüfen üretebilir ve bozuk profil okuması fark edilmez.
        """
        self.assertEqual(route.skill_task_class("grilling", ROOT), "research")
        self.assertEqual(route.skill_task_class("implement-change", ROOT),
                         "code-change")
        self.assertIsNone(route.skill_task_class("boyle-bir-skill-yok", ROOT))

    def test_profil_sinifi_kelime_puanlamasini_yener(self):
        """Otorite profildir: kelimeler başka sınıf söylese bile.

        "/grilling kodu düzelt ve uygula" isteminde tetikler code-change
        diyor; profil research diyor. Komutun sınıfı izin sınırından gelir,
        yoksa kullanıcı /komutla yazma yetkisi açabilirdi.
        """
        tc, _s, _e, explicit = self.pick("/grilling kodu düzelt ve uygula")
        self.assertEqual((tc, explicit), ("research", "grilling"))

    def test_kuralsiz_komut_risk_metadatasini_kaybetmez(self):
        """Yazma sınıfındaki /komut, risk sınıfını da taşımalı.

        /project-onboarding ile /auras aynı işi yapar; birinin approval
        diğerinin sessizce 'auto' sayılması, risk politikasını komut
        seçimine bağlı hale getirirdi.
        """
        tc, skill, _e, _x = self.pick("/project-onboarding")
        self.assertEqual(tc, "code-change")
        self.assertEqual(skill, "project-onboarding")

    def test_acik_komut_tetik_tasiyan_metinde_de_kazanir(self):
        """Kurallı olmayan skill'in /komutu, anahtar kelimeye yenilmez.

        "/grilling ... nasıl kurgulayacağımı bilmiyorum" isteminde "nasıl"
        research tetiğidir. Kullanıcı komutla seçimini yapmışken başka bir
        skill'i ZORUNLU kılmak, açık iradeyi anahtar kelimeyle ezmektir.
        """
        _tc, skill, _e, explicit = self.pick(
            "/grilling yeni bildirim sistemini nasıl kurgulayacağımı bilmiyorum")
        self.assertEqual(explicit, "grilling")
        # Zorunlu kılınan skill, kullanıcının istediği skill olmalı
        self.assertEqual(skill, "grilling")

    def test_yuk_testi_kod_isidir(self):
        _tc, skill, _e, _x = self.pick("API endpointine stres testi yap")
        self.assertEqual(skill, "implement-change")

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

    def test_disiplin_sahibi_secilir(self):
        """Analiz 'bu iş kimin işi' sorusunu cevaplamalı — tek sahip."""
        vakalar = (
            ("login ekranının butonları bozuk görünüyor", "frontend-engineer"),
            ("kullanıcı endpoint'ine yetki kontrolü ekle", "backend-engineer"),
            ("bu sorgu çok yavaş, index önerisi lazım", "database-engineer"),
            ("monolit mi mikroservis mi olmalı", "software-architect"),
            ("kullanıcı bu akışta hedefe varamıyor", "ux-designer"),
            ("docker compose deploy pipeline'ı kur", "devops-engineer"),
            ("model drift'i nasıl izleyelim", "ml-ai-engineer"),
        )
        for prompt, beklenen in vakalar:
            with self.subTest(prompt=prompt):
                self.assertEqual(route.sahip(prompt, self.cfg), beklenen)

    def test_tek_sahip_dondurur_zincir_degil(self):
        # Rol tiyatrosu yasağı: birden çok disiplin eşleşse de TEK sahip döner
        sahip = route.sahip("frontend butonu backend endpoint'i sorgu index",
                            self.cfg)
        self.assertIsInstance(sahip, str)

    def test_sahip_baglama_enjekte_edilir(self):
        context, _s = route.render("bu sorguyu hızlandır", self.cfg, pdir=ROOT)
        self.assertIn("👤", context)
        self.assertIn("database-engineer", context)

    def test_baslikta_sahip_satiri_var(self):
        context, _s = route.render("bu sorguyu hızlandır", self.cfg, pdir=ROOT)
        self.assertIn("👤 Sahip: database-engineer", context)

    def test_itiraz_yukumlulugu_enjekte_edilir(self):
        context, _s = route.render("cache ekle", self.cfg, pdir=ROOT)
        self.assertIn("İTİRAZ", context.upper())

    def test_bos_istek_ciktisiz(self):
        # main() stdin okur; boş istek yönlendirme üretmemeli
        self.assertEqual(route.route("", self.cfg)[1], None)


# Kuralsız /komut testleri tests/test_route_komut.py'de (dosya-boyutu
# eşiği, 2026-08-12) — burada yalnız yönlendirme tablosu vakaları yaşar.

if __name__ == "__main__":
    unittest.main()
