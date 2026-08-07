#!/usr/bin/env python3
"""Motor listesi + kanonik↔proje sınıflandırması — geri taşımanın bekçisi.

Kritik iddia: "ezilecek mi" kararı manifest'e değil kanonik git geçmişine
dayanır. Manifest yanılabiliyordu (2026-08-05 / 4cast); geçmiş yanılmaz.
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bin"))
import kernel_dosyalari as kd  # noqa: E402


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(ROOT, "bin", f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(kok, *arg):
    subprocess.run(["git", "-C", kok, *arg], check=True,
                   capture_output=True, text=True)


def yaz(kok, rel, icerik):
    yol = os.path.join(kok, rel)
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as fh:
        fh.write(icerik)


class MotorListesiTest(unittest.TestCase):
    def test_liste_tekrarsiz(self):
        hepsi = kd.MOTOR + kd.MOTOR_DIZIN
        self.assertEqual(len(hepsi), len(set(hepsi)), "listede tekrar var")

    def test_listedeki_her_giris_repoda_var(self):
        # yol_coz: proje dizini `Docs/` olabilir, motor `docs/` yazar.
        # Düz os.path.exists Linux'ta yanlış negatif verir (4cast, 2026-08-07).
        for rel in kd.MOTOR + kd.MOTOR_DIZIN:
            self.assertIsNotNone(kd.yol_coz(ROOT, rel),
                                 f"listede ama repoda yok: {rel}")

    def test_kendi_araclarini_tasir(self):
        # Geri taşıma yolu bağlı projeye de gitmeli, yoksa orada kullanılamaz
        for rel in ("bin/kernel_dosyalari.py", "bin/auras_geri.py"):
            self.assertIn(rel, kd.MOTOR, f"{rel} motor listesinde yok")


class KurulumBagimliligiTest(unittest.TestCase):
    """Taşınan test, taşınmayan dosyayı şart koşamaz.

    2026-08-07 / 4Flow: `tests/` motor dizini olduğu için KapsamSiniriTest
    her projeye taşındı, ama şart koştuğu `docs/yasam-dongusu-kapsami.md`
    motor listesinde yoktu — taze kurulum 4 test kırmızı başladı. Kutudan
    kırmızı çıkan kurulum, insana kapıyı baştan yok saymayı öğretir.
    """

    def test_bu_repoda_eksik_bagimlilik_yok(self):
        eksik = kd.eksik_test_bagimliliklari(ROOT)
        self.assertEqual(
            eksik, [],
            "taşınan testler taşınmayan dosya istiyor: " +
            ", ".join(f"{t} → {r}" for t, r in eksik))

    def test_yol_coz_buyuk_kucuk_harf_duyarsiz(self):
        """Proje `Docs/` kullanabilir, motor `docs/` yazar.

        macOS duyarsız olduğu için yerelde sorun çıkmıyor ama git yolu
        YAZILDIĞI gibi saklıyor; Linux CI'da dosya "yok" görünüp kapı
        yanlış yere kırmızı yanıyordu (4cast, 2026-08-07).
        """
        with tempfile.TemporaryDirectory() as td:
            yaz(td, "Docs/belge.md", "içerik\n")
            self.assertIsNotNone(kd.yol_coz(td, "docs/belge.md"))
            self.assertIsNone(kd.yol_coz(td, "docs/yok.md"))

    def test_kapsam_belgesi_motorla_gider(self):
        # Kullanıcı hangi aşamada kapı OLMADIĞINI bilmeden korunduğunu sanır.
        self.assertIn("docs/yasam-dongusu-kapsami.md", kd.MOTOR)

    def test_eksik_bagimlilik_yakalanir(self):
        with tempfile.TemporaryDirectory() as td:
            yaz(td, "docs/ozel.md", "kanonik-özel belge\n")
            yaz(td, "tests/test_x.py",
                'import os\nROOT = "."\n'
                'YOL = os.path.join(ROOT, "docs", "ozel.md")\n')
            self.assertEqual(kd.eksik_test_bagimliliklari(td),
                             [("test_x.py", "docs/ozel.md")])

    def test_motordaki_dosya_bagimliligi_sorun_degil(self):
        with tempfile.TemporaryDirectory() as td:
            yaz(td, "bin/route.py", "x = 1\n")     # MOTOR'da
            yaz(td, "tests/test_x.py",
                'import os\nROOT = "."\n'
                'YOL = os.path.join(ROOT, "bin", "route.py")\n')
            self.assertEqual(kd.eksik_test_bagimliliklari(td), [])

    def test_kurucunun_urettigi_dosya_sorun_degil(self):
        # Taban kurulumda üretilir; motor listesinde olması BEKLENMEZ.
        self.assertTrue(kd.kurulumda_bulunur(".agents/kalite-baseline.json"))
        self.assertTrue(kd.kurulumda_bulunur("AGENTS.md"))
        self.assertFalse(kd.kurulumda_bulunur("docs/rastgele-belge.md"))

    def test_kanonik_ozel_isaretli_test_denetim_disi(self):
        """Bağlı projede karşılığı olmayan test kırmızı vermemeli.

        Kurucunun kendisi (`bin/auras-init.sh`) projeye taşınmaz; onu
        denetleyen test de bağlı projede atlanmalı. İşaret gerekçesiyle
        yazılır ki "kapıyı susturmak" görünür bir karar olsun.
        """
        with tempfile.TemporaryDirectory() as td:
            yaz(td, "docs/ozel.md", "kanonik belge\n")
            yaz(td, "tests/test_x.py",
                "# kanonik-özel: yalnız şablon reposunda anlamlı\n"
                'import os\nROOT = "."\n'
                'YOL = os.path.join(ROOT, "docs", "ozel.md")\n')
            self.assertEqual(kd.eksik_test_bagimliliklari(td), [])


class TestKapsamiTest(unittest.TestCase):
    """Keşfe hiç girmeyen test dosyası sessizce kapsam kaybıdır.

    2026-08-07 bulgusu: PyYAML'sız yorumlayıcıda üç modül import'ta çöktü;
    süite `Ran 186` yazdı, PyYAML'lı yorumlayıcıda `Ran 220`. Eksilen 34 test
    "koşmadı" diye DEĞİL, hiç sayılmadığı için görünmedi. Aynı sessizlik
    yanlış adlandırılmış (`route_test.py`) ya da hiç test üretmeyen dosyada da
    olur — ve orada çıkış kodu bile 0'dır.
    """

    def test_kesfe_girmeyen_dosya_yakalanir(self):
        with tempfile.TemporaryDirectory() as td:
            yaz(td, "tests/route_test.py",       # `test*.py` desenine uymaz
                "import unittest\n"
                "class X(unittest.TestCase):\n    pass\n")
            self.assertEqual(kd.toplanmayan_testler(td, {"test_a"}),
                             ["route_test.py"])

    def test_dolayli_taban_sinifi_da_yakalanir(self):
        # Codex bulgusu (PR #26): taban sınıf takma adla gelirse `TestCase`
        # sözcüğü `class` satırında GEÇMEZ. Sözcüğe bakan bekçi burada kör
        # kalırdı — ve kör bekçi, olmayan korumaya güvendirir.
        with tempfile.TemporaryDirectory() as td:
            yaz(td, "tests/route_test.py",
                "import unittest\n"
                "Taban = unittest.TestCase\n"
                "class X(Taban):\n"
                "    def test_a(self):\n        pass\n")
            self.assertEqual(kd.toplanmayan_testler(td, set()),
                             ["route_test.py"])

    def test_async_test_metodu_da_yakalanir(self):
        # Codex bulgusu (PR #26, ikinci tur): IsolatedAsyncioTestCase alt
        # sınıfları `async def test_*` yazar. Takma adlı tabanla birleşince
        # her iki imza da ıskalanırdı.
        with tempfile.TemporaryDirectory() as td:
            yaz(td, "tests/async_test.py",
                "import unittest\n"
                "Taban = unittest.IsolatedAsyncioTestCase\n"
                "class X(Taban):\n"
                "    async def test_a(self):\n        pass\n")
            self.assertEqual(kd.toplanmayan_testler(td, set()),
                             ["async_test.py"])

    def test_toplanan_dosya_sorun_degil(self):
        with tempfile.TemporaryDirectory() as td:
            yaz(td, "tests/test_a.py",
                "import unittest\n"
                "class X(unittest.TestCase):\n    pass\n")
            self.assertEqual(kd.toplanmayan_testler(td, {"test_a"}), [])

    def test_testcase_tasimayan_yardimci_denetlenmez(self):
        # tests/ortam.py gibi paylaşılan yardımcılar test üretmez; keşfe
        # girmemeleri normaldir, kapsam kaybı değildir.
        with tempfile.TemporaryDirectory() as td:
            yaz(td, "tests/ortam.py", "YAML = None\n")
            self.assertEqual(kd.toplanmayan_testler(td, set()), [])

    def test_bu_reponun_her_test_dosyasi_toplaniyor(self):
        toplanan = {f[:-3] for f in os.listdir(os.path.join(ROOT, "tests"))
                    if f.startswith("test_") and f.endswith(".py")}
        self.assertEqual(kd.toplanmayan_testler(ROOT, toplanan), [])


class SiniflaTest(unittest.TestCase):
    def kur(self, td):
        """Kanonik: v1 commit'li, sonra v2. Hedef: boş dizin."""
        kanonik = os.path.join(td, "kanonik")
        hedef = os.path.join(td, "proje")
        os.makedirs(kanonik)
        os.makedirs(hedef)
        git(kanonik, "init", "-b", "main")
        git(kanonik, "config", "user.email", "t@t.t")
        git(kanonik, "config", "user.name", "t")
        yaz(kanonik, "bin/x.py", "v1\n")
        git(kanonik, "add", "-A")
        git(kanonik, "commit", "-m", "v1")
        yaz(kanonik, "bin/x.py", "v2\n")
        git(kanonik, "add", "-A")
        git(kanonik, "commit", "-m", "v2")
        return kanonik, hedef

    def test_hedefte_yoksa_yok(self):
        with tempfile.TemporaryDirectory() as td:
            kanonik, hedef = self.kur(td)
            self.assertEqual(kd.sinifla(kanonik, hedef, "bin/x.py"), "yok")

    def test_ayni_icerik_ayni(self):
        with tempfile.TemporaryDirectory() as td:
            kanonik, hedef = self.kur(td)
            yaz(hedef, "bin/x.py", "v2\n")
            self.assertEqual(kd.sinifla(kanonik, hedef, "bin/x.py"), "ayni")

    def test_eski_kanonik_surumu_geride(self):
        # Proje yalnız eski sürümde kalmış → güvenle güncellenebilir
        with tempfile.TemporaryDirectory() as td:
            kanonik, hedef = self.kur(td)
            yaz(hedef, "bin/x.py", "v1\n")
            self.assertEqual(kd.sinifla(kanonik, hedef, "bin/x.py"), "geride")

    def test_gecmiste_olmayan_icerik_yerel(self):
        # ASIL BULGU: manifest ne derse desin, kanonikte hiç görülmemiş
        # içerik yerel iştir ve ezilemez.
        with tempfile.TemporaryDirectory() as td:
            kanonik, hedef = self.kur(td)
            yaz(hedef, "bin/x.py", "v2\n# projede yapilan duzeltme\n")
            self.assertEqual(kd.sinifla(kanonik, hedef, "bin/x.py"), "yerel")

    def test_kanonikte_hic_olmayan_dosya_yerel(self):
        with tempfile.TemporaryDirectory() as td:
            kanonik, hedef = self.kur(td)
            yaz(hedef, "bin/yeni.py", "proje skill'i\n")
            self.assertEqual(kd.sinifla(kanonik, hedef, "bin/yeni.py"), "yerel")

    def test_git_yoksa_temkinli_korur(self):
        # Geçmiş okunamıyorsa varsayılan KORUMAK olmalı; ezmek veri kaybıdır.
        with tempfile.TemporaryDirectory() as td:
            kanonik = os.path.join(td, "kanonik")     # git deposu DEĞİL
            hedef = os.path.join(td, "proje")
            yaz(kanonik, "bin/x.py", "v2\n")
            yaz(hedef, "bin/x.py", "farkli\n")
            self.assertEqual(kd.sinifla(kanonik, hedef, "bin/x.py"), "yerel")


