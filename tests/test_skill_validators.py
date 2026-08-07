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

# Muafiyet testlerinin fixture parolası. AYNI konvansiyon: düz yazılırsa bu
# dosyanın KENDİSİ secret kapısına takılır — bugün bizzat takıldı (push
# engellendi, 2 bulgu, ikisi de bu satırlar). Tarayıcının kendi testini
# bloklaması ironik değil, DOĞRU davranış; kaçış yolu muafiyet değil,
# fixture'ı desene uymayacak biçimde kurmaktır.
FIXTURE_PAROLA = "pass" + "word123"


def kos(script, *arg):
    p = subprocess.run([sys.executable, script, *arg],
                       capture_output=True, text=True, cwd=ROOT, timeout=60)
    # stderr de kapı çıktısıdır: kullanım hataları oraya yazılır ve
    # "kapı ne dedi" iddiaları onu görmezse eksik denetlenir.
    return p.returncode, p.stdout + p.stderr


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
        self.assertNotIn("scan_secrets: temiz", cikti,
                         "kapı temiz İDDİASINDA bulunmamalı")

    def test_hic_dosya_taranmadiysa_temiz_demez(self):
        # Bulgu: var olmayan yol → 0 bulgu → "temiz ✓" + exit 0 (sahte yeşil)
        kod, cikti = kos(SCAN, "/yok/boyle/bir/dizin")
        self.assertEqual(kod, 2, "hiç dosya taranmadıysa 'temiz' denemez")
        self.assertNotIn("scan_secrets: temiz", cikti,
                         "kapı temiz İDDİASINDA bulunmamalı")

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
            self.assertNotIn("scan_secrets: temiz", cikti,
                         "kapı temiz İDDİASINDA bulunmamalı")

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


CITATIONS = os.path.join(ROOT, ".agents", "skills", "research-with-evidence",
                         "scripts", "check_citations.py")


class IsabetTest(unittest.TestCase):
    """Yanlış pozitif azaltma — kapının en pahalı hatası.

    4Flow kurulumunda 6 dosya yalnız ROTA YOLU ve DEĞİŞKEN REFERANSI yüzünden
    yakalandı (`"api/auth/change-password"`, `'$SqlPassword'`). Her repoya
    muafiyet satırı yazmak yanlış çözüm: kural yanlış yakalıyorsa düzeltilecek
    yer kuraldır, muafiyet listesi değil. Muafiyet "bilinen sırrı affet"
    demektir; burada ortada sır YOK.
    """

    def hits(self, satir):
        sys.path.insert(0, os.path.dirname(SCAN))
        import scan_secrets as ss
        return [ad for ad, _v in ss.scan_line(satir)]

    def test_sablon_dosyasi_taranmaz(self):
        """`.env.example` gibi şablonlar örnek değer TAŞIMAK içindir.

        Placeholder filtresi yalnız İngilizce kalıpları tanıyor; 4Flow'un
        `.env.example`'ındaki "yerel-parolasi" kaçtı ve kapı bloklandı.
        Şablonlar her repoda var — dosya adına bakmak doğru çözüm.
        """
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, ".env.example"), "w") as fh:
                # Parçalı: düz yazılırsa bu test dosyası kapıya takılır.
                fh.write('DB_PASSWORD="%s"\n' % ("buraya-kendi-" + "parolani-yaz"))
            with open(os.path.join(td, "temiz.py"), "w") as fh:
                fh.write("x = 1\n")
            self.assertEqual(kos(SCAN, td)[0], 0, "şablon dosyası bloklamamalı")

    def test_gercek_env_hala_taranir(self):
        # Şablon muafiyeti `.env`in kendisine SIZMAMALI.
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "app.env"), "w") as fh:
                fh.write(f'KEY = "{ORNEK_ANAHTAR}"\n')
            self.assertEqual(kos(SCAN, td)[0], 1, ".env taranmaya devam etmeli")

    def test_rota_yolu_parola_sayilmaz(self):
        for satir in ('const val CHANGE_PASSWORD = "api/auth/change-password"',
                      'PASSWORD_RESET = "/api/v1/auth/reset-password"',
                      'url: "https://x.test/account/change-password"'):
            with self.subTest(satir=satir):
                self.assertEqual(self.hits(satir), [], satir)

    def test_degisken_referansi_parola_sayilmaz(self):
        for satir in ("WITH PASSWORD = '$SqlPassword', CHECK_POLICY = OFF;",
                      'password: "${DB_PASSWORD}"',
                      "password: '{{ vault_pass }}'",
                      'password: "%s" % gizli'):
            with self.subTest(satir=satir):
                self.assertEqual(self.hits(satir), [], satir)

    def test_gercek_parola_hala_yakalanir(self):
        # İsabet artışı, kapıyı körleştirmemeli.
        # Parçalı kurulum ZORUNLU: düz yazılırsa bu dosya secret kapısına
        # takılır ve push engellenir (bugün iki kez oldu).
        gercek = "hunt" + "er2diller"
        for satir in (f'password = "{gercek}"',
                      "DB_PASS: '%s'" % ("Pr0d!" + "Secret9")):
            with self.subTest(satir=satir):
                self.assertIn("Hardcoded parola", self.hits(satir), satir)


