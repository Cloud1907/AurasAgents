#!/usr/bin/env python3
"""Süreç çalıştırma katmanı — alt süreç ağacını asla yetim bırakmaz.

Neden ayrı modül: `incele.py` KARAR verir (risk sınıfı, bulgu, merge);
burası SÜREÇ yönetir. İkisi 2026-08-07'de aynı dosyadaydı ve dosya kalite
ratchet'inin 400 satır sınırına dayandı — sınır, ayrılması gereken iki
sorumluluğu gösteriyordu.

Buradaki tek kural: **başlatılan ağaç, çıkış yolu ne olursa olsun ölür.**
Ölçüm (2026-08-07): `codex-review.sh` ağacı, onu başlatan süreç öldükten
sonra 2 saat 43 dakika yaşamaya devam etti (PPID 1, altında `codex exec`);
aynı iş normalde ~150s sürüyor. Sızan süreç aynı hesabın oturumunu meşgul
ettiği için sonraki inceleme yavaşlar → o da zaman aşımına uğrayıp bir
süreç daha sızdırır. Kontrollü ölçüm, aynı dondurulmuş diff:
    yetim canlı: 155.8s        yetim ölü: 98.5s / 45.5s / 54.0s
"""
import os
import signal
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# İnceleme bütçesi `gh` çağrılarınınkinden AYRIDIR (önce ikisi de `kos`'un
# genel varsayılanına bağlıydı; birini ayarlamak diğerini sessizce değiştirirdi).
# Ölçüm: 4.4KB→147s, 9.0KB→156s — boyut baskın değil, ~140s sabit taban var.
# Bu yüzden diff boyutuna göre ÖLÇEKLENMİYOR: ölçeklenecek değişken sürücü değil.
INCELEME_BUTCESI = int(os.environ.get("INCELE_BUTCE", "900"))


def agaci_oldur(p):
    """Süreç GRUBUNU öldürür. `p.kill()` yalnız doğrudan çocuğu (bash) alır;
    altındaki ask-codex.sh ve `codex exec` yaşar ve PPID 1'e düşer."""
    try:
        os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    except OSError:
        p.kill()
    try:
        p.communicate(timeout=10)
    except (OSError, subprocess.SubprocessError):
        pass


def kos(*arg, girdi=None, timeout=600):
    """Alt süreci KENDİ oturumunda başlatır; her çıkış yolunda ağacı öldürür.

    `subprocess.run(timeout=)` yalnız beklemeyi sınırlar, ağacı öldürmez.
    `KeyboardInterrupt` ise ne OSError ne SubprocessError'dır — zaman aşımını
    yakalayan blok onu görmez, Ctrl-C aynı sızıntıyı üretirdi. Bu yüzden
    `BaseException`. Gerekçe ve ölçüm: tests/test_surec.py.
    """
    try:
        p = subprocess.Popen(
            arg, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.PIPE if girdi is not None else None,
            text=True, cwd=ROOT, start_new_session=True)
    except OSError as e:
        return 1, "", str(e)
    try:
        out, err = p.communicate(girdi, timeout=timeout)
        return p.returncode, out, err
    except BaseException as e:  # Ctrl-C/SystemExit dahil: ağacı ASLA bırakma
        agaci_oldur(p)
        if isinstance(e, (OSError, subprocess.SubprocessError)):
            return 1, "", str(e)
        raise


def zaman_asimi_notu(butce):
    """Zaman aşımında kullanıcının önüne EYLEM koyar — önünde yol olmayan
    kapı `gh pr merge` ile atlanır, kural belgede kalır sistemde kalmaz."""
    return (
        f"İnceleme {butce}s bütçesinde bitmedi. Karar ENGEL — 'okunamadı' "
        "'temiz' demek değildir. Sırayla dene:\n"
        "1. Asılı süreç: `ps -eo etime,pid,command | grep 'codex exec'` — "
        "YAŞI bu incelemeden eskiyse yetimdir, öldür (eşzamanlı meşru "
        "incelemeyi öldürme). Sızan süreç sonrakini yavaşlatır: 155.8s→45.5s.\n"
        f"2. Bütçeyi yükseltip tekrar koş: "
        f"`INCELE_BUTCE={butce * 2} python3 bin/incele.py <pr>`\n"
        "3. PR'ı böl — tek amaçlı küçük diff hem hızlı hem doğru incelenir "
        "(AGENTS.md: ilgisiz işleri tek PR'da toplama).")
