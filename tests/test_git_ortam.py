#!/usr/bin/env python3
"""Miras git ortamı geçici depoları gerçek depoya çeviremez (bin/git_ortam.py).

Olay 2026-10-15, OICommand: worktree'den push → kanca validate.py'yi GIT_DIR
mirasıyla koştu → testlerin geçici depo `git init` / `git config user.*`
çağrıları gerçek depoya gitti: paylaşılan .git/config'e `core.bare = true` ve
`[user] t <t@t.t>` yazıldı, 17 test 128 ile düştü.

DİKKAT: buradaki her git çağrısı ortamını AÇIKÇA alır. validate.py süiti
kendi yemine yönlendirilmiş ortamda koşar; çıplak os.environ'la yapılan bir
çağrı o yemi değiştirir ve kapıyı (haklı olarak) kırmızıya çevirir.
"""
import ast
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bin"))
from git_ortam import (YEREL_DEGISKENLER, temiz_ortam, yem_depo,  # noqa: E402
                       yemde_kos)

# Olayda gerçek depoya yazan iki modül: biri `git config user.*` (→ [user] t),
# ikisi de geçici dizinde `git init` (→ core.bare = true).
TEMSILI_MODULLER = ("test_kernel_dosyalari", "test_skill_validators")


def git(ortam, *arg):
    return subprocess.run(["git", *arg], capture_output=True, text=True,
                          env=ortam)


class TemizOrtamTest(unittest.TestCase):
    def test_gitin_yerel_degiskenlerinin_hepsini_soker(self):
        """git yeni bir yönlendirme değişkeni eklerse liste eskimiş demektir."""
        p = git(temiz_ortam(), "rev-parse", "--local-env-vars")
        self.assertEqual(p.returncode, 0, p.stderr)
        eksik = set(p.stdout.split()) - set(YEREL_DEGISKENLER)
        self.assertFalse(eksik, f"YEREL_DEGISKENLER eksik: {sorted(eksik)}")

    def test_yalniz_yonlendirmeyi_soker(self):
        taban = {"GIT_DIR": "/x", "GIT_INDEX_FILE": "/x/i", "PATH": "/bin",
                 "GIT_AUTHOR_NAME": "a"}
        ortam = temiz_ortam(taban)
        self.assertEqual(ortam, {"PATH": "/bin", "GIT_AUTHOR_NAME": "a"})
        self.assertIn("GIT_DIR", taban, "taban yerinde değiştirilmemeli")


