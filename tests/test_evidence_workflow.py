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
