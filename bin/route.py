#!/usr/bin/env python3
"""Skill router — istek metninden görev sınıfı + skill seçimi üretir.

UserPromptSubmit hook'u olarak çalışır: stdin'den hook JSON'unu okur,
stdout'a Claude Code hook JSON'u basar (additionalContext + systemMessage).

İki kurulum biçimi:
  1. Proje bazlı — projenin `.claude/settings.json`'ı kendi `bin/route.py`'sini
     çağırır (repoyla taşınır, klonlayan herkeste çalışır).
  2. Global yedek — `~/.claude/settings.json` kanonik route.py'yi
     `--global-fallback` ile çağırır: her projede çalışır, ama projenin kendi
     router hook'u varsa sessizce çekilir (çift yönlendirme olmaz).

Yönlendirme tablosu sırası: `$CLAUDE_PROJECT_DIR/.agents/routing.yml` →
CWD'den yukarı yürüyerek bulunan proje → kanonik AurasAgents tablosu.

Elle deneme:
    echo '{"prompt":"login endpointine rate limit ekle"}' | python3 bin/route.py

Tasarım kuralı: bu betik ASLA isteği bloklamaz. Hata/eksik bağımlılık
durumunda sessizce exit 0 döner — yönlendirme yardımdır, kapı değildir.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANONICAL = os.path.join(ROOT, ".agents", "routing.yml")

# Skill envanteri ayrı modülde (bin/skill_kayit.py; MOTOR listesinde —
# bekçi: tests/test_kernel_dosyalari). Import başarısızsa yönlendirme
# çalışmaya devam eder, yalnız /komut ayrıcalığı ve kurulum uyarısı susar:
# router bloklamaz, eksik yardımı yokluğa çevirir.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import davranis
    from skill_kayit import (kuralsiz_komut_kurali, profil_disinda,
                             skill_installed, skill_izinli, skill_task_class)
except Exception:                                    # pragma: no cover
    skill_task_class = None

    def skill_installed(skill, pdir):
        return True

    def kuralsiz_komut_kurali(explicit, pdir):
        return None

    def profil_disinda(skill, pdir):
        return False

    def skill_izinli(skill, pdir):
        return False

# Türkçe küçük harf: I → ı (str.lower() bunu yapmaz).
TR_LOWER = str.maketrans("IİĞÜŞÖÇ", "iiğüşöç")


def normalize(text):
    return text.translate(TR_LOWER).lower()


def tokenize(text):
    return [t for t in re.split(r"[^0-9a-zçğıöşü_.]+", text) if t]


def matches(trigger, text, tokens):
    """Boşluklu tetik alt-dize; tek kelime tetik, kelime başı eşleşmesi."""
    if " " in trigger:
        return trigger in text
    return any(tok.startswith(trigger) for tok in tokens)


def project_dir():
    """Aktif projenin kökü: hook env'i, yoksa CWD'den yukarı arama."""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and os.path.isdir(env):
        return os.path.abspath(env)
    cur = os.getcwd()
    while True:
        if os.path.isdir(os.path.join(cur, ".agents")) or \
           os.path.isdir(os.path.join(cur, ".git")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return os.getcwd()
        cur = parent


def routing_path(pdir=None):
    """(tablo yolu, projeye mi ait) — proje tablosu kanonik olanı yener."""
    pdir = pdir or project_dir()
    local = os.path.join(pdir, ".agents", "routing.yml")
    if os.path.isfile(local):
        return local, True
    return CANONICAL, False


def load_rules(path=None):
    import yaml  # yoksa ImportError → main() sessizce çıkar
    with open(path or routing_path()[0], encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def project_registers_router(pdir):
    """Proje kendi router hook'unu kaydetmiş mi (global yedek geri çekilir)."""
    try:
        with open(os.path.join(pdir, ".claude", "settings.json"),
                  encoding="utf-8") as fh:
            return "route.py" in fh.read()
    except OSError:
        return False


def _extras(cfg, text, tokens):
    """Risk yüzeyi eşleşmesiyle daima eklenen skill'ler."""
    out = []
    for rule in cfg.get("always_add", []):
        if any(matches(normalize(t), text, tokens)
               for t in rule.get("triggers", [])):
            out.append(rule["skill"])
    return out


def sahip(prompt, cfg, primary=None):
    """İşin TEK sahip disiplinini seç: 'bu iş kimin işi?'

    Skill seçiminden bağımsızdır — aynı skill farklı disiplinlerde kullanılır
    (implement-change hem frontend hem backend işinde). Zincir DEĞİL tek sahip
    döner: rol tiyatrosu yasağı (VIBE_CODING_TASARIM_TEMMUZ_2026.md:62).
    Eşleşme yoksa kuralın kendi `owner` alanına düşer.
    """
    text = normalize(prompt)
    tokens = tokenize(text)
    en_iyi, en_puan = None, 0
    for d in cfg.get("disciplines", []):
        puan = sum(1 for t in d.get("triggers", [])
                   if matches(normalize(t), text, tokens))
        if puan > en_puan:
            en_iyi, en_puan = d.get("owner"), puan
    if en_iyi:
        return en_iyi
    # Sahip uydurma: disiplin okunamıyorsa None döner, router bunu söyler.
    return (primary or {}).get("owner")


