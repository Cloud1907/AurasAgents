#!/usr/bin/env python3
"""Süitin ortam ön-koşulları — eksik bağımlılık GÖRÜNÜR olsun diye tek yerde.

Neden bu dosya var: `import yaml` doğrudan test modülünün tepesinde dururken
PyYAML'sız yorumlayıcıda modül import'ta çöker ve içindeki testler süiteden
YOK OLUR. Çıktı "3 hata" der; gerçek "34 test hiç koşmadı"dır. Kapsamın
daraldığını hiçbir satır söylemez — sayının kendisi yanıltır. 2026-08-07
ölçümü, aynı repo: python3.13 (PyYAML var) 220 test / OK, python3 (PyYAML yok)
186 test / 3 hata.

Doğru davranış iki katmanlıdır ve biri diğerinin yerine geçmez:
  1. Bağımlılık eksikse test ATLANIR — sayıda kalır, gerekçesi yazılır
     (`pyyaml_gerekir`). Kapsam artık sessizce daralamaz.
  2. `tests/test_ortam.py` eksikliği TEK ve yüksek sesli bir hataya çevirir.
     Atlama tek başına yetmez: exit 0 veren eksik süit CI'da "geçti" diye
     okunur, oysa "koşmadı" ile "geçti" aynı şey değildir.
"""
import unittest

try:
    import yaml
except ImportError:                 # kurulum eksiği — kural ihlali değil
    yaml = None

# Atlanan her testin yanında görünen kısa gerekçe.
PYYAML_SEBEP = ("PyYAML yok — bu test yaml okumadan anlamsız "
                "(python3 -m pip install pyyaml)")

# test_ortam'ın tek, yüksek sesli hatası: neyin kaybolduğunu ADIYLA söyler.
PYYAML_EKSIK = (
    "PyYAML kurulu değil — yaml'a bağlı testler ATLANDI, süit EKSİK koştu. "
    "Yukarıdaki 'skipped' sayısı koşmayan testlerdir; bu yorumlayıcıda "
    "'OK' TAM KAPSAM DEMEK DEĞİLDİR. Kurulum: python3 -m pip install pyyaml "
    "(ya da PyYAML'lı bir yorumlayıcı ile koş)."
)

#: Sınıf ya da metot üstünde: @pyyaml_gerekir
pyyaml_gerekir = unittest.skipUnless(yaml is not None, PYYAML_SEBEP)
