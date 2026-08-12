#!/usr/bin/env python3
"""Değişikliğin KENDİSİNDEN okunan iki şey: risk sınıfı ve diff güvenilirliği.

Neden ayrı modül: `incele.py` merge KARARINI verir, `hukum.py` inceleyicinin
ne dediğini okur, `tur.py` kaçıncı turda olduğumuzu sayar; burası incelemeden
ÖNCE, yalnız diff'e bakarak cevaplanan iki soruyu ayırır — "bu ne sınıf bir
değişiklik" ve "bu diff'in hükmüne güvenilir mi". İkisi de dış dünyaya
dokunmaz, ikisi de AGENTS.md politikasının kod karşılığıdır.

Bu modül SAF: gh/Codex çağrısı yok, yalnız yol listesi ve diff metni.
"""
import re

# --- Risk sınıflandırma (AGENTS.md risk politikası, path kuralı) -----------
# Eskalasyon YALNIZ yukarı: bilinmeyen yol `approval` sayılır, `auto` değil.
DENY = re.compile(
    r"(^|/)(\.env($|\.)|secrets?/|credentials?/|id_rsa|.*\.pem$|.*\.key$)", re.I)
APPROVAL = re.compile(
    r"(auth|kimlik|oturum|session|payment|odeme|ödeme|migration|permission"
    r"|/hooks/|settings\.json|token|deploy|^bin/|^\.agents/|^\.github/"
    r"|package(-lock)?\.json$|\.csproj$|requirements\.txt$)", re.I)
AUTO = re.compile(r"(^docs/|\.md$|^tests?/|^\.agents/reports/)", re.I)


def risk_sinifi(dosyalar):
    """Değişen yollardan nihai risk sınıfı. Boş liste → approval (temkinli)."""
    if not dosyalar:
        return "approval"
    if any(DENY.search(d) for d in dosyalar):
        return "deny"
    if any(APPROVAL.search(d) for d in dosyalar):
        return "approval"
    if all(AUTO.search(d) for d in dosyalar):
        return "auto"
    return "approval"


# Diff, inceleyiciye TALİMAT veriyorsa hüküm güvenilmez. Yalnız EKLENEN
# satırlara bakılır; doğal dil kalıbı aranır (kod/regex tanımı değil).
ENJEKSIYON = re.compile(
    r"(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above)\s+"
    r"(instruction|rule|prompt)"
    r"|(?:sen|you)\s+bir\s+incele|you\s+are\s+(a\s+)?review"
    r"|TEM[İI]Z\s+(olarak\s+)?(yaz|raporla|d[öo]n)"
    r"|(output|report|respond)\s+(with\s+)?(TEMIZ|CLEAN|APPROVE)"
    r"|(approve|onayla)\s+(this|bu)\s+(pr|diff|change)", re.I)


def enjeksiyon_var_mi(diff):
    """Eklenen satırlarda inceleyiciye yönelik talimat var mı."""
    for satir in (diff or "").splitlines():
        if satir.startswith("+") and ENJEKSIYON.search(satir):
            return True
    return False