# --- Soru turu tespiti (2026-08-07) --------------------------------------
# Bulgu: bir oturumda 12+ tur yanlış sınıflandı. "bizim hafıza tarafı
# başarılı mı?" → code-change/approval + zorunlu kernel-work; "ne
# yapmalıyız?" → implement-change. Türkçe önek eşleşmesi DOĞRU çalışıyordu
# ("yapmalıyız" ile "yap" aynı fiildir); kusur tur TİPİNİN okunmamasıydı.
#
# Soru turunda zorunlu skill dayatmak iki zarar üretir: (1) her sohbet turu
# "onay riskli iş" görünür ve gerçek approval sinyali değersizleşir,
# (2) ajan atlama gerekçesini kayda geçirmek zorunda kalır — bürokrasi.
#
# Asimetri bilinçli: yanlış "soru" ucuzdur (router zaten bloklamaz, tur
# kapısı kanıtı yine ister), yanlış "code-change/approval" gürültülüdür.
SORU_SONU = re.compile(r"\?\s*$")
SORU_EKI = re.compile(
    r"(?:^|\s)(m[ıiuü]|m[ıiuü]s[ıi]n|m[ıiuü]y[ıi]m|m[ıiuü]sunuz)\b")
SORU_BASI = re.compile(
    r"^(ne|neden|niye|nas[ıi]l|hangi|kim|ka[çc]|nerede|sence|acaba)\b")


def soru_turu(text):
    """Bu tur bir SORU mu, yoksa iş emri mi?

    Soru işareti, ayrı duran soru eki (…iyi mi) ya da cümle BAŞINDA soru
    kelimesi arar. Soru kelimesi cümle ORTASINDAysa emir sayılır:
    "actions'a bak neden koşmadı" bir iştir, soru değil.
    """
    return bool(SORU_SONU.search(text) or SORU_EKI.search(text)
                or SORU_BASI.match(text))


def _komut_kurali_cozumle(explicit, cfg, scored, pdir):
    """Kuralsız /komutun sentetik kuralı, sınıfı ve riski çözülmüş hâlde.

    Meta-skill sınıfını işten alır (kural `task_class` boş döner): kelime
    puanlamasının sınıfı korunur, risk de o sınıftan türetilir — yoksa
    dağıtıcı bir skill, devrettiği kod işini salt-okunur profile mahkûm eder.
    """
    sentetik = kuralsiz_komut_kurali(explicit, pdir or project_dir())
    if not sentetik:
        return None
    sinif = (sentetik.get("task_class")
             or (scored[0][2].get("task_class") if scored else None)
             or cfg.get("fallback", {}).get("task_class", "research"))
    return dict(sentetik, task_class=sinif,
                risk="auto" if sinif == "research" else "approval")


def _puanla(cfg, text, tokens, explicit):
    """(tetik-puanlı kurallar, açık komutun kuralları) — ikisi de sıralı.

    Aynı skill birden çok kuralda olabilir (implement-change hem code-change
    hem incident). Açık /komut ilk eşleşende dururken diğeri ERİŞİLEMEZ
    kalıyordu; bağlam (tetik isabeti) seçsin.
    """
    scored, komut = [], []
    for rule in cfg.get("rules", []):
        hit = [t for t in rule.get("triggers", [])
               if matches(normalize(t), text, tokens)]
        if explicit and explicit == rule.get("skill"):
            komut.append((len(hit), rule, hit))
        if hit:
            scored.append((len(hit), rule.get("specificity", 1), rule, hit))
    # Puan → özgüllük → routing.yml sırası (kararlı sonuç).
    scored.sort(key=lambda s: (-s[0], -s[1]))
    komut.sort(key=lambda k: -k[0])
    return scored, komut


def route(prompt, cfg, pdir=None):
    """(task_class, primary, extras, hits, explicit) döndürür."""
    text = normalize(prompt)
    tokens = tokenize(text)

    explicit = None
    m = re.match(r"^\s*/([a-z0-9-]+)", prompt.strip())
    if m:
        explicit = m.group(1)

    scored, komut_kurallari = _puanla(cfg, text, tokens, explicit)
    if komut_kurallari:
        rule, hit = komut_kurallari[0][1], komut_kurallari[0][2]
        return (rule.get("task_class", "research"), rule,
                [s for s in _extras(cfg, text, tokens) if s != rule["skill"]],
                hit or [f"/{explicit}"], explicit)

    extras = _extras(cfg, text, tokens)

    sentetik = _komut_kurali_cozumle(explicit, cfg, scored, pdir)
    if sentetik:
        return (sentetik["task_class"], sentetik,
                [s for s in extras if s != explicit], [f"/{explicit}"],
                explicit)

    # Açık /komut soru biçimini EZER ("/auras bunu bağlar mısın?" iş emridir);
    # o dal yukarıda zaten döndü. Buraya gelen soru turu salt-okunur profil
    # alır ve zorunlu skill dayatılmaz — ajan kendi seçer, kapı kanıtı yine ister.
    if soru_turu(text):
        return "research", None, extras, [], explicit

    if not scored:
        fb = cfg.get("fallback", {})
        return fb.get("task_class", "research"), None, extras, [], explicit

    _score, _spec, top, hit = scored[0]
    for _s, _sp, rule, _h in scored[1:]:
        if rule["skill"] not in extras:
            extras.append(rule["skill"])
    extras = [s for s in extras if s != top["skill"]]
    return top.get("task_class", "research"), top, extras, hit, explicit


