#!/usr/bin/env python3
"""Kernel conformance testleri — skill, profil, form, şema ve evidence tutarlılığı.

Koşum: python3 bin/validate.py   (exit 0 = geçti)
"""
import json
import os
import re
import subprocess
import sys
import tempfile

try:
    import yaml
except ImportError:
    print("HATA: PyYAML gerekli (pip install pyyaml)")
    sys.exit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ERRORS = []


def err(msg):
    ERRORS.append(msg)


def check(cond, msg):
    if not cond:
        err(msg)


def frontmatter(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    return yaml.safe_load(m.group(1))


def test_skills():
    skills_dir = os.path.join(ROOT, ".agents", "skills")
    names = []
    for d in sorted(os.listdir(skills_dir)):
        full = os.path.join(skills_dir, d)
        if not os.path.isdir(full):
            continue
        md = os.path.join(full, "SKILL.md")
        check(os.path.isfile(md), f"skill '{d}': SKILL.md yok")
        if not os.path.isfile(md):
            continue
        fm = frontmatter(md)
        check(fm is not None, f"skill '{d}': frontmatter yok/bozuk")
        if fm:
            check(fm.get("name") == d,
                  f"skill '{d}': frontmatter name '{fm.get('name')}' dizinle uyuşmuyor")
            desc = fm.get("description", "")
            check(len(desc) >= 40,
                  f"skill '{d}': description çok kısa (seçim sinyali zayıf)")
            check("kullan" in desc.lower(),
                  f"skill '{d}': description ne zaman kullanılacağını söylemiyor")
        body = open(md, encoding="utf-8").read()
        low = body.lower()
        # SKILL.md < 500 satır (Anthropic best-practice; derinlik references/'a iner)
        check(len(body.splitlines()) < 500,
              f"skill '{d}': SKILL.md 500 satırı aştı — derinliği references/'a taşı")
        # İş akışı bölümü: eski 'Prosedür' veya yeni 'İş akışı'
        check("prosedür" in low or "akış" in low,
              f"skill '{d}': iş akışı/prosedür bölümü yok")
        # Gotcha içeriği (tuzak bilgisi) — bölüm adı serbest
        check("gotcha" in low or "tuzak" in low,
              f"skill '{d}': gotcha/tuzak bölümü yok (en yüksek sinyalli içerik)")
        # Eval: '## Eval' bölümü VEYA eval/ klasörü
        has_eval = ("## eval" in low or
                    os.path.isdir(os.path.join(full, "eval")))
        check(has_eval, f"skill '{d}': eval yok (## Eval bölümü ya da eval/ klasörü)")
        # Derin skill sinyali (uyarı değil, bilgi): references/ veya scripts/
        names.append(d)
    check(len(names) >= 4, f"en az 4 çekirdek skill bekleniyor, {len(names)} var")
    return set(names)


def test_profiles(skill_names):
    """Profilleri doğrular ve sınıf→izinli skill kümesini döndürür."""
    prof_dir = os.path.join(ROOT, ".agents", "capability-profiles")
    required_classes = {"code-change", "research", "incident"}
    seen, izinli_kume = set(), {}
    for f in sorted(os.listdir(prof_dir)):
        if not f.endswith(".yml"):
            continue
        path = os.path.join(prof_dir, f)
        data = yaml.safe_load(open(path, encoding="utf-8"))
        tc = data.get("task_class")
        seen.add(tc)
        izinli_kume[tc] = set(data.get("skills") or [])
        check(f == f"{tc}.yml", f"profil {f}: dosya adı task_class ile uyuşmuyor")
        for key in ("schema_version", "skills", "tools", "network",
                    "evidence_required", "risk"):
            check(key in data, f"profil {f}: '{key}' alanı eksik")
        for s in data.get("skills", []):
            check(s in skill_names,
                  f"profil {f}: tanımsız skill '{s}' (kayıtlı: {sorted(skill_names)})")
        risk = data.get("risk", {})
        check(risk.get("escalation") == "upward_only",
              f"profil {f}: risk.escalation 'upward_only' olmalı")
        net = data.get("network", {})
        check(net.get("mode") in ("allowlist", "open-web", "none"),
              f"profil {f}: geçersiz network.mode '{net.get('mode')}'")
    check(seen >= required_classes,
          f"eksik profil sınıfı: {required_classes - seen}")
    return izinli_kume


def test_issue_form():
    path = os.path.join(ROOT, ".github", "ISSUE_TEMPLATE", "work-contract.yml")
    check(os.path.isfile(path), "work-contract.yml issue form yok")
    if not os.path.isfile(path):
        return
    data = yaml.safe_load(open(path, encoding="utf-8"))
    ids = {b.get("id") for b in data.get("body", []) if isinstance(b, dict)}
    for needed in ("hedef", "gorev-sinifi", "kriterler", "kapsam",
                   "on-risk", "kanit"):
        check(needed in ids, f"issue form: '{needed}' alanı eksik")
    dropdowns = {b.get("id"): b for b in data.get("body", [])
                 if isinstance(b, dict) and b.get("type") == "dropdown"}
    if "gorev-sinifi" in dropdowns:
        opts = set(dropdowns["gorev-sinifi"]["attributes"]["options"])
        check(opts == {"code-change", "research", "incident"},
              f"issue form: görev sınıfı seçenekleri profillere uymuyor: {opts}")
    required_flags = [b.get("validations", {}).get("required")
                      for b in data.get("body", []) if isinstance(b, dict)]
    check(all(required_flags), "issue form: tüm alanlar zorunlu olmalı")


def test_workflow():
    path = os.path.join(ROOT, ".github", "workflows", "evidence.yml")
    check(os.path.isfile(path), "evidence.yml workflow yok")
    if not os.path.isfile(path):
        return
    data = yaml.safe_load(open(path, encoding="utf-8"))
    check("pull_request" in data.get(True, data.get("on", {})),
          "workflow: pull_request tetikleyicisi yok")
    text = open(path, encoding="utf-8").read()
    check("validate.py" in text, "workflow: kernel doğrulaması koşmuyor")
    check("make_evidence.py" in text, "workflow: evidence üretimi yok")
    check("upload-artifact" in text, "workflow: evidence artifact yüklenmiyor")


def test_evidence_roundtrip():
    schema = json.load(open(os.path.join(ROOT, "schemas",
                                         "evidence.schema.json"),
                            encoding="utf-8"))
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "evidence.json")
        digest_src = os.path.join(td, "report.txt")
        open(digest_src, "w").write("ornek rapor")
        proc = subprocess.run(
            [sys.executable, os.path.join(ROOT, "bin", "make_evidence.py"),
             "--out", out, "--contract", "#0", "--task-class", "code-change",
             "--skill", "implement-change",
             "--check", "tests=passed", "--check", "lint=passed",
             "--digest", f"report={digest_src}",
             "--risk-provisional", "auto", "--risk-final", "auto"],
            capture_output=True, text=True, cwd=ROOT)
        check(proc.returncode == 0,
              f"make_evidence başarısız: {proc.stderr or proc.stdout}")
        if proc.returncode != 0:
            return
        ev = json.load(open(out, encoding="utf-8"))
        for key in schema["required"]:
            check(key in ev, f"evidence: zorunlu alan eksik '{key}'")
        check(re.match(r"^[0-9a-f]{7,40}$", ev["commit_sha"]),
              "evidence: commit_sha biçimi geçersiz")
        for name, dig in ev.get("digests", {}).items():
            check(re.match(r"^sha256:[0-9a-f]{64}$", dig),
                  f"evidence: digest biçimi geçersiz ({name})")
        for c in ev["checks"]:
            check(c["status"] in ("passed", "failed", "skipped"),
                  f"evidence: geçersiz check durumu {c}")
        proc2 = subprocess.run(
            [sys.executable, os.path.join(ROOT, "bin", "make_evidence.py"),
             "--out", out, "--check", "tests=failed"],
            capture_output=True, text=True, cwd=ROOT)
        check(proc2.returncode == 1,
              "make_evidence: failed check'te non-zero dönmeli")


