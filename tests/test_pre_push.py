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


def kur(td, proje_kapisi=None, kapi_calistirilabilir=True, tarayici=True):
    """İzole bir depoda kapıyı kurar; pre-push'un çıkış kodunu döndürür."""
    os.makedirs(os.path.join(td, "bin", "hooks"))
    shutil.copy2(os.path.join(ROOT, "bin", "hooks", "pre-push"),
                 os.path.join(td, "bin", "hooks", "pre-push"))
    with open(os.path.join(td, "bin", "validate.py"), "w") as fh:
        fh.write('#!/usr/bin/env python3\nprint("ok")\n')
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

    def test_calistirilamayan_proje_kapisi_sessizce_atlanmaz(self):
        # chmod unutulursa kapı kaybolurdu — görünür hata olmalı
        with tempfile.TemporaryDirectory() as td:
            kod, cikti = kur(td, "#!/bin/sh\nexit 1\n",
                             kapi_calistirilabilir=False)
            self.assertEqual(kod, 1)
            self.assertIn("calistirilabilir degil", cikti)


if __name__ == "__main__":
    unittest.main()
