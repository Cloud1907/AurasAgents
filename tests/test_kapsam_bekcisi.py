#!/usr/bin/env python3
"""Kapsam bekçisi — keşfe girmeyen test dosyası sessiz kapsam kaybıdır.

Bu bekçi beş inceleme turunda beş kez sızdırdı ve her seferinde kaçak bir
METİN DESENİ varsayımından geldi. Buradaki her test o turlardan birini
kilitler; hepsi düzeltmeden ÖNCE kırmızıydı.
"""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bin"))
import kernel_dosyalari as kd  # noqa: E402


def yaz(kok, rel, icerik):
    yol = os.path.join(kok, rel)
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as fh:
        fh.write(icerik)


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

    def test_dis_taban_sinifi_da_yakalanir(self):
        # Codex bulgusu (PR #26, üçüncü tur): taban BAŞKA dosyadan gelirse
        # `unittest` adı bu dosyada hiç geçmez. Kural üçüncü kez aynı yerden
        # sızdı — çare deseni bir kez daha genişletmek değil, VARSAYILANI
        # çevirmek: test metodu varsa dosya toplanmalıdır, aksi açıkça yazılır.
        with tempfile.TemporaryDirectory() as td:
            yaz(td, "tests/dis_test.py",
                "from ortak_taban import Taban\n"
                "class X(Taban):\n"
                "    def test_a(self):\n        pass\n")
            self.assertEqual(kd.toplanmayan_testler(td, set()),
                             ["dis_test.py"])

    def test_toplanmaz_isareti_gerekceyle_muaf_tutar(self):
        # Kasıtlı yardımcı (paylaşılan mixin) susturulabilir — ama GÖRÜNÜR
        # ve gerekçeli. Gerekçesiz işaret muafiyet saymaz.
        with tempfile.TemporaryDirectory() as td:
            yaz(td, "tests/ortak.py",
                "# toplanmaz: paylasilan mixin, alt siniflar uzerinden kosar\n"
                "class Ortak:\n"
                "    def test_a(self):\n        pass\n")
            self.assertEqual(kd.toplanmayan_testler(td, set()), [])

    def test_string_icindeki_isaret_muaf_tutmaz(self):
        # Codex bulgusu (PR #30): işaret ham metinde arandığı için bir
        # fixture string'i dosyayı muaf tutuyordu. Tarayıcının kendi test
        # dosyasını görmemesi kapının en kötü kör noktasıdır — muafiyet
        # yalnız satır başındaki GERÇEK yorumla verilir.
        with tempfile.TemporaryDirectory() as td:
            yaz(td, "tests/sahte_test.py",
                "import unittest\n"
                'ORNEK = "# toplanmaz: bu bir fixture, gercek isaret degil"\n'
                "class X(unittest.TestCase):\n"
                "    def test_a(self):\n        pass\n")
            self.assertEqual(kd.toplanmayan_testler(td, set()),
                             ["sahte_test.py"])

    def test_bu_dosya_kendini_muaf_tutmuyor(self):
        # Bu dosya fixture'larında '# toplanmaz:' metnini TAŞIYOR; bekçi
        # onu muafiyet sayarsa kendi test dosyasına kör kalır.
        #
        # Ad `__file__`den okunur, elle yazılmaz: bu sınıf bir kez taşındı ve
        # sabit ad geride kalsaydı test YANLIŞ SEBEPLE yeşil kalırdı — işareti
        # taşımayan bir dosyayı denetliyor olurdu.
        self.assertIn(os.path.basename(__file__),
                      kd.toplanmayan_testler(ROOT, set()))

    def test_uc_tirnak_icindeki_isaret_muaf_tutmaz(self):
        # Codex bulgusu (PR #30, ikinci tur): satır başı kuralı ham metinde
        # uygulanınca docstring/fixture içindeki satır da "yorum" sayılıyordu.
        with tempfile.TemporaryDirectory() as td:
            yaz(td, "tests/sahte_test.py",
                'ORNEK = """\n'
                "# toplanmaz: bu bir fixture govdesi, gercek yorum degil\n"
                '"""\n'
                "import unittest\n"
                "class X(unittest.TestCase):\n"
                "    def test_a(self):\n        pass\n")
            self.assertEqual(kd.toplanmayan_testler(td, set()),
                             ["sahte_test.py"])

    def test_self_olmayan_ilk_parametre_de_yakalanir(self):
        # Codex bulgusu (PR #30, ikinci tur): ilk parametre adı sözleşme
        # değildir; `cls`, `_` ya da başka bir ad da geçerli test metodudur.
        with tempfile.TemporaryDirectory() as td:
            yaz(td, "tests/dis_test.py",
                "from ortak_taban import Taban\n"
                "class X(Taban):\n"
                "    def test_a(cls):\n        pass\n")
            self.assertEqual(kd.toplanmayan_testler(td, set()),
                             ["dis_test.py"])

    def test_satir_ici_isaret_muaf_tutmaz(self):
        # Codex bulgusu (PR #30, üçüncü tur): tokenize'a geçerken sütun
        # bilgisi düşmüştü. Muafiyet dosya düzeyinde bir BEYANDIR; bir kod
        # satırının kuyruğunda ya da metot gövdesinde kazara doğamaz.
        with tempfile.TemporaryDirectory() as td:
            yaz(td, "tests/kuyruk_test.py",
                "import unittest\n"
                "X = 1  # toplanmaz: kuyrukta, beyan degil\n"
                "class Y(unittest.TestCase):\n"
                "    def test_a(self):\n"
                "        # toplanmaz: govdede, beyan degil\n"
                "        pass\n")
            self.assertEqual(kd.toplanmayan_testler(td, set()),
                             ["kuyruk_test.py"])

    def test_kosul_icinde_tanimlanan_test_de_yakalanir(self):
        # Codex bulgusu (PR #30, dördüncü tur): yalnız doğrudan sınıf gövdesi
        # geziliyordu; `if`/`try` içinde tanımlanan metot görünmüyordu.
        # Sınıf gövdesi düz bir liste değil, bir AĞAÇTIR.
        with tempfile.TemporaryDirectory() as td:
            yaz(td, "tests/kosul_test.py",
                "import sys\n"
                "Taban = __import__('unittest').TestCase\n"
                "class X(Taban):\n"
                "    if sys.version_info >= (3, 8):\n"
                "        def test_a(self):\n            pass\n")
            self.assertEqual(kd.toplanmayan_testler(td, set()),
                             ["kosul_test.py"])

    def test_gerekcesiz_toplanmaz_isareti_muaf_tutmaz(self):
        with tempfile.TemporaryDirectory() as td:
            yaz(td, "tests/ortak.py",
                "# toplanmaz:\n"
                "class Ortak:\n"
                "    def test_a(self):\n        pass\n")
            self.assertEqual(kd.toplanmayan_testler(td, set()), ["ortak.py"])

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


if __name__ == "__main__":
    unittest.main()
