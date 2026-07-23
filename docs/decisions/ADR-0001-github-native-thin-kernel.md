# ADR-0001 — GitHub-native thin kernel

**Tarih:** 2026-07-24
**Durum:** Kabul edildi (Codex ile 2 münazara + 2 el sıkışma)
**Bağlam belgeleri:** `AURASAGENTS_PRODUCT_VISION.md` (v0.1), `VIBE_CODING_TASARIM_TEMMUZ_2026.md`

## Karar

Vizyondaki control plane / Capability Resolver / Evidence Ledger **servis
olarak yazılmaz**. Yerine GitHub üzerinde çalışan ince sözleşme çekirdeği:

1. Work Contract = GitHub Issue Form (`.github/ISSUE_TEMPLATE/work-contract.yml`)
2. Capability seçimi = 3 statik profil (`.agents/capability-profiles/`) +
   model'in profil-içi native seçimi
3. Kanıt = CI'ın ürettiği `evidence.json` (`schemas/evidence.schema.json`,
   sha256 digest'li) — GitHub Checks/artifacts içinde saklanır
4. Enforcement = üç deterministik sonuç (auto / approval / deny+break-glass);
   hook + branch protection + required checks ile
5. Hafıza = Git kanonik (`AGENTS.md` + `docs/decisions/`); auto-memory
   disposable; `CLAUDE.md` yalnız adapter

## Gerekçe

- 2026 saha konsensüsü: erken control-plane israf; ama şemasızlık metrikleri
  imkânsız kılar ("motor yazma, şema yaz" — Codex mutabakatı 1).
- Hibrit karar (Codex mutabakatı 2): bu sistem Agent Ofis'in yerine değil
  üzerine kurulur; nihai kıyas 20–30 görevlik pilot metriğiyle yapılır.

## Sonuçlar

- Control plane ancak evidence.json metrikleri ihtiyacı kanıtlarsa gündeme gelir.
- İkinci motor (Codex) aynı `.agents/skills/` kaynağını okuyabilmelidir.
- Kernel'in kendisi `bin/validate.py` conformance testleriyle korunur.
