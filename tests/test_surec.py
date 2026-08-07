#!/usr/bin/env python3
"""Süreç katmanı — başlatılan ağaç hiçbir çıkış yolunda yetim kalmamalı.

Bu testler bir kaynak sızıntısını değil, bir KAPI ARIZASINI kovalar: sızan
`codex exec` süreci aynı hesabın oturumunu meşgul eder → sonraki inceleme
yavaşlar → o da zaman aşımına uğrayıp bir süreç daha sızdırır. Her zaman
aşımı bir sonrakini daha olası kılar.
"""
import importlib.util
import os
import subprocess
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "surec", os.path.join(ROOT, "bin", "surec.py"))
surec = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(surec)


def _yasiyor(pid):
    """PID hâlâ canlı mı (sinyal göndermeden yoklar)."""
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _torun_komutu(pid_dosya):
    """Kabuk bir TORUN doğurur, PID'ini yazar, sonra kendi bekler —
    codex-review.sh → ask-codex.sh → codex zincirinin aynı şekli.

    Torunun çıktısı bilinçli olarak /dev/null'a gider: boruyu açık tutan bir
    torun `communicate()`'i süresiz bloklar (ayrı ve daha ağır bir kusur);
    testin kendisini asmamak için burada tetiklenmiyor.
    """
    return (f"sleep 120 >/dev/null 2>&1 & echo $! > {pid_dosya}; "
            "sleep 120 >/dev/null 2>&1")


class SurecSizintisiTest(unittest.TestCase):
    """P0 · Zaman aşımı süreç ağacını sızdırıyordu (2026-08-07 ölçümü).

    Gözlem: `codex-review.sh 14 --dry-run` ağacı, onu başlatan süreç
    öldükten sonra **2 saat 43 dakika** yaşadı (PPID 1, altında `codex exec`).
    Aynı iş normalde ~150s. Sebep: `subprocess.run(timeout=)` yalnız Python'un
    BEKLEMESİNİ sınırlar, başlattığı AĞACI öldürmez.
    """

    def test_zaman_asimi_torun_sureci_de_oldurur(self):
        with tempfile.TemporaryDirectory() as td:
            pid_dosya = os.path.join(td, "torun.pid")
            kod, _o, _e = surec.kos("bash", "-c", _torun_komutu(pid_dosya),
                                    timeout=2)
            self.assertEqual(kod, 1, "zaman aşımı hata kodu döndürmeli")
            self._torun_olmus_mu(pid_dosya, "zaman aşımından")

    def _torun_olmus_mu(self, pid_dosya, ne_sonrasi):
        with open(pid_dosya, encoding="utf-8") as fh:
            torun = int(fh.read().strip())
        time.sleep(0.5)
        yasiyor = _yasiyor(torun)
        if yasiyor:  # test kendisi sızdırmasın
            try:
                os.kill(torun, 9)
            except OSError:
                pass
        self.assertFalse(
            yasiyor,
            f"torun süreç {torun} {ne_sonrasi} sonra hâlâ yaşıyor — sızan "
            "codex süreci sonraki incelemeyi yavaşlatır")


class KesintiSizintisiTest(SurecSizintisiTest):
    """P1 · Ctrl-C ağacı yetim bırakıyordu (kapının PR #17'de bulduğu açık).

    `KeyboardInterrupt` ne `OSError` ne `subprocess.SubprocessError` alt
    sınıfıdır — zaman aşımını yakalayan blok onu görmez. Kullanıcı incelemeyi
    yarıda kesince Python çıkar, süreç GRUBU yaşamaya devam eder. Gözlenen
    2s43dk'lık yetim büyük olasılıkla tam böyle doğdu: zaman aşımı değil,
    kesilen bir üst süreç.
    """

    def test_zaman_asimi_torun_sureci_de_oldurur(self):
        pass  # üst sınıfın vakası orada koşuyor; burada kesinti sınanıyor

    def test_kesinti_torun_sureci_de_oldurur(self):
        with tempfile.TemporaryDirectory() as td:
            pid_dosya = os.path.join(td, "torun.pid")
            gercek = subprocess.Popen.communicate

            def kesintili(self_p, *a, **kw):
                if getattr(self_p, "_kesildi", False):
                    return gercek(self_p, *a, **kw)
                self_p._kesildi = True
                # Torun DOĞMADAN kesmek yarış koşuludur: sızıntı olmadığı
                # için değil, sızacak süreç henüz yokken test yeşil görünür.
                for _ in range(200):
                    if os.path.exists(pid_dosya):
                        with open(pid_dosya, encoding="utf-8") as fh:
                            if fh.read().strip():
                                break
                    time.sleep(0.05)
                raise KeyboardInterrupt

            subprocess.Popen.communicate = kesintili
            try:
                with self.assertRaises(KeyboardInterrupt):
                    surec.kos("bash", "-c", _torun_komutu(pid_dosya),
                              timeout=30)
            finally:
                subprocess.Popen.communicate = gercek
            self._torun_olmus_mu(pid_dosya, "Ctrl-C'den")


