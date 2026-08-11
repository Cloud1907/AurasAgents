#!/usr/bin/env python3
"""Skill kaydı — "bu skill kurulu mu" ve "hangi izin sınırına ait".

Router'ın yönlendirme mantığından ayrı tutulur: burası TABLO değil ENVANTER
sorusu sorar. Otorite capability profilidir (AGENTS.md: profil izin sınırı,
routing o sınır içinden seçim); dolayısıyla bir skill'in görev sınıfını
profil söyler, tetik kelimeleri değil.
"""
import os


def skill_installed(skill, pdir):
    """Skill bu projede ya da kullanıcı-global dizinde kurulu mu."""
    for base in (os.path.join(pdir, ".agents", "skills"),
                 os.path.join(pdir, ".claude", "skills"),
                 os.path.expanduser("~/.claude/skills")):
        if os.path.isdir(os.path.join(base, skill)):
            return True
    return False


def skill_task_class(skill, pdir):
    """Skill'i izinli sayan profilin sınıfı (yoksa None).

    Profil izin sınırıdır, dolayısıyla sınıfın OTORİTESİ odur — tahmin değil.
    Bilinmeyen skill'de None döner; çağıran o zaman kelime puanlamasına
    düşer, çünkü sınıfı uydurmak izin sınırını uydurmaktır.
    """
    try:
        import yaml  # route.load_rules ile aynı biçim: yoksa sessiz çekil
    except ImportError:
        return None
    pd = os.path.join(pdir, ".agents", "capability-profiles")
    try:
        adlar = sorted(os.listdir(pd))
    except OSError:
        return None
    for ad in adlar:
        if not ad.endswith(".yml"):
            continue
        # Dar except BİLİNÇLİ: geniş `except Exception` bir NameError'ı
        # sessizce yutup bu fonksiyonu hep None döndürmüştü — profil
        # otoritesi hiç çalışmadı, kimse görmedi (inceleme 11. tur).
        try:
            with open(os.path.join(pd, ad), encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        except (OSError, yaml.YAMLError):
            continue
        if skill in (data.get("skills") or []):
            return data.get("task_class")
    return None


def kuralsiz_komut_kurali(explicit, pdir):
    """Kuralsız ama kurulu bir /komut için sentetik kural (değilse None).

    Kullanıcı komutla seçimini yapmışken anahtar kelimeyle başka skill'i
    zorunlu kılmak, açık iradeyi ezmektir. Sınıf profilden gelir: komut,
    izin sınırını düşürmemeli — dosya yazan skill'i salt-okunur profile
    mahkûm etmek işi sessizce kırar.

    Risk de taşınır: /project-onboarding ile /auras aynı işi yapar; birinin
    approval diğerinin auto sayılması riski komut seçimine bağlardı. Kuralsız
    skill'in beyan edilmiş riski olmadığından KATI taraf seçilir — research
    dışı her sınıf approval (fazla temkin, eksik temkinden iyidir).

    Profilde OLMAYAN skill (ör. yalnız kullanıcı-global dizinde duran üçüncü
    taraf skill) zorunlu kılınmaz: sınırı tanımlı değilse sınıfını ve riskini
    uydurmak, izin sınırının kendisini uydurmaktır. Router yine "kullanıcı
    açıkça /X istedi" der — çağrı kaybolmaz, yalnız zorunluluk iddia edilmez.
    """
    if not (explicit and skill_installed(explicit, pdir)):
        return None
    sinif = skill_task_class(explicit, pdir)
    if not sinif:
        return None
    return {"skill": explicit, "task_class": sinif,
            "risk": "auto" if sinif == "research" else "approval"}
