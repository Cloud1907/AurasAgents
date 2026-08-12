#!/usr/bin/env python3
"""Niyet ayrımı: istek OKUMA mı MUTASYON mu? (route.py'nin 2. aşaması)

Bulgu (bağımsız inceleme, 2026-08-12, iki turda doğrulandı): tek aşamalı
kelime puanlaması salt-okunur inceleme isteğini ALAN ADLARI yüzünden yazma
yetkili işe çeviriyordu — "router, kanıt kapıları ve hafıza sistemini
eleştirel incele" 3 kernel-work tetiğiyle code-change/approval oldu;
inceleme istemindeki "düzelt" implement-change'i zorunlu kıldı.

Tasarım (incele.py P1 turu sonrası, PR #43): karar KONUMA değil BİÇİME
bakar. Pozitif yazma fiili görülen tur mutasyondur ("endpoint ekle ve
yaptığını raporla" → yazma). Pozitiflik ek morfolojisiyle ayrılır:
-ma/-me ile süren biçim olumsuz emir ya da fiil-isimdir ("kod yazma",
"düzeltmeden", "düzeltmemiz") ve işaret sayılmaz; -malı/-meli ve
-mak/-mek pozitiftir; -ıl/-il edilgendir ("düzeltilmesi gerekenleri
listele" iş emri değildir). Şikâyet/kurulum işaretleri (bug, çalışmıyor…)
zayıftır: yalnız okuma işareti YOKSA mutasyon sayılır.

Asimetri bilinçli (soru turu kararıyla aynı, route.py): yanlış "okuma"
ucuzdur — router bloklamaz, ajan gerekirse skill'i öneriden yine yükler,
kapılar kanıtı yine ister. Yanlış "yazma" pahalıdır: approval gürültüsü
gerçek approval sinyalini değersizleştirir.

Regresyon bekçisi: tests/test_route.py (ölçülen vakalar kalıcı vakadır).
"""
import re

OKU_ISARETLERI = ("incele", "araştır", "karşılaştır", "kıyasla",
                  "değerlendir", "denetle", "eleştir", "analiz", "rapor",
                  "gözden geçir", "keşfet", "öğren", "açıkla", "özetle",
                  "listele")
# Pozitif biçimde görülmesi tek başına mutasyon sayılan yazma fiilleri.
# routing.yml yazma kurallarının fiil tetikleriyle uyumlu tutulur
# (incele.py P1: "güzelleştir" tabloda vardı, burada yoktu).
YAZ_FIILLERI = ("yap", "uygula", "ekle", "yaz", "düzelt", "kodla",
                "refactor", "taşı", "kaldır", "sil", "implement", "fix",
                "oluştur", "geliştir", "değiştir", "güncelle", "tasarla",
                "güzelleştir", "bağla", "çöz")
# Zayıf işaretler: şikâyet/kurulum adları. Fiil çekimi taşımazlar; okuma
# işareti de varsa okuma kazanır ("bu bug'ın nedenini araştır").
ZAYIF_ISARETLER = ("bug", "hata", "çalışmıyor", "bozuk", "kurulum",
                   "onboard", "sisteme al")
# route.tokenize ile aynı karakter kümesi — ayrışırlarsa eşleşme kayar.
_TOKEN_RE = re.compile(r"[0-9a-zçğıöşü_.]+")
_POZITIF_DEVAM = ("malı", "meli", "mak", "mek")   # yükümlülük / mastar
_OLUMSUZ_DEVAM = ("ma", "me")                     # olumsuz emir / fiil-isim
_EDILGEN_DEVAM = ("ıl", "il", "ul", "ül")


def _pozitif_bicim(kalan):
    """Kök sonrası ek, işareti POZİTİF emir/istek olarak mı bırakıyor?

    "" (yalın emir "ekle"), -malı/-meli ("eklemeliyiz"), -mak/-mek
    ("eklemek istiyorum") pozitiftir. -ma/-me ile süren her biçim olumsuz
    emir ya da fiil-isimdir ("yazma", "yazmayın", "düzeltmeden",
    "düzeltmemiz") — işaret değildir. -ıl/-il/-ul/-ül edilgendir
    ("düzeltilecekleri raporla"). Kalan çekimler ("ekleyelim",
    "ekliyoruz", "ekleyin") pozitiftir.
    """
    if kalan.startswith(_POZITIF_DEVAM):
        return True
    if kalan.startswith(_OLUMSUZ_DEVAM) or kalan.startswith(_EDILGEN_DEVAM):
        return False
    return True


def _pozitif_var(text, isaretler):
    """İşaretlerden biri metinde pozitif biçimde geçiyor mu?"""
    for im in isaretler:
        if " " in im and im in text:
            return True
    for m in _TOKEN_RE.finditer(text):
        tok = m.group()
        for im in isaretler:
            if (" " not in im and tok.startswith(im)
                    and _pozitif_bicim(tok[len(im):])):
                return True
    return False


def mutasyon_niyeti(text):
    """Bu tur kod/dosya DEĞİŞTİRMEK mi istiyor? Biçim karar verir."""
    if _pozitif_var(text, YAZ_FIILLERI):
        return True
    return (_pozitif_var(text, ZAYIF_ISARETLER)
            and not _pozitif_var(text, OKU_ISARETLERI))


def kural_niyeti(rule):
    """Kuralın niyet sınıfı. research okur, gerisi yazar sayılır; tablo
    `intent` alanıyla ezer (security-review: denetim okur). Alan bekçisi:
    bin/validate.py test_routing (geçersiz değer kesilir)."""
    return rule.get("intent") or (
        "read" if rule.get("task_class") == "research" else "write")


def _okuma_sinifi(rule):
    """Okuma niyetinde seçilen kural salt-okunur profile iner.

    incele.py P1 (PR #43): intent:read kural code-change sınıfını
    koruyunca salt-okunur denetim yazma profili açıyordu. Skill
    zorunluluğu ve `risk` etiketi kuraldan gelir; yalnız profil iner.
    Mutasyon turunda kuralın kendi sınıfı geçerlidir (kopya cfg'yi bozmaz).
    """
    if rule.get("task_class") == "research":
        return rule
    return dict(rule, task_class="research")


def niyet_kapisi(text, scored, extras):
    """Mutasyon doğrulanmadıysa yazma kurallarını zorunluluktan düşür.

    `scored`: route.py'nin (puan, özgüllük, kural, tetikler) listesi.
    Dönüş (scored, extras): okuma niyetinde okuma kuralları öne alınır ve
    salt-okunur profile indirilir; hiç okuma kuralı yoksa scored BOŞALIR
    (route fallback'e düşer, zorunlu skill üretilmez) ve yazma
    eşleşmeleri öneri olarak extras'a taşınır.
    """
    if mutasyon_niyeti(text):
        return scored, extras
    okunur = [(p, sp, _okuma_sinifi(r), h) for p, sp, r, h in scored
              if kural_niyeti(r) == "read"]
    if okunur:
        return okunur + [s for s in scored
                         if kural_niyeti(s[2]) != "read"], extras
    for _p, _sp, rule, _h in scored:
        if rule["skill"] not in extras:
            extras.append(rule["skill"])
    return [], extras