def test_agents_md():
    path = os.path.join(ROOT, "AGENTS.md")
    check(os.path.isfile(path), "AGENTS.md yok")
    if not os.path.isfile(path):
        return
    lines = open(path, encoding="utf-8").read().splitlines()
    check(len(lines) <= 200, f"AGENTS.md {len(lines)} satır (>200 — kısalt)")
    claude = os.path.join(ROOT, "CLAUDE.md")
    check(os.path.isfile(claude), "CLAUDE.md adapter yok")
    if os.path.isfile(claude):
        check("@AGENTS.md" in open(claude, encoding="utf-8").read(),
              "CLAUDE.md: @AGENTS.md importu yok")
    link = os.path.join(ROOT, ".claude", "skills")
    check(os.path.islink(link) and
          os.path.realpath(link) == os.path.realpath(
              os.path.join(ROOT, ".agents", "skills")),
          ".claude/skills → .agents/skills symlink'i yok/yanlış")


def test_rules():
    """Path-scoped domain kuralları geçerli frontmatter taşıyor mu."""
    rules_dir = os.path.join(ROOT, ".claude", "rules")
    if not os.path.isdir(rules_dir):
        return
    for f in sorted(os.listdir(rules_dir)):
        if not f.endswith(".md"):
            continue
        fm = frontmatter(os.path.join(rules_dir, f))
        check(fm is not None, f"rule {f}: frontmatter yok")
        if fm:
            check("paths" in fm, f"rule {f}: 'paths' scope tanımı yok")
            check(isinstance(fm.get("paths"), list) and fm["paths"],
                  f"rule {f}: 'paths' boş/liste değil")


