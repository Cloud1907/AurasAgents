#!/usr/bin/env python3
"""Kurulum kaynağının tazeliği — /auras eski motoru sessizce yayamaz.

2026-08-15 ölçümü: kanonik çalışma ağacı e3f1ec1'deydi, origin/main
2d42b90'daydı — yani bir commit geride. `auras-init.sh` dosyaları doğrudan
çalışma ağacından kopyaladığı için o gün koşulan her /auras hedef repoya ESKİ
motoru kurar ve `.kernel-manifest.json`'a "güncel" diye damgalardı. Kapı var,
koruma yok hâli budur: kullanıcı senkron olduğunu sanır.

Bu testler sözleşmeyi kilitler — kurulum önce kaynağı ileri sarar; güvenle
saramıyorsa (yerel commit / kirli ağaç) DURUR, sessizce eski sürümü yaymaz.
"""
import os
import subprocess
import sys
import unittest
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bin"))
import kernel_dosyalari as kd  # noqa: E402


def git(kok, *arg):
    subprocess.run(["git", "-C", kok, *arg], check=True,
                   capture_output=True, text=True)


def yaz(kok, ad, icerik):
    with open(os.path.join(kok, ad), "w", encoding="utf-8") as fh:
        fh.write(icerik)


def depo_kur(kok):
    """İçinde tek commit olan, kimliği ayarlı bir git deposu."""
    git(kok, "init", "-b", "main", "-q")
    git(kok, "config", "user.email", "test@auras.local")
    git(kok, "config", "user.name", "auras test")
    yaz(kok, "motor.py", "surum = 1\n")
    git(kok, "add", "-A")
    git(kok, "commit", "-qm", "ilk")


def sha(kok, ref="HEAD"):
    p = subprocess.run(["git", "-C", kok, "rev-parse", ref],
                       capture_output=True, text=True, check=True)
    return p.stdout.strip()


class KaynakTazeligiTest(unittest.TestCase):
    """kaynak_tazele(): kurulumdan ÖNCE kaynak sürümünü kanıtlar."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.uzak = os.path.join(self.tmp.name, "uzak")
        self.kaynak = os.path.join(self.tmp.name, "kaynak")
        os.makedirs(self.uzak)
        depo_kur(self.uzak)
        subprocess.run(["git", "clone", "-q", self.uzak, self.kaynak],
                       check=True, capture_output=True, text=True)
        git(self.kaynak, "config", "user.email", "test@auras.local")
        git(self.kaynak, "config", "user.name", "auras test")
        self.addCleanup(self.tmp.cleanup)

    def uzakta_commit(self):
        yaz(self.uzak, "motor.py", "surum = 2\n")
        git(self.uzak, "add", "-A")
        git(self.uzak, "commit", "-qm", "yeni motor")

    def test_guncel_kaynak_gecer(self):
        durum, mesaj = kd.kaynak_tazele(self.kaynak)
        self.assertEqual(durum, "guncel", mesaj)

    def test_geride_kaynak_ileri_sarilir(self):
        # Asıl istenen davranış: /auras SON sürüme göre hareket etsin.
        self.uzakta_commit()
        durum, mesaj = kd.kaynak_tazele(self.kaynak)
        self.assertEqual(durum, "ilerletildi", mesaj)
        self.assertEqual(sha(self.kaynak), sha(self.uzak),
                         "kaynak uzak sürüme taşınmadı — kopyalanacak içerik eski")

    def test_yerel_commit_varsa_engel(self):
        # Ayrışmış geçmişte ff yapılamaz; sessizce eski/karışık sürüm yaymak
        # yerine DURULUR — kararı insan verir.
        self.uzakta_commit()
        yaz(self.kaynak, "yerel.py", "x = 1\n")
        git(self.kaynak, "add", "-A")
        git(self.kaynak, "commit", "-qm", "yerel is")
        durum, mesaj = kd.kaynak_tazele(self.kaynak)
        self.assertEqual(durum, "engel", mesaj)
        self.assertIn("yerel commit", mesaj)

    def test_kirli_agac_engel(self):
        self.uzakta_commit()
        yaz(self.kaynak, "motor.py", "surum = 'yarim is'\n")
        durum, mesaj = kd.kaynak_tazele(self.kaynak)
        self.assertEqual(durum, "engel", mesaj)
        self.assertIn("kirli", mesaj)

    def test_izlenmeyen_dosya_ileri_sarmayi_engellemez(self):
        # Scratch dosyası kurulumu durdurmamalı — ff'yi de bozmuyor.
        self.uzakta_commit()
        yaz(self.kaynak, "not.txt", "gecici\n")
        durum, mesaj = kd.kaynak_tazele(self.kaynak)
        self.assertEqual(durum, "ilerletildi", mesaj)

    def test_upstream_yoksa_dogrulanamadi(self):
        # "Bilinmiyor" ≠ "temiz": ayrı sınıf olarak GÖRÜNÜR kalır.
        yalniz = os.path.join(self.tmp.name, "yalniz")
        os.makedirs(yalniz)
        depo_kur(yalniz)
        durum, _ = kd.kaynak_tazele(yalniz)
        self.assertEqual(durum, "dogrulanamadi")

    def test_git_disi_dizin_dogrulanamadi(self):
        duz = os.path.join(self.tmp.name, "duz")
        os.makedirs(duz)
        durum, _ = kd.kaynak_tazele(duz)
        self.assertEqual(durum, "dogrulanamadi")

    def test_kirli_agac_guncel_kaynakta_da_uyarir(self):
        # Kaynak son sürümde ama ağaç kirliyse kurulan içerik hiçbir commit'e
        # ait değildir — bağlı repolara İNCELENMEMİŞ kernel işi gider.
        # Bloklamaz (kernel burada geliştirilir) ama "guncel" deyip susamaz.
        yaz(self.kaynak, "motor.py", "surum = 'yarim is'\n")
        durum, mesaj = kd.kaynak_tazele(self.kaynak)
        self.assertEqual(durum, "guncel", mesaj)
        self.assertIn("kirli", mesaj)

    def test_ilerideki_kaynak_uyarir(self):
        # Push edilmemiş kernel commit'i = bağlı repolara İNCELENMEMİŞ içerik.
        # Bloklamaz (kernel burada geliştiriliyor) ama sessiz de kalmaz.
        yaz(self.kaynak, "yerel.py", "x = 1\n")
        git(self.kaynak, "add", "-A")
        git(self.kaynak, "commit", "-qm", "henuz push edilmedi")
        durum, mesaj = kd.kaynak_tazele(self.kaynak)
        self.assertEqual(durum, "guncel", mesaj)
        self.assertIn("uyarı", mesaj)


if __name__ == "__main__":
    unittest.main()
