---
name: project-onboarding
description: Mevcut bir repoyu AurasAgents çalışma sistemine bağlar; AGENTS.md, capability profilleri, issue form ve evidence CI iskeletini kurar. Yeni proje sisteme alınırken (proje başına bir kez) kullan. Günlük geliştirme işinde kullanma.
---

# project-onboarding

## Prosedür

1. Repoyu keşfet: dil/framework, test komutu, build komutu, mevcut CI,
   riskli path'ler (auth, ödeme, migration, secret dosyaları).
2. `AGENTS.md` üret: bu repodaki kök şablonu temel al; risk tablosunun
   path kurallarını REPOYA ÖZGÜ doldur (genel bırakma).
3. Motor adapter'ı: `CLAUDE.md` = `@AGENTS.md` + repo-özel komutlar
   (test/lint/build/start).
4. `.agents/capability-profiles/` üç profili kopyala; tool/network alanlarını
   repo gerçeğine göre daralt.
5. `.github/ISSUE_TEMPLATE/work-contract.yml` kopyala.
6. `.github/workflows/evidence.yml` kur; `checks` listesine repoya özgü
   gerçek komutları yaz (typecheck/lint/test/build).
7. Branch protection gereksinimlerini README'ye not düş (required checks:
   evidence). Bu ayar GitHub arayüzünden/`gh api` ile yapılır.
8. Doğrula: `python3 bin/validate.py` eşdeğeri kontrolleri koş; ilk mikro PR
   ile CI'ın evidence.json ürettiğini kanıtla.

## Gotcha'lar

- Var olan CI'ı silme/yeniden yazma — evidence job'ını YANINA ekle.
- Manifest benzeri eski yapılandırma varsa (ör. Agent Ofis projects/*.yml)
  bilgiyi mekanizma-mekanizmaya taşı: forbidden→hook/deny kuralı,
  conventions→AGENTS.md, routing→profil. Düz metne kopyalayıp geçme.
- Onboarding tek PR'dır; repo koduna davranış değişikliği karıştırma.

## Referanslar

- `references/onboarding-checklist.md` — keşif, AGENTS.md uyarlama, CI
  entegrasyonu, Agent Ofis göçü ve doğrulama derin listesi.

## Eval

`eval/cases.md` — temsili vakalar (biri negatif: bağlı projede tetiklenmemeli).
Onboarding sonrası ölçüt: yeni cihazdan yalnız login ile contract'lı iş
başlatılıp doğrulanmış PR alınabiliyor mu (tasarım Aşama 1 ölçütü).
