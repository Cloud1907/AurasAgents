#!/usr/bin/env python3
"""Kişisel veri kapısı — sır taramasından AYRI bir boyut.

Sır tarayıcısı "bu değer bir anahtar mı" diye sorar; bu tarayıcı "bu dosya
bir insan listesi mi" diye sorar. Üretimde iki ayrı script (scan_secrets.py /
scan_personal_data.py); testleri de ayrı durur — tek dosyada birikirse hangi
kapının neyi garanti ettiği okunmaz hâle gelir.
"""
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PII = os.path.join(ROOT, ".agents", "skills", "security-review",
                   "scripts", "scan_personal_data.py")


def kos(script, *arg):
    p = subprocess.run([sys.executable, script, *arg],
                       capture_output=True, text=True, cwd=ROOT, timeout=60)
    return p.returncode, p.stdout + p.stderr


class KisiselVeriTest(unittest.TestCase):
    """Toplu kişisel veri dökümü — sır değil ama repoda durmamalı.

    4Flow'da bulundu (2026-08-07): `users_list.json`, bir üretim API
    çıktısının dosyaya dökülmüş hâli — 20 kişinin adı, soyadı ve kurumsal
    e-postası. Tarayıcı "temiz" dedi ve DOĞRU davrandı: parola/anahtar
    arıyordu, kişisel veri aramıyordu. Yani kapıda bu boyut hiç yoktu.

    Ölçüt TEK e-posta değil TOPLU dökümdür: bir yorumdaki iletişim adresi
    ihlal değil, 20 kişilik liste dökümüdür. Tek adres eşiği yanlış pozitif
    üretir ve kapıyı güvenilmez yapar.
    """

    def kur(self, td, icerik, ad="dump.json"):
        with open(os.path.join(td, ad), "w", encoding="utf-8") as fh:
            fh.write(icerik)
        with open(os.path.join(td, "temiz.py"), "w") as fh:
            fh.write("x = 1\n")
        return td

    def test_toplu_eposta_dokumu_yakalanir(self):
        with tempfile.TemporaryDirectory() as td:
            kisiler = ", ".join(
                f'{{"email":"kisi{i}@sirket.com.tr","fullName":"Kisi {i}"}}'
                for i in range(20))
            self.kur(td, "[" + kisiler + "]")
            kod, cikti = kos(PII, td)
            self.assertEqual(kod, 1, cikti)
            self.assertIn("dump.json", cikti)
            self.assertIn("kişisel veri", cikti)

    def test_tek_eposta_yanlis_pozitif_uretmez(self):
        # Bir yorumdaki iletişim adresi ihlal değildir.
        with tempfile.TemporaryDirectory() as td:
            self.kur(td, "# soru olursa: destek@sirket.com\n", "not.md")
            self.assertEqual(kos(PII, td)[0], 0)

    def test_bir_avuc_eposta_yanlis_pozitif_uretmez(self):
        # Eşiğin altı: CODEOWNERS/yazar listesi gibi meşru küçük kümeler.
        with tempfile.TemporaryDirectory() as td:
            self.kur(td, "\n".join(f"a{i}@x.com" for i in range(4)), "not.md")
            self.assertEqual(kos(PII, td)[0], 0)

    def test_katki_dosyalari_muaf(self):
        # AUTHORS/CONTRIBUTORS listesi TANIMI GEREĞİ kişi listesidir.
        with tempfile.TemporaryDirectory() as td:
            self.kur(td, "\n".join(f"Kisi {i} <k{i}@x.com>" for i in range(20)),
                     "AUTHORS")
            self.assertEqual(kos(PII, td)[0], 0)

    def test_toplu_tc_kimlik_yakalanir(self):
        with tempfile.TemporaryDirectory() as td:
            # 11 haneli, birbirinden farklı sayılar
            self.kur(td, "\n".join(str(10000000000 + i * 7919) for i in range(12)),
                     "kimlikler.csv")
            kod, cikti = kos(PII, td)
            self.assertEqual(kod, 1, cikti)
            self.assertIn("kişisel veri", cikti)


if __name__ == "__main__":
    unittest.main()