def test_memory_tool():
    """Hafıza bakım robotu var, çalışıyor ve birim testleri geçiyor mu."""
    path = os.path.join(ROOT, "bin", "memory_hygiene.py")
    check(os.path.isfile(path), "bin/memory_hygiene.py yok")
    if os.path.isfile(path):
        proc = subprocess.run(
            [sys.executable, path, "--today", "2026-07-24"],
            capture_output=True, text=True, cwd=ROOT)
        check(proc.returncode in (0, 1),
              f"memory_hygiene beklenmedik exit: {proc.returncode}")
        check("HAFIZA BAKIMI" in proc.stdout,
              "memory_hygiene beklenen çıktı biçimini üretmedi")
    # Bekçinin bekçisi: araçların kendi birim testleri de koşmalı
    if os.path.isdir(os.path.join(ROOT, "tests")):
        proc = subprocess.run(
            [sys.executable, "-W", "error::ResourceWarning",
             "-m", "unittest", "discover", "-s", "tests", "-q"],
            capture_output=True, text=True, cwd=ROOT)
        check(proc.returncode == 0,
              f"tests/ birim testleri başarısız: {proc.stderr[-300:]}")


def test_routing(skill_names, profil_skills=None):
    """Router mekanizması: tablo eksiksiz mi, hook kayıtlı mı, seçim doğru mu."""
    path = os.path.join(ROOT, ".agents", "routing.yml")
    check(os.path.isfile(path), ".agents/routing.yml yok (skill yönlendirme tablosu)")
    router = os.path.join(ROOT, "bin", "route.py")
    check(os.path.isfile(router), "bin/route.py yok")
    if not (os.path.isfile(path) and os.path.isfile(router)):
        return

    cfg = yaml.safe_load(open(path, encoding="utf-8"))
    routed = set()
    for rule in cfg.get("rules", []):
        skill = rule.get("skill")
        check(skill, f"routing kuralı 'skill' alanı taşımıyor: {rule}")
        check(rule.get("task_class") in ("code-change", "research", "incident"),
              f"routing '{skill}': geçersiz task_class '{rule.get('task_class')}'")
        trig = rule.get("triggers") or []
        check(len(trig) >= 3,
              f"routing '{skill}': en az 3 tetik ifadesi gerekli ({len(trig)} var)")
        if rule.get("external"):
            continue  # skill repo dışında (kullanıcı-global) — varlığı doğrulanamaz
        check(skill in skill_names,
              f"routing '{skill}': böyle bir skill yok (kayıtlı: {sorted(skill_names)})")
        routed.add(skill)
    # Analiz katmanı: her iş bir disipline sahiplenir (tek sahip — zincir değil).
    roller = set(cfg.get("roles") or [])
    check(len(roller) >= 5,
          "routing: 'roles' kaydı yok/eksik — analiz 'bu iş kimin işi' sorusunu "
          "cevaplayamaz")
    for rule in cfg.get("rules", []):
        check(rule.get("owner") in roller,
              f"routing '{rule.get('skill')}': geçersiz/eksik owner "
              f"'{rule.get('owner')}' (kayıtlı roller: {sorted(roller)})")
    for d in cfg.get("disciplines", []):
        check(d.get("owner") in roller,
              f"disiplin '{d.get('owner')}': roles kaydında yok")
        check(len(d.get("triggers") or []) >= 3,
              f"disiplin '{d.get('owner')}': en az 3 tetik gerekli")
    # Codex hükmü (2026-07-26): profil "izin sınırı", routing "bu turdaki
    # seçim". Sınır uygulanmıyorsa profil süstür. routing ⊆ profile.skills.
    if profil_skills:
        for rule in cfg.get("rules", []):
            if rule.get("external"):
                continue  # repo dışı skill profil kümesinde aranmaz
            tc, sk = rule.get("task_class"), rule.get("skill")
            izinli = profil_skills.get(tc, set())
            check(sk in izinli,
                  f"routing '{sk}' sınıfı '{tc}' için zorunlu kılıyor ama o "
                  f"sınıfın profilinde yok (izinli: {sorted(izinli)}) — "
                  "ya profili genişlet ya task_class'ı düzelt")
    check(cfg.get("fallback", {}).get("message"),
          "routing: eşleşme yoksa ne yapılacağını söyleyen fallback mesajı yok")

    # Her skill ya yönlendirilir ya da gerekçeli olarak dışarıda bırakılır —
    # yoksa görünür ama hiç seçilmeyen ölü ağırlık olur.
    excluded = set()
    for entry in cfg.get("not_routed", []):
        skill = entry.get("skill")
        check(skill in skill_names,
              f"not_routed '{skill}': böyle bir skill yok")
        check(len((entry.get("reason") or "").strip()) >= 40,
              f"not_routed '{skill}': yönlendirilmeme gerekçesi yok/çok kısa")
        excluded.add(skill)
    missing = skill_names - routed - excluded
    check(not missing,
          f"routing tablosunda tetiği olmayan skill(ler): {sorted(missing)} "
          f"— tetik ekle ya da not_routed'a gerekçeyle yaz")

    # Hook kayıtlı mı (mekanizma; bağlam değil).
    settings = os.path.join(ROOT, ".claude", "settings.json")
    check(os.path.isfile(settings), ".claude/settings.json yok (router hook'u kayıtsız)")
    if os.path.isfile(settings):
        data = json.load(open(settings, encoding="utf-8"))
        cmds = [h.get("command", "")
                for entry in data.get("hooks", {}).get("UserPromptSubmit", [])
                for h in entry.get("hooks", [])]
        check(any("route.py" in c for c in cmds),
              "settings.json: UserPromptSubmit hook'u route.py'yi çağırmıyor")

    # Golden vaka: router gerçekten doğru skill'i seçiyor mu (regresyon kapısı).
    # Doğrulama koşumu kullanıcının aktivite kaydını kirletmemeli (izolasyon).
    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ, AURAS_EVENT_LOG=os.path.join(td, "events.jsonl"))
        _routing_golden_cases(router, env)