class GeriTest(unittest.TestCase):
    def test_rapor_yerel_isi_ayirir(self):
        geri = _load("auras_geri")
        with tempfile.TemporaryDirectory() as td:
            kanonik = os.path.join(td, "kanonik")
            hedef = os.path.join(td, "proje")
            os.makedirs(kanonik)
            git(kanonik, "init", "-b", "main")
            git(kanonik, "config", "user.email", "t@t.t")
            git(kanonik, "config", "user.name", "t")
            yaz(kanonik, "bin/kapi.py", "eski\n")
            git(kanonik, "add", "-A")
            git(kanonik, "commit", "-m", "v1")
            yaz(hedef, "bin/kapi.py", "eski\n+yerel duzeltme\n")
            rapor = geri.incele(kanonik, hedef)
            self.assertEqual([y["dosya"] for y in rapor["yerel"]],
                             ["bin/kapi.py"])
            self.assertEqual(rapor["geride"], [])

    def test_al_kanonige_kopyalar_commit_etmez(self):
        geri = _load("auras_geri")
        with tempfile.TemporaryDirectory() as td:
            kanonik = os.path.join(td, "kanonik")
            hedef = os.path.join(td, "proje")
            yaz(kanonik, "bin/kapi.py", "eski\n")
            yaz(hedef, "bin/kapi.py", "yeni\n")
            alinan = geri.al(kanonik, hedef, ["bin/kapi.py"])
            self.assertEqual(alinan, ["bin/kapi.py"])
            with open(os.path.join(kanonik, "bin/kapi.py"),
                      encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "yeni\n")

    def test_projede_olmayan_dosya_atlanir(self):
        geri = _load("auras_geri")
        with tempfile.TemporaryDirectory() as td:
            kanonik = os.path.join(td, "kanonik")
            hedef = os.path.join(td, "proje")
            yaz(kanonik, "bin/kapi.py", "eski\n")
            os.makedirs(hedef, exist_ok=True)
            self.assertEqual(geri.al(kanonik, hedef, ["bin/kapi.py"]), [])


