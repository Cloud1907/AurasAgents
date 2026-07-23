# AurasAgents

Tek kişilik kurucu için kanıt-temelli agent çalışma sistemi — GitHub-native
thin kernel. Tasarım: [VIBE_CODING_TASARIM_TEMMUZ_2026.md](VIBE_CODING_TASARIM_TEMMUZ_2026.md) ·
Vizyon: [AURASAGENTS_PRODUCT_VISION.md](AURASAGENTS_PRODUCT_VISION.md) ·
Kararlar: [docs/decisions/](docs/decisions/)

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

## Kurulum sonrası (GitHub tarafı — bir kez)

1. Repo'yu GitHub'a push'la.
2. Branch protection (main): "Require status checks" → `kernel` job'ı zorunlu.
3. Codex Review app'ini repoya bağla (Review all PRs).
4. claude.ai/code üzerinden repo'yu cloud session'a bağla.