def _routing_golden_cases(router, env):
    for prompt, expected in (("kullanıcı endpoint'i ekle", "implement-change"),
                             ("bu metrik nerede hesaplanıyor", "research-with-evidence"),
                             ("login akışını güvenlik açısından incele", "security-review")):
        proc = subprocess.run(
            [sys.executable, router],
            input=json.dumps({"prompt": prompt}), capture_output=True,
            text=True, cwd=ROOT, env=env)
        check(proc.returncode == 0, f"route.py exit {proc.returncode} ('{prompt}')")
        check(expected in proc.stdout,
              f"router '{prompt}' → beklenen '{expected}' yönlendirmesi yok")
        check("🧭" in proc.stdout and "🔧" in proc.stdout,
              "router: cevap başlığı biçimini dayatmıyor — kullanıcı yazışmada "
              "hangi skill'in çalıştığını göremez")


def test_no_external_roles():
    """Sabit rol dosyası KURMA ilkesi mekanizmaya bağlandı.

    Disiplin bir ETİKETTİR (analiz çıktısı); derinlik yalnız skill'lerde
    yaşar. Router dış rol dosyasına (ör. ~/.claude/agents/*.md) atıf yaparsa
    ikinci bir bilgi otoritesi doğar ve skill'lerle çakışıp bayatlar —
    kullanıcı itirazı 2026-07-26, Codex mutabakatı aynı gün.
    """
    router = os.path.join(ROOT, "bin", "route.py")
    if not os.path.isfile(router):
        return
    metin = open(router, encoding="utf-8").read()
    for yasak in ("~/.claude/agents", ".claude/agents/"):
        check(yasak not in metin,
              f"route.py: dış rol dosyasına atıf ('{yasak}') — disiplin etiket "
              "olmalı, derinlik skill'de yaşamalı")
    check(not os.path.isdir(os.path.join(ROOT, ".agents", "roles")),
          ".agents/roles/ var — sabit rol tanımı skill'lerle çakışır; "
          "derinlik gerekiyorsa skill yaz")


