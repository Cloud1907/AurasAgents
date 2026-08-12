#!/usr/bin/env python3
"""Niyet ayrımı: istek OKUMA mı MUTASYON mu? (route.py'nin 2. aşaması)

Bulgu (bağımsız inceleme, 2026-08-12, iki turda doğrulandı): tek aşamalı
kelime puanlaması salt-okunur inceleme isteğini ALAN ADLARI yüzünden yazma
yetkili işe çeviriyordu — "router, kanıt kapıları ve hafıza sistemini
eleştirel incele" 3 kernel-work tetiğiyle code-change/approval oldu;
inceleme istemindeki "düzelt" implement-change'i zorunlu kıldı.

Tasarım: mutasyon POZİTİF işaretle doğrulanmadıkça yazma-niyetli kural
zorunlu kılınmaz, eşleşmesi öneriye (ek skill) düşer. Türkçe emir cümle
sonundadır: SON görülen niyet işareti kazanır ("incele ve düzelt" → yazma;
"düzeltilecekleri raporla" → okuma). Kök+ma/me olumsuz emirdir ("kod
yazma") ve işaret sayılmaz.

Asimetri bilinçli (soru turu kararıyla aynı, route.py): yanlış "okuma"
ucuzdur — router bloklamaz, ajan gerekirse skill'i öneriden yine yükler,
kapılar kanıtı yine ister. Yanlış "yazma" pahalıdır: approval gürültüsü
gerçek approval sinyalini değersizleştirir.

Regresyon bekçisi: tests/test_route.py (ölçülen iki vaka kalıcı vakadır).
"""
import re

OKU_ISARETLERI = ("incele", "araştır", "karşılaştır", "kıyasla",
                  "değerlendir", "denetle", "eleştir", "analiz", "rapor",
                  "gözden geçir", "keşfet", "öğren", "açıkla", "özetle",
                  "listele")
YAZ_ISARETLERI = ("yap", "uygula", "ekle", "yaz", "düzelt", "kodla",
                  "refactor", "taşı", "kaldır", "sil", "implement", "fix",
                  "oluştur", "geliştir", "değiştir", "güncelle", "tasarla",
                  "bağla", "çöz", "kurulum", "sisteme al", "onboard",
                  "bug", "hata", "çalışmıyor", "bozuk")
# route.tokenize ile aynı karakter kümesi — ayrışırlarsa konumlar kayar.
_TOKEN_RE = re.compile(r"[0-9a-zçğıöşü_.]+")
_OLUMSUZ_EK = ("ma", "me", "mayın", "meyin")


def _son_isaret(text, isaretler):
    """İşaret listesinin metindeki SON başlangıç konumu (yoksa -1)."""
    son = -1
    for im in isaretler:
        if " " in im:
            son = max(son, text.rfind(im))
    for m in _TOKEN_RE.finditer(text):
        tok = m.group()
        for im in isaretler:
            if " " in im or not tok.startswith(im):
                continue
            if tok[len(im):] in _OLUMSUZ_EK:
                continue  # olumsuz emir: "kod yazma", "dosya ekleme"
            son = max(son, m.start())
    return son


def mutasyon_niyeti(text):
    """Bu tur kod/dosya DEĞİŞTİRMEK mi istiyor? Son işaret karar verir."""
    yaz = _son_isaret(text, YAZ_ISARETLERI)
    return yaz >= 0 and yaz > _son_isaret(text, OKU_ISARETLERI)


def kural_niyeti(rule):
    """Kuralın niyet sınıfı. research okur, gerisi yazar sayılır; tablo
    `intent` alanıyla ezer (security-review: denetim okur, sınıfı approval
    kalır — bulgular kod değişikliğine komşudur). Alan bekçisi:
    bin/validate.py test_routing (geçersiz değer kesilir)."""
    return rule.get("intent") or (
        "read" if rule.get("task_class") == "research" else "write")


def niyet_kapisi(text, scored, extras):
    """Mutasyon doğrulanmadıysa yazma kurallarını zorunluluktan düşür.

    `scored`: route.py'nin (puan, özgüllük, kural, tetikler) listesi.
    Dönüş (scored, extras): okuma niyetinde okuma kuralları öne alınır;
    hiç okuma kuralı yoksa scored BOŞALIR (route fallback'e düşer, zorunlu
    skill üretilmez) ve yazma eşleşmeleri öneri olarak extras'a taşınır.
    """
    if mutasyon_niyeti(text):
        return scored, extras
    okunur = [s for s in scored if kural_niyeti(s[2]) == "read"]
    if okunur:
        return okunur + [s for s in scored
                         if kural_niyeti(s[2]) != "read"], extras
    for _s, _sp, rule, _h in scored:
        if rule["skill"] not in extras:
            extras.append(rule["skill"])
    return [], extras
