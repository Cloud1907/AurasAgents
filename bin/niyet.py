#!/usr/bin/env python3
"""Niyet ayrımı: istek OKUMA mı MUTASYON mu? (route.py'nin 2. aşaması)

Bulgu (bağımsız inceleme, 2026-08-12, iki turda doğrulandı): tek aşamalı
kelime puanlaması salt-okunur inceleme isteğini ALAN ADLARI yüzünden yazma
yetkili işe çeviriyordu — "router, kanıt kapıları ve hafıza sistemini
eleştirel incele" 3 kernel-work tetiğiyle code-change/approval oldu;
inceleme istemindeki "düzelt" implement-change'i zorunlu kıldı.

Tasarım (incele.py iki P1 turu sonrası, PR #43): karar KONUMA değil
BİÇİME bakar ve ek analizi KARA-liste değil BEYAZ-listedir — fiil kökü
ancak bilinen POZİTİF emir/istek ekiyle sürüyorsa işaret sayılır. Böylece
isim gövdeleri ("yapısını" ≠ yap), olumsuz emir ("kod yazma"), edilgen
("eklenmesi", "düzeltilmesi") ve fiil-isimler kendiliğinden dışarıda
kalır. İki zayıf kanal ancak GÜÇLÜ okuma emri yokken mutasyon sayılır:
-mA fiil-ismi + gerek/lazım ("düzeltmemiz gerekiyor") ve şikâyet/kurulum
adları ("login çalışmıyor").

Asimetri bilinçli (soru turu kararıyla aynı, route.py): yanlış "okuma"
ucuzdur — router bloklamaz, ajan gerekirse skill'i öneriden yine yükler,
kapılar kanıtı yine ister. Yanlış "yazma" pahalıdır: approval gürültüsü
gerçek approval sinyalini değersizleştirir.

Regresyon bekçisi: tests/test_route.py (ölçülen vakalar kalıcı vakadır).
"""
import re

OKU_ISARETLERI = ("incele", "araştır", "karşılaştır", "kıyasla",
                  "değerlendir", "denetle", "eleştir", "analiz", "rapor",
                  "raporla", "gözden geçir", "keşfet", "öğren", "açıkla",
                  "özetle", "listele")
# Pozitif biçimde görülmesi tek başına mutasyon sayılan yazma fiilleri.
# routing.yml yazma kurallarının fiil tetikleriyle ve yaygın eş
# anlamlılarla uyumlu tutulur (incele.py P1 ×2: güzelleştir, iyileştir).
YAZ_FIILLERI = ("yap", "uygula", "ekle", "yaz", "düzelt", "kodla",
                "refactor", "taşı", "kaldır", "sil", "implement", "fix",
                "oluştur", "geliştir", "değiştir", "güncelle", "tasarla",
                "güzelleştir", "bağla", "çöz", "iyileştir", "hızlandır",
                "optimize", "düzenle", "birleştir", "kur", "yükselt",
                "temizle")
# Zayıf işaretler: şikâyet/kurulum adları. Fiil çekimi taşımazlar; güçlü
# okuma işareti varsa okuma kazanır ("bu bug'ın nedenini araştır").
ZAYIF_ISARETLER = ("bug", "hata", "çalışmıyor", "bozuk", "kurulum",
                   "onboard", "sisteme al")
# route.tokenize ile aynı karakter kümesi — ayrışırlarsa eşleşme kayar.
_TOKEN_RE = re.compile(r"[0-9a-zçğıöşü_.]+")

# Kök sonrası POZİTİF emir/istek ekleri (beyaz-liste; incele.py P1:
# kara-liste "yapısını"yı yap sanıyordu). Sırayla: yalın emir, -( y)AlIm,
# -(y)AyIm, -(y)In(Iz), -(I)yor…, -(y)AcAk/-(y)AcAğ…, -DI geçmiş
# (yaptım/yaptık/yaptılar) ve -DIğ sıfat-fiili (yaptığını), -mAlI…,
# -mAk, -sIn…, -(y)Abil… Eşleşmeyen her devam işaret DEĞİLDİR.
_POZ_EK = re.compile(
    r"^(?:"
    r"|y?[ae]l[ıi]m(?:[ıi]z)?"
    r"|y?[ae]y[ıi]m"
    r"|y?[ıiuü]n(?:[ıiuü]z)?"
    r"|[ıiuü]?yor\w*"
    r"|y?[ae]c[ae][kğ]\w*"
    r"|[dt][ıiuü](?:m|n|k|n[ıiuü]z|l[ae]r)?"
    r"|[dt][ıiuü]ğ\w*"
    r"|m[ae]l[ıi]\w*"
    r"|m[ae]k"
    r"|s[ıiuü]n\w*"
    r"|y?[ae]bil\w*"
    r")$")
# -mA fiil-ismi + iyelik: "düzeltmem(iz)", "düzeltmesi", "düzeltmeleri".
# Tek başına işaret değildir; gerek/lazım ile birlikte iş talebidir.
# Çıplak -ma/-me (olumsuz emir "yazma") bilinçli olarak DIŞARIDA.
_VN_EK = re.compile(r"^m[ae](?:m|m[ıiuü]z|n|n[ıiuü]z|s[ıi]|l[ae]r[ıi])$")


def _tara(text, isaretler):
    """(güçlü, fiil_ismi) — işaretlerin pozitif biçimde görülme bayrakları."""
    guclu = fiil_ismi = False
    for im in isaretler:
        if " " in im and im in text:
            guclu = True
    for m in _TOKEN_RE.finditer(text):
        tok = m.group()
        for im in isaretler:
            if " " in im or not tok.startswith(im):
                continue
            kalan = tok[len(im):]
            if _POZ_EK.match(kalan):
                guclu = True
            elif _VN_EK.match(kalan):
                fiil_ismi = True
    return guclu, fiil_ismi


def _zayif_var(text):
    """Şikâyet/kurulum adı geçiyor mu (ad — fiil morfolojisi uygulanmaz)."""
    tokens = [m.group() for m in _TOKEN_RE.finditer(text)]
    for im in ZAYIF_ISARETLER:
        if " " in im:
            if im in text:
                return True
        elif any(tok.startswith(im) for tok in tokens):
            return True
    return False


def mutasyon_niyeti(text):
    """Bu tur kod/dosya DEĞİŞTİRMEK mi istiyor? Biçim karar verir."""
    yaz, yaz_fiil_ismi = _tara(text, YAZ_FIILLERI)
    if yaz:
        return True
    if _tara(text, OKU_ISARETLERI)[0]:
        return False  # güçlü okuma emri: zayıf kanallar okumaya yenilir
    if yaz_fiil_ismi and ("gerek" in text or "lazım" in text):
        return True   # "auth kontrolünü düzeltmemiz gerekiyor"
    return _zayif_var(text)


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