def render(prompt, cfg, pdir=None, table_is_local=True):
    pdir = pdir or project_dir()
    task_class, primary, extras, hits, explicit = route(prompt, cfg, pdir)
    profile = os.path.join(".agents", "capability-profiles", f"{task_class}.yml")
    lines = ["[AurasAgents router]"]

    # Karşılama katmanı: açık /komut yoksa işi önce AurasPrime karşılar.
    # Derinlik skill dosyasındadır; burada yalnız DAVRANIŞ enjekte edilir —
    # her turda skill yüklemek maliyet, karşılama kararını skill'in kendi
    # negatif tetikleri verir (küçük iş ve takip turunda tören yapılmaz).
    if not explicit:
        lines.append(davranis.KARSILAMA)

    if explicit and profil_disinda(explicit, pdir):
        lines.append(
            f"/{explicit} bu projenin izin sınırı dışında (capability "
            "profilinde yok) — YÜKLEME. Gerekiyorsa kullanıcıya söyle: "
            "profile eklemek bilinçli bir karardır, reviewed PR ister.")
    elif explicit:
        lines.append(f"Kullanıcı açıkça /{explicit} istedi — onu yükle.")

    lines.append(f"Görev sınıfı: {task_class}  |  profil: {profile}")

    if primary:
        lines.append(
            f"ZORUNLU skill: {primary['skill']} "
            f"(ön risk: {primary.get('risk', 'auto')}; "
            f"eşleşen tetik: {', '.join(hits[:4])})")
    else:
        lines.append("Eşleşen skill yok.")
        msg = cfg.get("fallback", {}).get("message")
        if msg:
            lines.append(msg.strip())

    if extras:
        lines.append(f"Ek skill: {', '.join(extras)}")

    if not table_is_local:
        lines.append(
            "Not: bu proje kendi routing.yml'ini taşımıyor, kanonik AurasAgents "
            "tablosu kullanıldı.")
    eksik = [s for s in ([primary["skill"]] if primary else []) + extras
             if not skill_installed(s, pdir)]
    if eksik:
        lines.append(
            f"Uyarı: {', '.join(eksik)} bu projede kurulu değil — /auras ile "
            "bağla, ya da kurulu olmadığını kullanıcıya söyleyip skill'siz çalış.")

    lines.append(
        "Kural: yönlendirilen skill'i Skill aracıyla YÜKLEMEDEN işe başlama. "
        "Yönlendirme yanlışsa tek cümleyle gerekçelendir ve kullanıcıya söyle "
        "— sessizce atlama.")

    lines += _davranis_satirlari(prompt, cfg, primary, task_class)

    context = "\n".join(lines)
    picked = primary["skill"] if primary else "—"
    if explicit:
        picked = f"/{explicit}"
    summary = f"router → {task_class} · {picked}"
    if extras:
        summary += f" (+{len(extras)})"
    return context, summary


def _davranis_satirlari(prompt, cfg, primary, task_class):
    """Her turda enjekte edilen davranış sözleşmesi (metinler: davranis.py)."""
    return davranis.sozlesme(sahip(prompt, cfg, primary), task_class,
                             (primary or {}).get("risk", "auto"))


def _kaydet(prompt, cfg, pdir):
    """Yönlendirme kararını görünür kayda yaz (best-effort; asla bloklamaz).

    Böylece `bin/durum.py` "ne yönlendirildi vs ne yüklendi" karşılaştırmasını
    ajanın beyanına değil kayda dayandırır.
    """
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "_run_event", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "run_event.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        task_class, primary, extras, _hits, explicit = route(prompt, cfg, pdir)
        mod.append({
            "kind": "route",
            "task_class": task_class,
            "routed": (primary or {}).get("skill") or (explicit if explicit else None),
            "extras": extras,
            "intent": prompt,
        }, mod.log_path(pdir=pdir))
    except Exception:
        pass


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    pdir = project_dir()
    # Global yedek, projenin kendi router'ı varsa devreye girmez.
    if "--global-fallback" in argv and project_registers_router(pdir):
        return 0
    try:
        raw = sys.stdin.read()
    except Exception:
        return 0
    try:
        prompt = (json.loads(raw or "{}") or {}).get("prompt", "")
    except (ValueError, AttributeError):
        prompt = raw
    if not prompt or not prompt.strip():
        return 0
    try:
        table, is_local = routing_path(pdir)
        cfg = load_rules(table)
        context, summary = render(prompt, cfg, pdir, is_local)
    except Exception:
        return 0  # yönlendirme yardımdır; asla isteği bloklamaz
    _kaydet(prompt, cfg, pdir)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        },
        "systemMessage": summary,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
