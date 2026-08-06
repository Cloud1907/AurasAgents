#!/usr/bin/env python3
"""Kapıya bağlanan skill doğrulayıcıları — bekçinin bekçisi.

Bu scriptler artık pre-push ve CI'da blocking koşuyor. Sessizce bozulurlarsa
kapı sahte-yeşile döner (en tehlikeli hâl: kural var sanılır, yok). Bu yüzden
davranışları burada kilitlenir.
"""
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN = os.path.join(ROOT, ".agents", "skills", "security-review",
                    "scripts", "scan_secrets.py")
TESTFIRST = os.path.join(ROOT, ".agents", "skills", "implement-change",
                         "scripts", "check_test_first.py")

# Stripe dokümanındaki örnek anahtar — gerçek hesaba ait değil. Parçalı
# kurulur: düz yazılırsa bu dosyanın KENDİSİ secret kapısına takılır
# (tests/test_memory_hygiene.py aynı konvansiyonu kullanır).
ORNEK_ANAHTAR = "sk_" + "live_4eC39HqLyjWDarjtT1zdp7dc"


def kos(script, *arg):
    p = subprocess.run([sys.executable, script, *arg],
                       capture_output=True, text=True, cwd=ROOT, timeout=60)
    return p.returncode, p.stdout


class ScanSecretsTest(unittest.TestCase):
    def test_gercek_secret_yakalanir(self):
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "cfg.py"), "w") as fh:
                fh.write(f'KEY = "{ORNEK_ANAHTAR}"\n')
            kod, cikti = kos(SCAN, td)
            self.assertEqual(kod, 1, "secret bulunmalıydı")
            self.assertIn("cfg.py", cikti)

    def test_placeholder_tetiklemez(self):
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "ornek.env"), "w") as fh:
                fh.write('API_KEY="your-api-key-here"\nTOKEN=xxx\n')
            self.assertEqual(kos(SCAN, td)[0], 0, "placeholder yanlış pozitif")

    def test_exclude_dislar(self):
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, "eval"))
            with open(os.path.join(td, "eval", "cases.md"), "w") as fh:
                fh.write(f"beklenen bulgu: {ORNEK_ANAHTAR}\n")
            # Dışlanmayan temiz dosya ŞART: yoksa "hiç taranmadı" durumu
            # doğar ve o 'temiz' değildir (bkz. test_asiri_genis_dislama).
            with open(os.path.join(td, "temiz.py"), "w") as fh:
                fh.write("x = 1\n")
            self.assertEqual(kos(SCAN, td)[0], 1, "dışlamasız yakalanmalı")
            self.assertEqual(kos(SCAN, "--exclude", "*/eval/*", td)[0], 0,
                             "dışlama uygulanmadı")

    def test_exclude_kapsam_disini_korur(self):
        # Dışlama fazla geniş olmamalı: eval DIŞINDAKİ secret hâlâ yakalanır
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, "eval"))
            with open(os.path.join(td, "eval", "cases.md"), "w") as fh:
                fh.write(f"fixture: {ORNEK_ANAHTAR}\n")
            with open(os.path.join(td, "gercek.py"), "w") as fh:
                fh.write(f'K = "{ORNEK_ANAHTAR}"\n')
            kod, cikti = kos(SCAN, "--exclude", "*/eval/*", td)
            self.assertEqual(kod, 1)
            self.assertIn("gercek.py", cikti)
            self.assertNotIn("cases.md", cikti)

    def test_yolsuz_cagri_kullanim_hatasi(self):
        self.assertEqual(kos(SCAN, "--exclude", "*/eval/*")[0], 2)

    # --- güvenlik denetimi bulguları (2026-08-06) — fail-open sınıfı ---

    def test_degersiz_exclude_temiz_demez(self):
        # Bulgu: '--exclude' yol sanılıp tarama boşa düşüyor, exit 0 "temiz ✓"
        kod, cikti = kos(SCAN, "--exclude")
        self.assertEqual(kod, 2, "değersiz --exclude kullanım hatası olmalı")
        self.assertNotIn("temiz", cikti)

    def test_hic_dosya_taranmadiysa_temiz_demez(self):
        # Bulgu: var olmayan yol → 0 bulgu → "temiz ✓" + exit 0 (sahte yeşil)
        kod, cikti = kos(SCAN, "/yok/boyle/bir/dizin")
        self.assertEqual(kod, 2, "hiç dosya taranmadıysa 'temiz' denemez")
        self.assertNotIn("temiz", cikti)

    def test_asiri_genis_dislama_temiz_demez(self):
        # Dışlama her şeyi yerse bu da "taranmadı"dır, "temiz" değil
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "a.py"), "w") as fh:
                fh.write(f'K = "{ORNEK_ANAHTAR}"\n')
            self.assertEqual(kos(SCAN, "--exclude", "*", td)[0], 2)

    def test_git_modu_izlenmeyen_dosyayi_taramaz(self):
        """OICommand bulgusu: .gitignore'lu .env.local push'u blokluyordu.

        Push kapısı git'in GÖNDERECEĞİ içeriğe bakmalı; izlenmeyen dosya
        uzak depoya gitmez. Aksi hâlde kullanıcı --no-verify öğrenir.
        """
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["git", "init", "-q", "-b", "main", td], check=True,
                           capture_output=True)
            for k, v in (("user.email", "t@t.t"), ("user.name", "t")):
                subprocess.run(["git", "-C", td, "config", k, v], check=True,
                               capture_output=True)
            with open(os.path.join(td, ".gitignore"), "w") as fh:
                fh.write("*.local\n")
            with open(os.path.join(td, "app.env.local"), "w") as fh:
                fh.write(f'KEY = "{ORNEK_ANAHTAR}"\n')
            with open(os.path.join(td, "izlenen.py"), "w") as fh:
                fh.write("x = 1\n")
            subprocess.run(["git", "-C", td, "add", "-A"], check=True,
                           capture_output=True)
            self.assertEqual(kos(SCAN, td)[0], 1,
                             "--git'siz tarama izlenmeyeni de görmeli")
            self.assertEqual(kos(SCAN, "--git", td)[0], 0,
                             "--git modu izlenmeyen dosyayı taramamalı")

    def test_git_modu_izlenen_secreti_hala_yakalar(self):
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["git", "init", "-q", "-b", "main", td], check=True,
                           capture_output=True)
            with open(os.path.join(td, "cfg.py"), "w") as fh:
                fh.write(f'KEY = "{ORNEK_ANAHTAR}"\n')
            subprocess.run(["git", "-C", td, "add", "-A"], check=True,
                           capture_output=True)
            kod, cikti = kos(SCAN, "--git", td)
            self.assertEqual(kod, 1)
            self.assertIn("cfg.py", cikti)

    def test_git_olmayan_dizinde_git_modu_temiz_demez(self):
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "a.py"), "w") as fh:
                fh.write("x = 1\n")
            kod, cikti = kos(SCAN, "--git", td)
            self.assertEqual(kod, 2, "git deposu değilse 'temiz' denemez")
            self.assertNotIn("temiz", cikti)

    def test_nokta_ile_baslayan_yol_deseni_eslesir(self):
        # Bulgu: lstrip('./') '.agents/...' → 'agents/...' yapıyordu; nokta
        # ile başlayan kesin desen sessizce eşleşmiyordu → operatör deseni
        # gereğinden geniş tutmaya itiliyordu.
        sys.path.insert(0, os.path.dirname(SCAN))
        import scan_secrets as ss
        self.assertTrue(ss.is_excluded(".agents/skills/x/eval/c.md",
                                       [".agents/skills/*/eval/*"]))
        self.assertFalse(ss.is_excluded(".agents/skills/x/src/c.py",
                                        [".agents/skills/*/eval/*"]))


class CheckTestFirstTest(unittest.TestCase):
    def test_kaynak_varken_testsiz_diff_uyarir(self):
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["git", "init", "-b", "main", td], check=True,
                           capture_output=True)
            for k, v in (("user.email", "t@t.t"), ("user.name", "t")):
                subprocess.run(["git", "-C", td, "config", k, v], check=True,
                               capture_output=True)
            with open(os.path.join(td, "app.py"), "w") as fh:
                fh.write("x = 1\n")
            subprocess.run(["git", "-C", td, "add", "-A"], check=True,
                           capture_output=True)
            subprocess.run(["git", "-C", td, "commit", "-m", "ilk"],
                           check=True, capture_output=True)
            with open(os.path.join(td, "app.py"), "a") as fh:
                fh.write("y = 2\n")
            p = subprocess.run([sys.executable, TESTFIRST],
                               capture_output=True, text=True, cwd=td,
                               timeout=60)
            self.assertEqual(p.returncode, 1,
                             "kaynak değişti test değişmedi — uyarmalıydı")


if __name__ == "__main__":
    unittest.main()
