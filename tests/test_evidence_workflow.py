#!/usr/bin/env python3
"""Kanıt workflow'unun tetikleyici sözleşmesi.

2026-08-06 GitHub Actions kesintisi (githubstatus "Incident with Actions",
15:22:49Z): webhook teslimatı bozulunca push/pull_request hiç run üretmedi,
yalnız workflow_dispatch çalıştı. Kanıt üretiminin TEK yolu otomatik olay
olamaz — aksi hâlde kesinti boyunca hiçbir PR bağımsız makine kanıtı
üretemez ve merge kararı yerel çıktıya kalır.
"""
import os
import unittest

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(ROOT, ".github", "workflows", "evidence.yml")
VALIDATE = os.path.join(ROOT, "bin", "validate.py")


def oku(yol):
    with open(yol, encoding="utf-8") as fh:
        return fh.read()


def tetikleyiciler():
    d = yaml.safe_load(oku(WF))
    # PyYAML 'on:' anahtarını boolean True'ya çevirir (YAML 1.1 mirası).
    return d.get(True, d.get("on", {})) or {}


class EvidenceWorkflowTest(unittest.TestCase):
    def test_uc_tetikleyici_de_tanimli(self):
        on = tetikleyiciler()
        for t in ("pull_request", "push", "workflow_dispatch"):
            self.assertIn(t, on, f"evidence.yml '{t}' tetikleyicisini kaybetmiş")

    def test_elle_tetikleme_bekcisi_validate_icinde(self):
        # Bekçi silinirse tetikleyici bir sonraki şablon düzenlemesinde
        # sessizce kaybolur; bu test bekçinin kendisini kilitler.
        metin = oku(VALIDATE)
        self.assertIn("workflow_dispatch", metin,
                      "validate.py workflow_dispatch bekçisini kaybetmiş")

    def test_workflow_yaml_gecerli(self):
        d = yaml.safe_load(oku(WF))
        self.assertIn("jobs", d, "evidence.yml 'jobs' taşımıyor")

    def test_kanit_uretimi_ve_artifact_adimi_duruyor(self):
        metin = oku(WF)
        for parca in ("make_evidence.py", "upload-artifact", "validate.py"):
            self.assertIn(parca, metin, f"evidence.yml '{parca}' kaybetmiş")


if __name__ == "__main__":
    unittest.main()


class KapsamSiniriTest(unittest.TestCase):
    """Sistem neyi zorlamadığını açıkça söylemeli (2026-08-07).

    Kapsam sınırını gizleyen sistem, kapsamı dar olandan tehlikelidir:
    kullanıcı korunduğunu sanır. Ölçüm: 10 aşamanın 4'ünde hiç kapı yok.
    """

    BELGE = os.path.join(ROOT, "docs", "yasam-dongusu-kapsami.md")
    AGENTS = os.path.join(ROOT, "AGENTS.md")

    def test_kapsam_belgesi_var(self):
        self.assertTrue(os.path.isfile(self.BELGE),
                        "yaşam döngüsü kapsam haritası kaybolmuş")

    def test_agents_md_referans_veriyor(self):
        # Referans yoksa belge yetim kalır ve okunmaz
        self.assertIn("yasam-dongusu-kapsami", oku(self.AGENTS))

    def test_belge_kapsanmayan_asamalari_adiyla_sayiyor(self):
        # Genel "bazı eksikler var" cümlesi yeterli değil; hangi aşama?
        metin = oku(self.BELGE).lower()
        for asama in ("keşif", "tasarım", "operasyon", "ölçme"):
            self.assertIn(asama, metin, f"'{asama}' aşaması belgede yok")

    def test_belge_olculemez_alani_ayirt_ediyor(self):
        # Ölçülemeyeni kapıya bağlamaya çalışmak sahte kesinlik üretir
        metin = oku(self.BELGE).lower()
        self.assertIn("ölçülemez", metin)
        self.assertIn("sahte kesinlik", metin)