def test_visibility():
    """Görünürlük katmanı: skill çağrıları ve tur aktivitesi kayda geçiyor mu.

    Kullanıcı 'hangi skill çağrıldı, ne yapıldı' sorusunu benim beyanımdan
    değil makine kaydından cevaplayabilmeli.
    """
    for rel in ("bin/run_event.py", "bin/durum.py"):
        check(os.path.isfile(os.path.join(ROOT, rel)), f"görünürlük aracı yok: {rel}")
    if not all(os.path.isfile(os.path.join(ROOT, r))
               for r in ("bin/run_event.py", "bin/durum.py")):
        return

    settings = os.path.join(ROOT, ".claude", "settings.json")
    if os.path.isfile(settings):
        data = json.load(open(settings, encoding="utf-8"))
        hooks = data.get("hooks", {})
        skill_hook = any(
            "run_event.py" in h.get("command", "")
            for e in hooks.get("PostToolUse", [])
            if "Skill" in (e.get("matcher") or "")
            for h in e.get("hooks", []))
        check(skill_hook,
              "settings.json: PostToolUse/Skill hook'u run_event.py'yi çağırmıyor "
              "— skill çağrıları kayda geçmez")
        check(any("kapi.py" in h.get("command", "")
                  for e in hooks.get("Stop", []) for h in e.get("hooks", [])),
              "settings.json: Stop hook'u kapi.py'yi çağırmıyor — kanıtsız tur "
              "kapanabilir")
        check(any("--kind ui" in h.get("command", "")
                  for e in hooks.get("PostToolUse", []) for h in e.get("hooks", [])),
              "settings.json: tarayıcı etkileşimi kayda geçmiyor — 'tıklama "
              "kanıtı' kapısı çalışmaz")
        check(any("--kind edit" in h.get("command", "")
                  for e in hooks.get("PostToolUse", []) for h in e.get("hooks", [])),
              "settings.json: düzenlemeler kayda geçmiyor — kapı neyin "
              "değiştiğini bilemez")

    # Kayıt disposable ve gitignore'lu olmalı (auto-memory kuralı: hiçbir iş
    # buna bağımlı olamaz, repoya sızmamalı).
    gi = os.path.join(ROOT, ".gitignore")
    check(os.path.isfile(gi) and ".agents/runtime" in open(gi, encoding="utf-8").read(),
          ".gitignore: .agents/runtime yok — disposable kayıt repoya sızar")

    # Uçtan uca: sahte Skill hook payload'u → olay → tabloda görünür.
    with tempfile.TemporaryDirectory() as td:
        log = os.path.join(td, "events.jsonl")
        p1 = subprocess.run(
            [sys.executable, os.path.join(ROOT, "bin", "run_event.py"),
             "--kind", "skill", "--log", log],
            input=json.dumps({"tool_input": {"skill": "kernel-work"}}),
            capture_output=True, text=True, cwd=ROOT)
        check(p1.returncode == 0, f"run_event.py exit {p1.returncode}")
        p2 = subprocess.run(
            [sys.executable, os.path.join(ROOT, "bin", "durum.py"), "--log", log],
            capture_output=True, text=True, cwd=ROOT)
        check(p2.returncode == 0, f"durum.py exit {p2.returncode}")
        check("kernel-work" in p2.stdout,
              "durum.py: kaydedilen skill çağrısı tabloda görünmüyor")


