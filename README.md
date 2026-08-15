# AurasAgents

Tek kişilik kurucu için kanıt-temelli agent çalışma sistemi — GitHub-native
thin kernel. Tasarım: [VIBE_CODING_TASARIM_TEMMUZ_2026.md](VIBE_CODING_TASARIM_TEMMUZ_2026.md) ·
Vizyon: [AURASAGENTS_PRODUCT_VISION.md](AURASAGENTS_PRODUCT_VISION.md) ·
Kararlar: [docs/decisions/](docs/decisions/)

## Yeni bir projeyi bağlamak

Herhangi bir proje klasöründe Claude Code aç ve `/auras` yaz. Kurulum
(AGENTS.md, profiller, form, CI, kanca, GitHub) tek adımda yapılır.
Global skill: `~/.claude/skills/auras/` — kanonik kopyası
`.agents/skills/auras/`. Motor: `bin/auras-init.sh` (idempotent).

## Yapı

```
AGENTS.md                        kanonik çalışma kuralları (motor-bağımsız)
CLAUDE.md                        Claude adapter'ı (@AGENTS.md)
.agents/skills/                  çekirdek skill'ler (Agent Skills standardı)
.agents/capability-profiles/     görev sınıfı → izin kümesi (3 profil)
.github/ISSUE_TEMPLATE/          work contract issue form
.github/workflows/evidence.yml   CI: kernel doğrulama + evidence.json
schemas/evidence.schema.json     kanıt manifesti şeması
bin/validate.py                  kernel conformance testleri
bin/make_evidence.py             kanıt üretici
```

## Komutlar

```bash
python3 bin/validate.py
```

```bash
bash bin/install-hooks.sh
```

```bash
bin/codex-review.sh --dry-run
```

Sistem hafızası raporunu canlı veriden üret ve aç:

```bash
python3 bin/report.py --open
```

## Kurulum sonrası (GitHub tarafı — bir kez)

1. Repo'yu GitHub'a push'la.
2. Branch protection (main) — bu repoda **kurulu** (2026-08-16). Yeni bir
   projede kurmak için (repo public ya da GitHub Pro olmalı):

   ```bash
   gh api -X PUT repos/<owner>/<repo>/branches/main/protection --input - <<'JSON'
   {"required_status_checks":{"strict":true,"contexts":["kernel"]},
    "enforce_admins":true,
    "required_pull_request_reviews":{"required_approving_review_count":0,
                                     "dismiss_stale_reviews":true},
    "restrictions":null,"allow_force_pushes":false,"allow_deletions":false}
   JSON
   ```

   Üç alanın üçü de **şart**, biri eksikse sınır delik kalır:

   - `enforce_admins: true` — `false` ise agent kullanıcının yetkisiyle
     korumayı geçer; sınır yalnız kazaya karşı bir hatırlatıcıya döner.
   - `required_pull_request_reviews` — **`null` YETMEZ.** Yalnız required
     status check ile, check'i ZATEN GEÇMİŞ bir SHA doğrudan `main`'e
     itilebilir: dalı it, CI koşsun, sonra aynı commit'i main'e it. Bağımsız
     inceleme bunu P0 olarak yakaladı (2026-08-16) ve ölçümle doğrulandı.
     `required_approving_review_count: 0` PR'ı zorunlu kılar ama ikinci bir
     insan istemez — tek kişilik akışa uyar.
   - `allow_force_pushes: false` — yoksa geçmiş yeniden yazılabilir.

   **Kurduktan sonra DOĞRULA, hemen değil.** Ayar değişikliğinin yerleşmesi
   saniyeler alır; kurulumdan hemen sonraki push propagasyon penceresinden
   geçebilir (2026-08-16'da bizzat yaşandı — koruma doğruydu, push geçti).
   Doğrulama: `git commit --allow-empty` + `git push --no-verify origin main`
   → **iki gerekçeyle birden** reddedilmeli:
   `Changes must be made through a pull request.` ve
   `Required status check "kernel" is expected.`
   Tek gerekçe görüyorsan sınır eksiktir.
3. Codex Review app'ini repoya bağla (Review all PRs).
4. claude.ai/code üzerinden repo'yu cloud session'a bağla.
