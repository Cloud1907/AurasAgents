#!/usr/bin/env python3
"""bin/niyet.py niyet kapısı regresyonları — okuma/mutasyon ayrımı.

Ölçülen yanlış yönlendirmeler (bağımsız inceleme 2026-08-12) ve incele.py
P1 turlarının (PR #43) kalıcı vakaları. tests/test_route.py dosya-boyutu
eşiğine dayandığı için ayrıldı; tablo/komut testleri orada yaşar.
"""
import importlib.util
import os
import sys
import unittest

# Keşif `tests/`i sys.path'e koyar, `python3 -m unittest tests.test_x` koymaz.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ortam import pyyaml_gerekir  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_spec = importlib.util.spec_from_file_location(
    "route", os.path.join(ROOT, "bin", "route.py"))
route = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(route)


@pyyaml_gerekir
class NiyetKapisiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = route.load_rules()

    def pick(self, prompt):
        task_class, primary, extras, _hits, explicit = route.route(
            prompt, self.cfg)
        return task_class, (primary or {}).get("skill"), extras, explicit

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

    # --- incele.py P1 bulguları, 2. tur (PR #43) — ek beyaz-listesi ---

    def test_isim_govdesi_yazma_emri_sanilmaz(self):
        # P1: startswith morfem sınırı aramıyordu — "yapısını" içindeki
        # "yap" kökü mutasyon sayılıp kernel-work'ü zorunlu kılıyordu.
        tc, skill, extras, _x = self.pick("router yapısını eleştirel incele")
        self.assertEqual(tc, "research")
        self.assertEqual(skill, "research-with-evidence")
        self.assertIn("kernel-work", extras)

    def test_edilgen_n_biçimi_yazma_isareti_sayilmaz(self):
        # P1: edilgen listesi -ıl/-il ile sınırlıydı; ünlüyle biten kökün
        # -n edilgeni ("eklenmesi") mutasyon sayılıyordu.
        tc, skill, _e, _x = self.pick(
            "eklenmesi gereken kontrolleri raporla")
        self.assertNotEqual(skill, "implement-change")
        self.assertEqual(tc, "research")

    def test_yukumluluk_fiil_ismi_mutasyondur(self):
        # P1: her -ma/-me devamı olumsuz sayılıyordu — "düzeltmemiz
        # gerekiyor" açık iş talebi salt-okunur profile düşüyordu. Okuma
        # emri varsa okuma yine kazanır (ölçülen vaka 2 çiti). Skill
        # seçimi golden özgüllük kuralına kalır: auth işi security-review.
        tc, skill, extras, _x = self.pick(
            "auth kontrolünü düzeltmemiz gerekiyor")
        self.assertEqual(tc, "code-change")
        self.assertEqual(skill, "security-review")
        self.assertIn("implement-change", extras)

    def test_es_anlamli_yazma_fiilleri_sozlukte(self):
        # P1: fiil listesi eksikti — "iyileştir" açık değişiklik emriydi.
        _tc, skill, _e, _x = self.pick("dashboard ekranını iyileştir")
        self.assertEqual(skill, "designing-interfaces")

    # --- incele.py P1 bulguları, 3. tur (PR #43) ---

    def test_gecmis_zaman_ve_sifat_fiil_emir_sayilmaz(self):
        # P1: -DI / -DIğ biçimleri emir sayılıyordu — "eklediğimiz"
        # tamamlanmış işi anlatır, yeni mutasyon talebi değildir.
        tc, skill, _e, _x = self.pick(
            "eklediğimiz auth kodunu güvenlik açısından incele")
        self.assertEqual(tc, "research")
        self.assertEqual(skill, "security-review")

    def test_belirsiz_niyette_tablo_otoritesi_korunur(self):
        # P1: tanınmayan fiil ("devreye al") varsayılan okumaya düşüp
        # zorunlu skill'i yutuyordu. Kapı yalnız POZİTİF okuma niyetinde
        # devreye girer; niyet belirsizse tetik tablosu karar verir.
        tc, skill, _e, _x = self.pick("login endpointini devreye al")
        self.assertEqual(tc, "code-change")
        self.assertEqual(skill, "implement-change")


if __name__ == "__main__":
    unittest.main()
