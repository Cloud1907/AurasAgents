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
        for rel in kd.MOTOR + kd.MOTOR_DIZIN:
            self.assertTrue(os.path.exists(os.path.join(ROOT, rel)),
                            f"listede ama repoda yok: {rel}")

    def test_kendi_araclarini_tasir(self):
        # Geri taşıma yolu bağlı projeye de gitmeli, yoksa orada kullanılamaz
        for rel in ("bin/kernel_dosyalari.py", "bin/auras_geri.py"):
            self.assertIn(rel, kd.MOTOR, f"{rel} motor listesinde yok")


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