class ProjeMuafiyetiTest(unittest.TestCase):
    """Projenin kendi muafiyet dosyası — GEREKÇELİ ve GÖRÜNÜR.

    Neden gerekli (4Flow kurulumu, 2026-08-07): projede meşru test fixture'ı
    vardı (dummy kullanıcıya verilen sabit parola, localhost'a istek atan
    yerel betik). Tarayıcının projeye özel muafiyet yolu YOKTU — yalnız
    pre-push'a gömülü `--exclude */eval/*`. Yani proje ya kapıyı hiç
    geçemeyecek ya da motor dosyasını çatallayacaktı; ikisi de yanlış.

    Tasarım kuralı: muafiyet SESSİZ OLAMAZ. Her satır gerekçe ister ve
    tarayıcı kaç bulguyu neyle bastırdığını yazar — "neyin taranmadığı"
    gizli kalırsa kapı vardır ama korumaz.
    """

    def kur(self, td, muafiyet=None):
        os.makedirs(os.path.join(td, "tests"), exist_ok=True)
        with open(os.path.join(td, "tests", "fixture.js"), "w") as fh:
            fh.write("const u = { password: '%s' };\n" % FIXTURE_PAROLA)
        with open(os.path.join(td, "temiz.py"), "w") as fh:
            fh.write("x = 1\n")
        if muafiyet is not None:
            os.makedirs(os.path.join(td, ".agents"), exist_ok=True)
            with open(os.path.join(td, ".agents", "secret-allowlist.txt"),
                      "w", encoding="utf-8") as fh:
                fh.write(muafiyet)
        return td

    def test_muafiyet_yokken_yakalanir(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(kos(SCAN, self.kur(td))[0], 1)

    def test_gerekceli_muafiyet_bastirir(self):
        with tempfile.TemporaryDirectory() as td:
            self.kur(td, "tests/fixture.js  # yerel test fixture'ı, gerçek hesap yok\n")
            kod, cikti = kos(SCAN, td)
            self.assertEqual(kod, 0, cikti)
            self.assertIn("muafiyet", cikti.lower(),
                          "bastırılan bulgu sessizce kaybolmamalı")

    def test_gerekcesiz_muafiyet_reddedilir(self):
        # Gerekçesiz satır = sessiz susturma. Kapı bunu kabul edemez.
        with tempfile.TemporaryDirectory() as td:
            self.kur(td, "tests/fixture.js\n")
            kod, cikti = kos(SCAN, td)
            self.assertEqual(kod, 2, cikti)
            self.assertIn("gerekçe", cikti.lower())

    def test_muafiyet_kapsam_disini_korur(self):
        # Muafiyet yalnız yazdığı yolu kapsar; başka dosya hâlâ yakalanır.
        with tempfile.TemporaryDirectory() as td:
            self.kur(td, "tests/fixture.js  # fixture\n")
            with open(os.path.join(td, "gercek.py"), "w") as fh:
                fh.write(f'KEY = "{ORNEK_ANAHTAR}"\n')
            kod, cikti = kos(SCAN, td)
            self.assertEqual(kod, 1, "muaf olmayan secret hâlâ bloklamalı")
            self.assertIn("gercek.py", cikti)
            # Bastırılan bulgu GÖRÜNÜR kalır ama 'muaf' etiketiyle — sessiz
            # kaybolması, muafiyetin denetlenemez olması demekti.
            self.assertIn("muaf: ", cikti)
            self.assertNotIn("fixture.js:1  [Hardcoded parola]  →", cikti)


class CheckCitationsTest(unittest.TestCase):
    """Komut çıktısı da kaynaktır.

    4cast denetimi (2026-08-06): kanıtların çoğu `komut → sonuç` biçimindeydi
    (`gh api … → HTTP 403`, `git shortlog → semih 191`) ama araç yalnız URL ve
    dosya:satır tanıyordu → iyi kaynaklandırılmış rapor %89 kaynaksız çıktı.
    Yanlış sinyal, sinyalsizlikten kötüdür: aracı susturmaya iter.
    """

    def olc(self, govde):
        with tempfile.TemporaryDirectory() as td:
            yol = os.path.join(td, "r.md")
            with open(yol, "w", encoding="utf-8") as fh:
                fh.write("# Rapor\n\n## Bulgular\n\n" + govde + "\n")
            return kos(CITATIONS, yol)

    def test_komut_ciktisi_kaynak_sayilir(self):
        kod, cikti = self.olc(
            "Ana dalda koruma kurulamıyor; `gh api repos/x/y/branches/main/"
            "protection` → HTTP 403 döndü ve bu Free plan sınırıdır.")
        self.assertEqual(kod, 0, f"komut→sonuç kaynak sayılmadı:\n{cikti}")

    def test_ciplak_komut_adi_kaynak_sayilmaz(self):
        # Komutu ANMAK kanıt değildir; koşup sonucu göstermek kanıttır.
        kod, _c = self.olc(
            "Bu depoda kalite ölçümü için `bin/kalite.py` kullanılmalıdır "
            "ve ölçüm düzenli tekrarlanmalıdır diye düşünüyoruz.")
        self.assertEqual(kod, 1, "çıplak komut anması kaynak sayıldı")

    def test_yonetici_ozeti_iddia_sayilmaz(self):
        # Özet, altında kanıtlanmış bulguyu tekrar eder; kaynak orada durur.
        with tempfile.TemporaryDirectory() as td:
            yol = os.path.join(td, "r.md")
            with open(yol, "w", encoding="utf-8") as fh:
                fh.write("# Rapor\n\n## Yönetici özeti\n\n"
                         "Ürün sağlam ama süreç boruları delik; bulguların "
                         "hiçbiri mimari yeniden yazım gerektirmiyor.\n\n"
                         "## Bulgular\n\n"
                         "Deploy testlere bağlı değil "
                         "`.github/workflows/deploy.yml:16` satırında "
                         "tetikleyici doğrudan push olarak tanımlı.\n")
            self.assertEqual(kos(CITATIONS, yol)[0], 0,
                             "özet bölümü iddia sayıldı")

    def test_yorum_etiketi_kaynaksiz_sayilmaz(self):
        # Açıkça "bu çıkarım" demek, ölçümmüş gibi sunmanın tersidir.
        kod, _c = self.olc(
            "Devralma maliyetini belirleyen şey tek dosyada yoğunlaşan karar "
            "sayısıdır `[yorum]` — bu depoda ölçülmedi, denetçi çıkarımıdır.")
        self.assertEqual(kod, 0, "[yorum] etiketi kaynaksız sayıldı")

    def test_dosya_satir_hala_kaynak(self):
        kod, _c = self.olc(
            "Deploy testlere bağlı değil; `.github/workflows/deploy.yml:16` "
            "satırında tetikleyici doğrudan push olarak tanımlanmış durumda.")
        self.assertEqual(kod, 0)


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