class YemDepoTest(unittest.TestCase):
    def gecici_depo(self, td, ortam):
        """Olaydaki test kurulumunun aynısı: init + kimlik + add."""
        with open(os.path.join(td, "a.py"), "w") as fh:
            fh.write("x = 1\n")
        for arg in (["init", "-q", "-b", "main", td],
                    ["-C", td, "config", "user.name", "t"],
                    ["-C", td, "config", "user.email", "t@t.t"],
                    ["-C", td, "add", "-A"]):
            git(ortam, *arg)

    def test_miras_ortam_yemi_bozar(self):
        """Negatif kontrol: yem, temizlenmemiş çağrıyı GÖRÜR.

        Görmeseydi aşağıdaki yeşiller hiçbir şey ölçmezdi. Bu aynı zamanda
        olayın mekanizmasıdır — `git -C <tmp>` GIT_DIR'e yenilir.
        """
        with yem_depo() as yem, tempfile.TemporaryDirectory() as td:
            self.gecici_depo(td, yem.ortam)
        self.assertIn("config", yem.degisen,
                      "miras GIT_DIR'le git init/config yemin config'ine "
                      "yazmalıydı — yem sızıntıyı göremiyor")

    def test_temiz_ortamla_gecici_depo_yeme_dokunmaz(self):
        with yem_depo() as yem, tempfile.TemporaryDirectory() as td:
            self.gecici_depo(td, temiz_ortam(yem.ortam))
            ad = git(temiz_ortam(), "-C", td, "config", "user.name").stdout
        self.assertEqual(yem.degisen, [])
        self.assertEqual(ad.strip(), "t", "kimlik geçici depoya yazılmalıydı")

    def test_olaydaki_moduller_miras_ortamda_yesil_ve_zararsiz(self):
        """Olayın birebir tekrarı, temsili modüllerle: süit miras GIT_DIR'le
        koşar; yeşil kalmalı ve yeme dokunmamalı."""
        with yem_depo() as yem:
            p = subprocess.run(
                [sys.executable, "-m", "unittest", "-q", *TEMSILI_MODULLER],
                cwd=os.path.join(ROOT, "tests"), env=yem.ortam,
                capture_output=True, text=True, timeout=300)
        self.assertEqual(p.returncode, 0,
                         f"miras GIT_DIR altında düştü:\n{p.stderr[-1500:]}")
        self.assertEqual(yem.degisen, [],
                         "temsili modüller miras GIT_DIR'in deposuna yazdı")

    def test_git_dizinindeki_soket_izi_bozmaz(self):
        """core.fsmonitor açık kullanıcıda .git'te fsmonitor--daemon.ipc soketi
        olur; açılamaz (Errno 102). İz onu atlamazsa her validate.py — yani her
        push — nedeni görünmeyen bir traceback'le düşer (inceleme bulgusu P2)."""
        with yem_depo() as yem:
            s = socket.socket(socket.AF_UNIX)
            self.addCleanup(s.close)
            onceki = os.getcwd()
            try:            # göreli bağ: AF_UNIX yol sınırı (~104) geçici
                os.chdir(yem.git_dizini)   # dizinin mutlak yolunda aşılabilir
                s.bind("fsmonitor--daemon.ipc")
            finally:
                os.chdir(onceki)
        self.assertEqual(yem.degisen, [])

    def test_yem_kurulumu_kullanicinin_git_ayarindan_yalitik(self):
        """commit.gpgsign=true olan makinede yemin commit'i imza ister: imza
        aracı yoksa 128, varsa her push'ta istem. Yem kullanıcının global
        ayarına bağlı olamaz."""
        with tempfile.TemporaryDirectory() as td:
            ayar = os.path.join(td, "gitconfig")
            with open(ayar, "w") as fh:
                fh.write("[commit]\n\tgpgsign = true\n[gpg]\n\tprogram = false\n")
            with mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": ayar}):
                with yem_depo() as yem:
                    pass
        self.assertEqual(yem.degisen, [])


class YemdeKosTest(unittest.TestCase):
    def test_sizan_komutu_adiyla_yakalar(self):
        with tempfile.TemporaryDirectory() as td:
            p, degisen = yemde_kos(["git", "init", "-q", td], td)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("config", degisen)

    def test_sizmayan_komut_temiz_doner(self):
        p, degisen = yemde_kos([sys.executable, "-c", "print('ok')"], ROOT)
        self.assertEqual((p.returncode, p.stdout.strip(), degisen),
                         (0, "ok", []))

    def test_validate_birim_suitini_yemde_kosar(self):
        """Bekçinin kablosu: validate.py süiti yemde koşmazsa güvenlik ağı
        SESSİZCE kalkar — her şey yeşil kalır (inceleme bulgusu P3)."""
        yol = os.path.join(ROOT, "bin", "validate.py")
        agac = ast.parse(open(yol, encoding="utf-8").read())
        cagiranlar = []
        for dugum in ast.walk(agac):
            if not isinstance(dugum, ast.Call):
                continue
            for arg in dugum.args:
                sabitler = {e.value for e in getattr(arg, "elts", [])
                            if isinstance(e, ast.Constant)}
                if {"unittest", "discover"} <= sabitler:
                    cagiranlar.append(ast.unparse(dugum.func))
        self.assertTrue(cagiranlar, "validate.py birim süitini koşmuyor")
        self.assertEqual(set(cagiranlar), {"git_ortam.yemde_kos"},
                         "validate.py süiti yem DIŞINDA koşuyor — miras git "
                         "ortamı sızıntısı artık yakalanmaz")


if __name__ == "__main__":
    unittest.main()
