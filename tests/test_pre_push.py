#!/usr/bin/env python3
"""pre-push kapısının davranışı — izole depoda, gerçek script ile.

Kapı üç şeyi zorlar: kernel doğrulaması, secret taraması, proje kapısı.
Üçünün de "yok" hâli "geçti" OLAMAZ; sessiz atlama en tehlikeli hatadır
(koruma illüzyonu). Bu testler o sessizlikleri kilitler.
"""
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_REL = ".agents/skills/security-review/scripts/scan_secrets.py"


def kur(td, proje_kapisi=None, kapi_calistirilabilir=True, tarayici=True,
        validate_kod=0):
    """İzole bir depoda kapıyı kurar; pre-push'un çıkış kodunu döndürür.

    validate_kod: sahte kernel doğrulayıcısının çıkış kodu.
      0 geçti · 1 kural ihlali · 2 araç hatası (doğrulama koşamadı).
    """
    os.makedirs(os.path.join(td, "bin", "hooks"))
    shutil.copy2(os.path.join(ROOT, "bin", "hooks", "pre-push"),
                 os.path.join(td, "bin", "hooks", "pre-push"))
    with open(os.path.join(td, "bin", "validate.py"), "w") as fh:
        fh.write("#!/usr/bin/env python3\nimport sys\n"
                 f'print("ok")\nsys.exit({validate_kod})\n')
    if tarayici:
        hedef = os.path.join(td, SCAN_REL)
        os.makedirs(os.path.dirname(hedef))
        shutil.copy2(os.path.join(ROOT, SCAN_REL), hedef)
    with open(os.path.join(td, "temiz.py"), "w") as fh:
        fh.write("x = 1\n")
    if proje_kapisi is not None:
        yol = os.path.join(td, "bin", "hooks", "proje-kapisi")
        with open(yol, "w") as fh:
            fh.write(proje_kapisi)
        if kapi_calistirilabilir:
            os.chmod(yol, 0o755)
        else:
            os.chmod(yol, 0o644)
    subprocess.run(["git", "init", "-q", "-b", "main", td], check=True,
                   capture_output=True)
    # Dosyalar STAGE edilmeli: secret kapısı --git modunda yalnız izlenen
    # içeriği tarar (push edilecek olan budur). Stage'lenmemiş depo "0 dosya
    # tarandı" verir ve bu bilinçli olarak 'temiz' sayılmaz.
    subprocess.run(["git", "-C", td, "add", "-A"], check=True,
                   capture_output=True)
    # input="" ŞART: pre-push sonunda 'while read' ile git'ten ref bekler;
    # stdin miras alınırsa test süresiz asılır.
    p = subprocess.run(["sh", os.path.join(td, "bin", "hooks", "pre-push")],
                       capture_output=True, text=True, cwd=td, timeout=60,
                       input="")
    return p.returncode, p.stdout + p.stderr


class PrePushTest(unittest.TestCase):
    def test_temiz_depo_gecer(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(kur(td)[0], 0)

    def test_kural_ihlali_bloklar(self):
        with tempfile.TemporaryDirectory() as td:
            kod, cikti = kur(td, validate_kod=1)
            self.assertEqual(kod, 1)
            self.assertIn("dogrulamasi basarisiz", cikti)

    def test_arac_hatasi_ihlalden_ayrilir(self):
        """"Koşamadı" ile "kaldı" aynı mesajı almaz.

        2026-08-07: Homebrew python3'u 3.14'e taşıdı, PyYAML yeni
        yorumlayıcıda yoktu; validate.py 2 ile çıktı, kapı "dogrulama
        BASARISIZ" dedi. Kullanıcı olmayan bir kural ihlalini aramaya
        başlar. İkisi de bloklar (fail-closed doğru), ama sebep doğru
        söylenmeli — yanlış teşhis --no-verify alışkanlığı üretir.
        """
        with tempfile.TemporaryDirectory() as td:
            kod, cikti = kur(td, validate_kod=2)
            self.assertEqual(kod, 1, "araç hatası da bloklamalı (fail-closed)")
            self.assertIn("KOSAMADI", cikti)
            self.assertNotIn("dogrulamasi basarisiz", cikti)

    def test_tarayici_yoksa_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            kod, cikti = kur(td, tarayici=False)
            self.assertEqual(kod, 1, "tarayıcı yoksa sessizce geçmemeli")
            self.assertIn("tarayicisi bulunamadi", cikti)

    def test_proje_kapisi_yoksa_gecer(self):
        # Uzantı noktası OPSİYONEL — yokluğu ihlal değildir
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(kur(td, proje_kapisi=None)[0], 0)

    def test_proje_kapisi_ihlalde_bloklar(self):
        with tempfile.TemporaryDirectory() as td:
            kod, cikti = kur(td, '#!/bin/sh\necho "yasak: X"\nexit 1\n')
            self.assertEqual(kod, 1)
            self.assertIn("proje kapisi gecilemedi", cikti)

    def test_proje_kapisi_temizse_gecer(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(kur(td, "#!/bin/sh\nexit 0\n")[0], 0)

    def test_proje_kapisi_ref_akisini_yiyemez(self):
        """Denetim bulgusu: kapı stdin okursa git'in ref listesini yer.

        O zaman sonraki while-read hiçbir ref görmez ve ref'e dayanan her
        politika (ör. 'main'e doğrudan push' uyarısı) sessizce kaybolur.
        """
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, "bin", "hooks"))
            shutil.copy2(os.path.join(ROOT, "bin", "hooks", "pre-push"),
                         os.path.join(td, "bin", "hooks", "pre-push"))
            with open(os.path.join(td, "bin", "validate.py"), "w") as fh:
                fh.write('#!/usr/bin/env python3\nprint("ok")\n')
            hedef = os.path.join(td, SCAN_REL)
            os.makedirs(os.path.dirname(hedef))
            shutil.copy2(os.path.join(ROOT, SCAN_REL), hedef)
            with open(os.path.join(td, "temiz.py"), "w") as fh:
                fh.write("x = 1\n")
            # Stdin'i sonuna kadar yiyen bir proje kapısı
            yol = os.path.join(td, "bin", "hooks", "proje-kapisi")
            with open(yol, "w") as fh:
                fh.write("#!/bin/sh\ncat >/dev/null\nexit 0\n")
            os.chmod(yol, 0o755)
            subprocess.run(["git", "init", "-q", "-b", "main", td], check=True,
                           capture_output=True)
            subprocess.run(["git", "-C", td, "add", "-A"], check=True,
                           capture_output=True)
            p = subprocess.run(
                ["sh", os.path.join(td, "bin", "hooks", "pre-push")],
                capture_output=True, text=True, cwd=td, timeout=60,
                input="refs/heads/main aaa refs/heads/main bbb\n")
            self.assertEqual(p.returncode, 0)
            self.assertIn("dogrudan main", p.stdout,
                          "proje kapısı git'in ref akışını yemiş — ref'e "
                          "dayanan politikalar sessizce kayboluyor")

    def test_calistirilamayan_proje_kapisi_sessizce_atlanmaz(self):
        # chmod unutulursa kapı kaybolurdu — görünür hata olmalı
        with tempfile.TemporaryDirectory() as td:
            kod, cikti = kur(td, "#!/bin/sh\nexit 1\n",
                             kapi_calistirilabilir=False)
            self.assertEqual(kod, 1)
            self.assertIn("calistirilabilir degil", cikti)


if __name__ == "__main__":
    unittest.main()