def test_onboarding_parity():
    """auras-init.sh, validate.py'nin aradığı her şeyi yeni projeye taşıyor mu.

    Sürüklenme bekçisi: kernel'e yeni zorunlu dosya eklenip kurulum betiği
    güncellenmezse, /auras ile bağlanan proje ilk doğrulamada kırmızı verir.
    """
    # auras-init.sh yalnız kanonik şablon reposunda bulunur; bağlanmış
    # projelerde yoktur ve orada denetlenecek bir şey de yok.
    path = os.path.join(ROOT, "bin", "auras-init.sh")
    if not os.path.isfile(path):
        return
    text = open(path, encoding="utf-8").read()
    required = [
        "AGENTS.md", "CLAUDE.md",
        ".agents/skills", ".agents/capability-profiles", ".agents/routing.yml",
        ".claude/rules",
        ".github/ISSUE_TEMPLATE/work-contract.yml",
        ".github/workflows/evidence.yml",
        "schemas/evidence.schema.json",
        "bin/validate.py", "bin/make_evidence.py", "bin/route.py",
        "bin/memory_hygiene.py", "bin/run_event.py", "bin/durum.py",
        "bin/kapi.py", "bin/araclar.py",
        "bin/codex-review.sh", "bin/install-hooks.sh",
        "bin/hooks", "tests",
    ]
    for rel in required:
        check(rel in text,
              f"auras-init.sh '{rel}' taşımıyor — yeni proje doğrulamada kırılır")
    check("route.py" in text and "UserPromptSubmit" in text,
          "auras-init.sh: router hook'unu hedef projeye kaydetmiyor")


def test_mechanisms():
    """Deterministik kapılar ve risk sinyali araçları yerinde mi."""
    for rel in ("bin/hooks/pre-push", "bin/install-hooks.sh",
                "bin/codex-review.sh"):
        path = os.path.join(ROOT, rel)
        check(os.path.isfile(path), f"mekanizma eksik: {rel}")
        if os.path.isfile(path):
            check(os.access(path, os.X_OK), f"{rel}: çalıştırma izni yok")
    hook = os.path.join(ROOT, "bin", "hooks", "pre-push")
    if os.path.isfile(hook):
        check("validate.py" in open(hook, encoding="utf-8").read(),
              "pre-push kancası kernel doğrulamasını koşmuyor")
    # Kurulu kanca makineye özel durumdur; CI'da .git/hooks yoktur ve CI
    # zaten aynı doğrulamayı doğrudan koşar.
    installed = os.path.join(ROOT, ".git", "hooks", "pre-push")
    if os.path.isdir(os.path.join(ROOT, ".git")) and not os.environ.get("CI"):
        check(os.path.isfile(installed) and os.access(installed, os.X_OK),
              "pre-push kancası kurulu değil (bash bin/install-hooks.sh)")


def main():
    skill_names = test_skills()
    profil_skills = test_profiles(skill_names)
    test_issue_form()
    test_workflow()
    test_evidence_roundtrip()
    test_agents_md()
    test_rules()
    test_memory_tool()
    test_routing(skill_names, profil_skills)
    test_no_external_roles()
    test_visibility()
    test_onboarding_parity()
    test_mechanisms()
    if ERRORS:
        print(f"KERNEL DOĞRULAMA: {len(ERRORS)} hata")
        for e in ERRORS:
            print(f"  ✗ {e}")
        return 1
    print("KERNEL DOĞRULAMA: tüm kontroller geçti ✓")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
