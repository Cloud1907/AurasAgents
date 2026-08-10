#!/usr/bin/env python3
"""Açık istek dili sezgileri — "kullanıcı bunu gerçekten istiyor mu?"

`routing.yml` içinde `explicit_request: true` taşıyan kurallar için kullanılır.
O kuralların tetiği zaten "şunu yap" demektir; dolayısıyla olumsuzu açık
REDDİR ve alıntılanmışı emir değil ANMA'dır. Bu ayrımı yapmadan tetik
eşleştirmek, opt-in vaadini ihlal eder.

Kapsam sınırı bilinçlidir: burası cümle çözümleyici DEĞİL. Router bir kapı
değil pusuladır (AGENTS.md) — amaç en sık yanlış-pozitifleri ucuza elemek.
Kalan belirsizliği skill'in kendi ön-koşulu kapatır: grilling, oturumu
açmadan önce isteğin gerçekten açık olduğunu doğrulamakla yükümlüdür.
"""
import re

# Türkçe olumsuzluk eki fiil kökünden hemen sonra gelir: "çek-me",
# "sok-ma-dan", "çek-mi-yor", "çek-mez". İki biçim 'm' ile başlar ama
# OLUMSUZ DEĞİLDİR: mastar ("çek-mek") ve gereklilik ("çek-meli").
OLUMSUZ_EK = re.compile(r"^m[eaıiuü]")
OLUMSUZ_ISTISNA = re.compile(r"^m[ea](k|l[iı])")

# İsimden fiil yapan -le/-la eki tetikle olumsuzluk arasına girebilir:
# "grill" + "-le" + "-me" → "grill'leme". Ek atlanmazsa olumsuzluk görünmez.
# 'l' isteğe bağlıdır çünkü tetiğin son harfiyle kaynaşabilir: "gril|leme"
# yazımında tetik "beni grill" eşleşince geriye yalnız "eme" kalır.
YAPIM_EKI = re.compile(r"^['’]?l?[eaıiuü]")

# Olumsuzluk tetiğin ekinde değil, yardımcı fiilde de olabilir: "sorguya
# çekmek İSTEMİYORUM". Sözcük listesi kaba ama tetik listesiyle aynı
# sınıfta: ucuz, okunur, testli.
RET_ISARETLERI = ("istemiyorum", "istemem", "istemez", "gerek yok",
                  "boşver", "boş ver", "vazgeçtim", "hayır")

# Anma (mention) kullanım değildir. Düz kesme (') KASTEN dışarıda —
# Türkçede ek ayıracıdır ("grill'le"), tırnak sanmak isteği yutardı.
ALINTI = re.compile(r"[\"“”«»‹›][^\"“”«»‹›]*[\"“”«»‹›]|[‘’][^‘’]*[’‘]")


def istek_degil(text):
    """İstem, açık istek OLMADIĞINI ele veren bir ret işareti taşıyor mu?

    Bilinen ve KABUL EDİLEN sınır: ret işareti tüm isteme mutlak veto koyar.
    "istemiyorum demiştim; fikrimi değiştirdim, beni sorguya çek" gibi
    fikir-değiştiren istem yönlendirilmez. Yanlış-negatiftir ve ucuzdur —
    kullanıcı /grilling yazar. Ters yönü (reddi istek sanmak) pahalıdır:
    istenmeyen sorgu oturumu açar. Sıra/kapsam çözümlemesi bu katmanın
    işi değil; belirsizliği skill'in kendi ön-koşulu kapatır (SKILL.md 0).
    """
    return any(r in text for r in RET_ISARETLERI)


def alintisiz(text):
    """Tırnak içindeki (anılan) bölümleri düşürür."""
    return ALINTI.sub(" ", text)


def olumsuzlanmis(trigger, text):
    """Tetiğin TÜM geçişleri olumsuz çekimliyse True.

    Tek geçiş bile olumluysa istek sayılır: "sorguya çekme dedim ama yine de
    beni sorguya çek" — sondaki olumlu kullanım kazanır.
    """
    yer, bulundu = text.find(trigger), False
    while yer != -1:
        bulundu = True
        kalan = YAPIM_EKI.sub("", text[yer + len(trigger):], count=1)
        if not (OLUMSUZ_EK.match(kalan) and not OLUMSUZ_ISTISNA.match(kalan)):
            return False
        yer = text.find(trigger, yer + 1)
    return bulundu