class NormalDonusTest(SurecSizintisiTest):
    """P1 · Normal dönüşte grup temizlenmiyordu (kapının 3. bulgusu).

    `agaci_oldur` yalnız istisna yolundaydı. Arka plana atılmış, stdio'su
    yönlendirilmiş bir torun boruyu tutmaz — kabuk çıkar, `communicate()`
    sorunsuz döner, `kos` başarı bildirir ve torun yaşamaya devam eder.
    Zaman aşımı da Ctrl-C de olmadan sızıntı: PR'ın tezindeki son delik.
    """

    def test_zaman_asimi_torun_sureci_de_oldurur(self):
        pass  # üst sınıfta koşuyor; burada normal dönüş sınanıyor

    def test_normal_donuste_torun_kalmaz(self):
        with tempfile.TemporaryDirectory() as td:
            pid_dosya = os.path.join(td, "torun.pid")
            # Kabuk torunu doğurup HEMEN çıkar — zaman aşımı yok, hata yok.
            komut = (f"sleep 120 >/dev/null 2>&1 & echo $! > {pid_dosya}; "
                     "exit 0")
            kod, _o, _e = surec.kos("bash", "-c", komut, timeout=30)
            self.assertEqual(kod, 0, "normal çıkış beklenir")
            self._torun_olmus_mu(pid_dosya, "normal dönüşten")


class TuzakTest(unittest.TestCase):
    """P1 · SIGKILL kabuk `EXIT` tuzağını koşturmuyordu (kapının 4. bulgusu).

    `codex-review.sh` prompt'u `mktemp` ile yazar ve
    `trap 'rm -f "$PROMPT_FILE"' EXIT` ile siler. SIGKILL yakalanamaz —
    zaman aşımında tuzak hiç koşmaz, geçici dosya /tmp'de kalır.

    Çözüm önce SIGTERM (tuzak koşsun), kısa bekleme, sonra hâlâ yaşayana
    SIGKILL. Ölüm garantisi bozulmaz; temizlik şansı verilir.
    """

    def test_zaman_asiminda_exit_tuzagi_kosar(self):
        with tempfile.TemporaryDirectory() as td:
            iz = os.path.join(td, "tuzak-kosti")
            # codex-review.sh'nin şekli: EXIT tuzağı + uzun iş
            komut = f"trap 'touch {iz}' EXIT; sleep 120 >/dev/null 2>&1"
            kod, _o, _e = surec.kos("bash", "-c", komut, timeout=2)
            self.assertEqual(kod, 1, "zaman aşımı hata kodu döndürmeli")
            time.sleep(0.5)
            self.assertTrue(
                os.path.exists(iz),
                "EXIT tuzağı koşmadı — SIGKILL yakalanamaz, kabuk geçici "
                "dosyalarını temizleyemez (codex-review.sh mktemp sızdırır)")


class IncelemeButcesiTest(unittest.TestCase):
    """P1 · İnceleme bütçesi `gh` çağrılarıyla aynı sabitti — `gh pr view`
    (saniyeler) ile Codex incelemesi (dakikalar) tek sayıya bağlıydı."""

    def test_inceleme_butcesi_ayri_ve_acik(self):
        self.assertTrue(hasattr(surec, "INCELEME_BUTCESI"))
        self.assertGreater(surec.INCELEME_BUTCESI, 600,
                           "ölçüm: temiz makinede ~150s, çekişme altında "
                           "600s'i aşıyor — bütçe 600'ün üstünde olmalı")

    def test_butce_disaridan_ayarlanabilir(self):
        with open(os.path.join(ROOT, "bin", "surec.py"),
                  encoding="utf-8") as fh:
            kaynak = fh.read()
        self.assertIn("INCELE_BUTCE", kaynak,
                      "bütçe ortam değişkeniyle ayarlanamıyor — zaman "
                      "aşımında kullanıcının elinde seçenek kalmaz")

    def test_zaman_asimi_notu_eyleme_donuk(self):
        metin = surec.zaman_asimi_notu(900)
        self.assertIn("900", metin, "bütçe sayısı görünmeli")
        self.assertIn("INCELE_BUTCE", metin,
                      "bütçeyi yükseltme yolu gösterilmeli")
        self.assertIn("etime", metin,
                      "süreç YAŞINA bakmalı — eşzamanlı meşru inceleme "
                      "öldürülmesin")


if __name__ == "__main__":
    unittest.main()