if __name__ == "__main__":
    unittest.main()


class GitleaksMuafiyetTest(unittest.TestCase):
    """Kernel manifest'i gitleaks'te yanlış pozitif üretmemeli (2026-08-07).

    4cast'te 7 yanlış pozitif CI'ı bir haftadan uzun kırmızıda tuttu; dosyayı
    kernel ÜRETTİĞİ için sorun bağlı her projede tekrarlanır.
    """

    def wf_ile(self, td, icerik="run: gitleaks detect"):
        os.makedirs(os.path.join(td, ".github", "workflows"), exist_ok=True)
        yaz(td, ".github/workflows/ci.yml", icerik + "\n")

    def test_workflowda_anilirsa_kullaniyor_sayilir(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertFalse(kd.gitleaks_kullaniyor(td))
            self.wf_ile(td)
            self.assertTrue(kd.gitleaks_kullaniyor(td))

    def test_config_varsa_kullaniyor_sayilir(self):
        with tempfile.TemporaryDirectory() as td:
            yaz(td, ".gitleaks.toml", "title = 'x'\n")
            self.assertTrue(kd.gitleaks_kullaniyor(td))

    def test_muafiyet_yoksa_tespit_edilir(self):
        with tempfile.TemporaryDirectory() as td:
            self.wf_ile(td)
            self.assertFalse(kd.manifest_muaf_mi(td))

    def test_sablon_kendi_kontrolunu_gecer(self):
        # Şablon regex kaçışı taşır (\.kernel-manifest\.json); kontrol düz
        # nokta arasaydı kendi şablonunu bile eşleştiremezdi (gerçek hata).
        with tempfile.TemporaryDirectory() as td:
            yaz(td, ".gitleaks.toml", kd.MUAFIYET_BLOGU)
            self.assertTrue(kd.manifest_muaf_mi(td),
                            "şablon kendi kontrolünü geçmiyor")

    def test_gitleaks_kullanmayan_proje_zorlanmaz(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertFalse(kd.gitleaks_kullaniyor(td))
