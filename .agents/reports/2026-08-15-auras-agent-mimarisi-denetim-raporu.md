# AURAS skills, agent ve context-engineering mimarisi denetim raporu

**Rapor tarihi:** 15 Ağustos 2026  
**Denetlenen commit:** `1224e7178119f4f708c701ac2a38f1d2d3dbe5ac`  
**Denetlenen dal:** `feat/auras-son-surumden-kurar`  
**Denetim türü:** Bağımsız mimari, güvenlik, context ve operasyon denetimi  
**Karar:** **Güçlü temel, önemli iyileştirmeler gerekli**  
**Puan:** **74/100**

## TL;DR

AURAS'ın mevcut skills ve agent mimarisi; kanonik talimat otoritesi, standart
Agent Skills düzeni, ADR'lar, 472 test, secret/PII taraması, kalite ratchet'i ve
yerel kapıların sınırlarını dürüstçe açıklaması sayesinde sıradan agent
konfigürasyonlarının belirgin biçimde üzerindedir. Bununla birlikte capability
profillerindeki tool/ağ/dosya sistemi sınırları fiilen uygulanmıyor, remote
required check etkin değil ve yazılı `deny` risk sözleşmesi gerçek risk motorunda
tam karşılık bulmuyor. Öneri: önce güven sınırlarını mekanik olarak uygula,
ardından contract→risk→evidence zincirini kapat ve gerçek görevlerde routing,
token ve rework metriklerini ölç.

## 1. Kapsam ve yöntem

Denetim aşağıdaki alanları kapsadı:

- `AGENTS.md`, `CLAUDE.md`, `.agents/skills/**`, capability profilleri ve
  routing tablosu.
- Claude hook/rule ayarları, pre-push ve CI kapıları.
- Risk sınıflandırması, evidence üretimi ve bağımsız review mekanizması.
- Runtime event kaydı, Stop kapısı, memory ve çoklu oturum davranışı.
- Test, kalite, secret/PII ve kernel senkron mekanizmaları.
- Claude Code, OpenAI Codex, GitHub Copilot ve MCP taşınabilirliği.

Yerel kod ve belgeler commit
`1224e7178119f4f708c701ac2a38f1d2d3dbe5ac` üzerinden incelendi. Güncel platform
iddialarında yalnız üretici veya standart kuruluşunun birincil dokümantasyonu
kullanıldı; web kaynaklarına erişim tarihi 15 Ağustos 2026'dır.

Çalıştırılan doğrulamalar:

- `python3 bin/validate.py` — geçti.
- `python3 -m unittest discover -s tests -q` — 472 test geçti.
- Secret taraması — 118 dosya temiz.
- Kişisel veri taraması — 118 dosya temiz.
- Denetim öncesi çalışma ağacı temizdi.

## 2. Yönetici kararı

**Güçlü temel, önemli iyileştirmeler gerekli.** — **[yorum]**

AURAS'ın mimari omurgası doğru yönde: kanonik otorite açık, skill'ler progressive
disclosure ile yükleniyor, doğrulayıcıların kapıya bağlanması test ediliyor ve
yerel guard'lar güvenlik sınırıymış gibi pazarlanmıyor (`AGENTS.md:1-5`,
`AGENTS.md:69-81`, `AGENTS.md:163-185`). — **doğrulanmış**

Ancak production güvenilirliği bakımından üç bloklayıcı açıklık vardır:
capability profil izinleri yalnız beyan/şema düzeyindedir, remote required check
yoktur ve `deny` risk politikasının veri silme/prod migration/permission widening
kısmı kodda uygulanmamıştır (`.agents/capability-profiles/code-change.yml:19-25`,
`.claude/settings.json:1-92`, `AGENTS.md:50-59`, `bin/risk.py:14-35`). —
**doğrulanmış**

## 3. Puan kartı

| Alan | Puan | Maksimum | Gerekçe ve kanıt |
|---|---:|---:|---|
| Mimari netlik ve görev ayrımı | 9 | 10 | Kanonik otorite, kapsam ve kapı sınıfları açık (`AGENTS.md:1-22`, `AGENTS.md:163-185`). |
| Agent rolleri ve delegasyon | 6 | 10 | Tek-yazar ve bağımsız worktree ilkesi doğru; ownership/lease/çakışma mekanizması yok (`AGENTS.md:28-30`, `VIBE_CODING_TASARIM_TEMMUZ_2026.md:57-65`). |
| Skill yapısı ve tetikleme | 9 | 12 | Agent Skills standardı ve profil doğrulaması iyi; semantik misroute vakaları var (`.agents/routing.yml:77-203`, `bin/route.py:235-323`). |
| Context ve token ekonomisi | 7 | 10 | Progressive disclosure iyi; her prompt'taki karşılama/memory enjeksiyonu gereksiz sabit yük (`bin/route.py:251-323`, `bin/davranis.py:12-85`). |
| Talimat tutarlılığı | 6 | 8 | Otorite sırası açık; risk, capability enforcement ve kernel senkronunda belge-kod drift'i var (`AGENTS.md:37-48`, `.agents/skills/auras/SKILL.md:24-31`). |
| Planlama, uygulama ve doğrulama | 8 | 10 | Spec-anchored TDD ve CI evidence güçlü; Issue Form→evidence/risk zinciri eksik (`.agents/skills/implement-change/SKILL.md:13-35`, `.github/workflows/evidence.yml:71-98`). |
| Tool, izinler ve güvenlik | 6 | 12 | Secret/PII ve review koruması güçlü; profil izinleri ve remote bütünlük sınırı uygulanmıyor (`bin/hooks/pre-push:121-225`, `AGENTS.md:160-180`). |
| Hata yönetimi ve idempotency | 7 | 8 | Fail-closed review, SHA sabitleme ve tur tavanı iyi; router/Stop bilinçli fail-open (`bin/incele.py:91-152`, `bin/kapi.py:282-317`). |
| Test edilebilirlik ve kalite | 7 | 8 | 472 test ve kalite ratchet'i güçlü; skill eval'leri davranışsal çalıştırılmıyor (`bin/validate.py:58-97`, `docs/decisions/ADR-0004-kod-kalitesi-ratchet.md:18-54`). |
| Bakım ve dokümantasyon | 6 | 7 | ADR ve kapsam dürüstlüğü yüksek; tekrarlı onboarding ve eski memory girdileri bakım yükü (`.agents/routing.yml:257-283`, `bin/hatirla.py:83-160`). |
| Claude, Codex ve MCP uyumluluğu | 3 | 5 | `AGENTS.md` ve `.agents/skills` taşınabilir; işlemsel hook/gate'ler Claude'a özgü. |
| **Toplam** | **74** | **100** | **Kullanılabilir; global standart iddiası erken.** |

## 4. En güçlü 10 özellik

### 4.1 Güven sınırlarının dürüst sınıflandırılması

Yerel Stop hook'u, pre-push, bağımsız review ve CI'ın neyi engelleyemediği açıkça
yazılmıştır (`AGENTS.md:163-185`). Bu, kullanıcıyı mevcut olmayan bir güvenlik
sınırına inanmaktan korur. — **doğrulanmış**

### 4.2 Tek kanonik talimat otoritesi

Motor bağımsız kurallar `AGENTS.md`de tutulur; `CLAUDE.md` ince bir motor
adaptörüdür (`AGENTS.md:1-5`, `CLAUDE.md:1-21`). Politika drift'ini ve aynı
kuralın iki ayrı motor dosyasında farklılaşmasını azaltır. — **doğrulanmış**

### 4.3 Açık Agent Skills standardı ve progressive disclosure

Kanonik skill kaynağı `.agents/skills/`dir ve `.claude/skills` bu dizine
symlink'tir (`AGENTS.md:69-71`, `bin/validate.py:58-97`). Aynı workflow'un iki
kopyasını tutmadan Claude, Codex ve Copilot tarafından keşfedilmesine olanak
verir. — **doğrulanmış**

### 4.4 Spec-anchored TDD akışı

`implement-change`, kabul kriterini teste çevirme, kırmızıyı görme ve doğrulama
adımlarını açık sözleşmeye bağlar (`.agents/skills/implement-change/SKILL.md:13-35`).
CI'daki test-first kontrolü de kaynak değişip test değişmediğinde görünür sonuç
üretir (`.github/workflows/evidence.yml:45-61`). — **doğrulanmış**

### 4.5 Secret ve kişisel verinin ayrı riskler olarak ele alınması

Secret taraması index ve commit geçmişini; PII taraması ise toplu insan verisini
inceler (`bin/hooks/pre-push:121-225`, `.github/workflows/evidence.yml:30-43`).
Bu ayrım, API anahtarı olmayan fakat hassas olan veri dökümlerinin görünmesini
sağlar. — **doğrulanmış**

### 4.6 Test kaybolmasına karşı discovery kapısı

Test dosyasının import'ta kırılması veya discovery deseninden düşmesi başarı
olarak yorumlanmaz (`AGENTS.md:123-135`). Kırmızı test kadar sessizce eksilen
testin de risk olduğu doğru biçimde mekanikleştirilmiştir. — **doğrulanmış**

### 4.7 Fail-closed ve SHA'ya sabitlenmiş review

Ayrıştırılamayan model hükmü temiz sayılmaz; merge komutu incelenen head SHA'ya
sabitlenir (`bin/incele.py:91-116`). Böylece inceleme sonrasında dala eklenen
commit otomatik olarak aynı hükmü devralmaz. — **doğrulanmış**

### 4.8 Sonlu review döngüsü

Tur tavanı, değişmemiş dal koruması ve artımlı inceleme review-fix-review
döngüsünün sınırsız büyümesini engeller (`AGENTS.md:104-116`,
`bin/incele.py:127-149`). — **doğrulanmış**

### 4.9 Kod kalitesi ratchet'i

Mevcut teknik borç kabul edilir, ancak dosya/fonksiyon boyutu, branch ve borç
işaretlerinin büyümesi bloklanır
(`docs/decisions/ADR-0004-kod-kalitesi-ratchet.md:18-33`). Eski projeler için
uygulanabilir bir geçiş modelidir. — **doğrulanmış**

### 4.10 Çift yönlü kernel senkronu

Kernel kurulumu önce kaynağı ileri sarmayı, overwrite kararında kanonik git
geçmişini ve ters yönde reviewed geri taşımayı kullanır
(`docs/decisions/ADR-0002-kernel-senkronu-cift-yonlu.md:9-36`). Eski motorun
bağlı projeyi güncelmiş gibi ezmesi riskini azaltır. — **doğrulanmış**

## 5. Sorunlar ve riskler

### 5.1 P0 — Capability profilleri uygulanmış güvenlik sınırı değil

**Problem:** Capability YAML'larındaki `filesystem`, `commands` ve `network`
alanları doğrulanıyor, fakat Claude ayarlarında bunları zorlayan `permissions`,
sandbox veya `PreToolUse` politikası yoktur
(`.agents/capability-profiles/code-change.yml:19-25`,
`.claude/settings.json:1-92`, `bin/validate.py:100-128`). — **doğrulanmış**

**Etki:** “Research read-only” veya “yalnız api.github.com” gibi sınırlar gerçek
client/OS sınırı değil, model talimatıdır. Prompt injection veya model hatasında
profil dışı yazım/ağ erişimi gerçekleşebilir. — **[yorum]**

**Öneri:** Profilleri tek kaynaktan Claude permissions+sandbox+PreToolUse,
Codex `.codex/config.toml`/rules/hooks ve Copilot `.github/hooks` çıktısına
derleyen bir enforcement katmanı kur. CI, her profil için üretilen motor
politikasının güncel olduğunu doğrulasın. — **[yorum]**

**Tahmini efor:** L

### 5.2 P0 — Remote bütünlük sınırı etkin değil

**Problem:** Pre-push `--no-verify` ile, review doğrudan `gh pr merge` ile
atlanabilir; CI `kernel` check'i required değildir (`AGENTS.md:160-180`). —
**doğrulanmış**

**Etki:** Hatalı veya kötü niyetli bir değişiklik evidence ve review yolu
dışından main'e ulaşabilir. — **[yorum]**

**Öneri:** GitHub ruleset/branch protection ile `kernel` check'ini required yap;
direct push ve force-push'ı kapat; insan ve bot kimliklerini aynı kurala bağla.
— **[yorum]**

**Tahmini efor:** S–M

### 5.3 P0 — `deny` risk sözleşmesi kodda eksik

**Problem:** Politika veri silme, prod migration ve permission genişletmeyi
`deny` sayar (`AGENTS.md:50-59`). `bin/risk.py`, secret/credential yollarını
deny ederken `migration` ve `permission`ı yalnız `approval` sayar ve veri silme
aksiyonunu semantik olarak incelemez (`bin/risk.py:14-35`). Issue Form'dan gelen
provisional risk de merge kararında final risk ile birleştirilmez
(`bin/incele.py:160-169`). — **doğrulanmış**

**Etki:** Veri kaybı veya yetki genişletme riski, yazılı politikadan daha düşük
sınıfta sonuçlanabilir. — **[yorum]**

**Öneri:** Tek makine-okur risk sözleşmesi; path + diff-action kuralları;
provisional/final risk için yukarı yönlü `max()` birleşimi; destructive SQL,
prod migration ve permission widening adversarial testleri. — **[yorum]**

**Tahmini efor:** M–L

### 5.4 P1 — Router semantik olarak güvenilir değil

Denetimde aşağıdaki promptlar mevcut kurallarla çalıştırıldı. Sonuçlar aşağıdaki
tabloda gösterilmiştir. — **doğrulanmış**

| Prompt | Mevcut seçim | Beklenen |
|---|---|---|
| `Token maliyetini analiz et` | `security-review` primary | research |
| `Hafıza sistemi nasıl çalışıyor?` | mandatory skill yok | research |
| `MCP entegrasyonunu tasarla` | `designing-interfaces` | architecture/research |
| `Yeni veritabanı şemasını tasarla` | `designing-interfaces` | architecture/code-change |
| `Güvenlik skillini güncelle` | `security-review` primary | `kernel-work` primary |

Bu sonuçlar `token`, `tasarla/tasarım` gibi geniş sözcük tetiklerinden ve soru
cümlelerini mandatory skill'den düşüren niyet kapısından kaynaklanır
(`.agents/routing.yml:120-168`, `bin/secim.py:24-51`). — **doğrulanmış**

**Etki:** Yanlış workflow, gereksiz bağlam ve kritik skill'in atlanması. — **[yorum]**

**Öneri:** En az 100 pozitif/negatif/adversarial prompt içeren executable eval;
domain-aware tokenization; “tasarım=UI” varsayımının kaldırılması; soru
short-circuit'i yerine intent skoru. — **[yorum]**

**Tahmini efor:** M

### 5.5 P1 — Evidence sözleşmesi uçtan uca bağlı değil

Workflow, task class'ı `code-change` veya `micro` olarak üretir; Issue Form'daki
research/incident sınıfını, riski, kabul kriteri eşlemesini, skill/model bilgisini,
digest ve approvals kayıtlarını evidence'a taşımaz
(`.github/workflows/evidence.yml:71-98`, `schemas/evidence.schema.json:6-60`).
`make_evidence.py` bu alanların bir kısmını destekler, fakat workflow argüman
vermez (`bin/make_evidence.py:53-66`, `bin/make_evidence.py:93-113`). —
**doğrulanmış**

**Etki:** `evidence.json`, tasarım belgesinin öngördüğü karar ve provenance
kaydından daha zayıftır. — **[yorum]**

**Öneri:** Issue body'yi şemalı parse et; contract class/risk/kriterleri ve
model/skill/digest/approval alanlarını artifact'a taşı; kritik alanları schema'da
required yap. — **[yorum]**

**Tahmini efor:** M

### 5.6 P1 — Review prompt-injection ve portability sınırı zayıf

`bin/codex-review.sh`, ham diff'i model prompt'una gömer ve kullanıcı-global
`$HOME/.claude/skills/codex-debate/bin/ask-codex.sh` bridge'ine bağlıdır
(`bin/codex-review.sh:13-30`, `bin/codex-review.sh:64-77`). Injection regex'i
yalnız bilinen doğal dil kalıplarını yakalar (`bin/risk.py:38-53`). —
**doğrulanmış**

**Etki:** Obfuscation veya yeni bir dil kalıbı review hükmünü etkileyebilir;
bridge olmayan makinede workflow çalışmaz. — **[yorum]**

**Öneri:** Diff'i açıkça untrusted ayrı veri alanında taşı; structured output
schema kullan; reviewer sürümü/modelini evidence'a yaz; bridge'i belgeli repo
bağımlılığı veya plugin yap. — **[yorum]**

**Tahmini efor:** M

### 5.7 P1 — Çoklu ajan koordinasyonu politika düzeyinde

Tek-yazar ve bağımsız worktree ilkesi belgelenmiştir, ancak file ownership,
lease, dependency graph, overlap preflight veya merge queue mekanizması bulunmaz
(`AGENTS.md:28-30`, `VIBE_CODING_TASARIM_TEMMUZ_2026.md:57-65`). —
**doğrulanmış**

**Etki:** İki ajan ayrı worktree'lerde aynı mantıksal alana çakışan değişiklik
yapabilir; Git yalnız text conflict'i yakalar, semantik conflict'i yakalamaz.
— **[yorum]**

**Öneri:** Task manifestinde owner, path/glob, base SHA, dependency ve lease;
başlangıçta overlap kontrolü; merge öncesi rebase ve birleşik test. — **[yorum]**

**Tahmini efor:** M–L

### 5.8 P1 — Gerçek görev ölçümü yok

Tasarım 20–30 görevlik pilot ve ölçüm öngörür
(`VIBE_CODING_TASARIM_TEMMUZ_2026.md:188-199`,
`VIBE_CODING_TASARIM_TEMMUZ_2026.md:254-267`). Runtime log ise gitignore'lu,
silinebilir ve kalıcı karar kaynağı değildir (`bin/run_event.py:13-21`). —
**doğrulanmış**

**Etki:** Route precision, first-pass success, rework, token ve escaped defect
iddiaları ölçülememektedir. — **[yorum]**

**Öneri:** En az 20–30 temsili görevde route precision/recall, first-pass
success, rework, time-to-evidence, token ve escaped defect ölç. — **[yorum]**

**Tahmini efor:** M

### 5.9 P1 — CI supply-chain girdileri sabitlenmemiş

Workflow `actions/checkout@v4`, `actions/upload-artifact@v4` ve sürüm
sabitlenmemiş `pyyaml` kurulumunu kullanır (`.github/workflows/evidence.yml:18-23`,
`.github/workflows/evidence.yml:100-104`). — **doğrulanmış**

**Etki:** Upstream sürüm değişikliği veya compromise deterministik evidence
üretimini etkileyebilir. — **[yorum]**

**Öneri:** Action'ları tam commit SHA'ya, PyYAML'ı hash'li sürüme sabitle;
güncellemeyi Dependabot/Renovate PR'larına bağla. — **[yorum]**

**Tahmini efor:** S

### 5.10 P2 — Her prompt'ta sabit context yükü

Router slash-dışı her prompt'a karşılama davranışı ve geçmiş bloğu ekler
(`bin/route.py:257-266`). Üç temsili prompt'ta ölçülen ek çıktı 1.996–2.401
karakter ve 288–331 kelimedir. — **doğrulanmış**

**Etki:** Basit takip sorularında dahi yaklaşık 500–600 token ek yük ve talimat
dikkat dağılması. — **[yorum]**

**Öneri:** Router yalnız kısa class/skill/policy ID'si üretsin; karşılama ve
memory gerçek tetik eşiği geçildiğinde yüklensin. — **[yorum]**

**Tahmini efor:** M

### 5.11 P2 — Runtime olayları session-aware okunmuyor

Event şeması `session` alanını kabul eder (`bin/run_event.py:36-39`), fakat
`durum.py` olayları son global route üzerinden gruplar ve session filtresi
kullanmaz (`bin/durum.py:60-80`). Stop kapısı da son global stop'tan sonraki
olayları “bu tur” sayar (`bin/kapi.py:65-77`). — **doğrulanmış**

**Etki:** Aynı worktree'de eşzamanlı iki oturum birbirinin skill/test kanıtını
sahiplenebilir. — **[yorum]**

**Öneri:** Session başına event dosyası veya zorunlu session filtresi; append
için dosya kilidi. — **[yorum]**

**Tahmini efor:** M

### 5.12 P2 — Bash tabanlı dosya yazımları Stop guard'dan kaçabilir

Edit olayı yalnız `Edit|Write|NotebookEdit` tool'larında yazılır
(`.claude/settings.json:26-34`). `kapi.py` kaynak değişikliklerini event'teki
edit yollarından çıkarır (`bin/kapi.py:146-167`). Shell scripti, `sed -i` veya
redirection ile yazım edit olayı üretmeyebilir. — **doğrulanmış**

**Etki:** Kod değiştiği hâlde Stop kapısı test/UI/security yükümlülüğünü
görmeyebilir. — **[yorum]**

**Öneri:** Turn başı/sonu git diff snapshot'ı; doğrulamayı yalnız tool olayına
değil gerçek çalışma ağacı farkına bağla. — **[yorum]**

**Tahmini efor:** M

### 5.13 P2 — Memory güncellik seçimi zayıf

`hatirla.py`, ADR, git subject ve raporlardaki kaba anahtar eşleşmelerinden ilk
satırları döndürür (`bin/hatirla.py:83-160`). Superseded karar veya eski rapor
güncel karardan önce eşleşebilir. — **doğrulanmış**

**Etki:** Agent doğru geçmişi hatırladığına inanırken eski bir ara bulguyu
yeniden bağlama sokabilir. — **[yorum]**

**Öneri:** Kaynak otoritesi, tarih ve `superseded_by` metadata'sı; ADR ve son
reviewed kararı önceleme. — **[yorum]**

**Tahmini efor:** M

### 5.14 P2 — Skill eval'leri davranışsal değil

`validate.py`, eval klasörü ve başlık varlığını kontrol eder; skill'in doğru
prompt'ta aktive olup doğru çıktıyı verdiğini çalıştırmaz (`bin/validate.py:58-97`).
— **doğrulanmış**

**Etki:** Eval dosyası mevcut olduğu için yeşil görünen skill gerçek host/modelde
yanlış tetiklenebilir. — **[yorum]**

**Öneri:** Pozitif, negatif, eksik girdi ve adversarial vakaları çalıştıran
activation/output contract harness. — **[yorum]**

**Tahmini efor:** M

### 5.15 P3 — Düşük önem düzeltmeleri

- `auras/SKILL.md`, overwrite kararında manifest'i otorite gibi anlatırken
  ADR-0002 git geçmişini otorite yapmıştır
  (`.agents/skills/auras/SKILL.md:24-31`,
  `docs/decisions/ADR-0002-kernel-senkronu-cift-yonlu.md:23-30`). —
  **doğrulanmış**, efor S.
- `project-onboarding`, routing tablosunda `auras` tarafından kapsanan tekrar
  olarak işaretlidir (`.agents/routing.yml:271-279`). — **doğrulanmış**, efor S.
- Test koşusunda `tests/test_kernel_dosyalari.py:90` kaynaklı unclosed-file
  `ResourceWarning` çıktıları görüldü; test sonucu yine 0'dı. — **doğrulanmış**,
  efor S.
- Kalite ratchet'i duplication, type, lint, a11y ve performansı ölçmez;
  kapsam ADR'da dürüstçe sınırlandırılmıştır
  (`docs/decisions/ADR-0004-kod-kalitesi-ratchet.md:46-54`). —
  **doğrulanmış**, efor M.

## 6. Çelişki ve tekrar matrisi

| Talimat A | Talimat B | Sorun | Korunması gereken |
|---|---|---|---|
| `AGENTS.md:72-74`: profil tool/ağ izin kümesini belirler | `.claude/settings.json:1-92`: permissions/sandbox/PreToolUse yok | Enforcement yalnız beyan | AGENTS sözleşmesi; motor adaptörlerinde uygulanmalı |
| `AGENTS.md:55-58`: data deletion/prod migration/permission widening deny | `bin/risk.py:16-35`: migration/permission approval | Risk sınıfı aşağı düşüyor | AGENTS; risk motoru düzeltilmeli |
| `.agents/capability-profiles/code-change.yml:30-33`: provisional issue + final diff | `bin/incele.py:160-169`: yalnız değişen yollar | Issue riski merge kararına girmiyor | Profil sözleşmesi |
| `.agents/skills/auras/SKILL.md:24-31`: manifest kullanıcı değişimini belirler | `ADR-0002:23-30`: manifest otorite değil | Eski skill anlatımı | ADR-0002 |
| `VIBE_CODING_TASARIM_TEMMUZ_2026.md:149-170`: zengin evidence | `.github/workflows/evidence.yml:88-98`: temel checks/hardcoded class | Tasarım uygulanmamış | Tasarım sözleşmesi |
| `AGENTS.md:1-5`: motor bağımsız tek doğruluk kaynağı | `.claude/settings.json`: işlemsel mekanizmalar Claude'a özel | Politika taşınabilir, enforcement değil | Kanonik politika + üretilmiş motor adaptörleri |
| `aurasprime/SKILL.md:17-35`: basit/takip işinde tören yok | `bin/route.py:257-266`: her slash-dışı prompt'a davranış | Negatif trigger context maliyetini önlemiyor | Router ön elemesi |
| `project-onboarding` | `.agents/routing.yml:271-279`: `auras` kapsıyor | Tekrarlı workflow | `auras`; diğeri alias/deprecated |

## 7. Eksik mekanizmalar

### 7.1 Dünya standardı için gerekli

1. Motorlar tarafından gerçekten uygulanan capability enforcement. — **[yorum]**
2. Remote required check ve protected merge yolu. — **[yorum]**
3. Action-aware, tek kaynaklı risk motoru. — **[yorum]**
4. Contract→risk→evidence→review→merge uçtan uca testi. — **[yorum]**
5. Router ve skill activation için executable adversarial eval seti. — **[yorum]**
6. Session-isolated ve kilitli event/kanıt kaydı. — **[yorum]**
7. Çoklu ajan file ownership/lease/overlap kontrolü. — **[yorum]**
8. Review girdisi için structured untrusted-data sınırı. — **[yorum]**
9. Tam sabitlenmiş CI dependency ve action SHA'ları. — **[yorum]**
10. Gerçek görevlerden route, rework, token ve defect ölçümü. — **[yorum]**

### 7.2 Yararlı fakat zorunlu olmayanlar

- Merkezi control plane veya agent organizasyon şeması. — **[yorum]**
- Vector database tabanlı harici hafıza. — **[yorum]**
- Her disiplin için ayrı persona/subagent. — **[yorum]**
- Genel amaçlı MCP sunucuları. — **[yorum]**
- Canlı operasyon dashboard'u. — **[yorum]**
- Her yaşam döngüsü aşamasında zorunlu kapı. — **[yorum]**

İkinci grubun eklenmesi tek başına kalite kanıtı değildir. Önce ilk gruptaki
güven ve ölçüm açıklıkları kapatılmalıdır. — **[yorum]**

## 8. Claude Code, Codex, Copilot ve MCP uyumluluğu

### 8.1 Claude Code

**Değerlendirme:** İyi workflow uyumu, eksik enforcement. — **[yorum]**

Claude `.claude/settings.json`, path-scoped `.claude/rules`, skill symlink'i ve
hook event'lerini kullanabilir. Anthropic'in güncel dokümantasyonu `CLAUDE.md`
talimatlarının hard enforcement olmadığını; erişim sınırları için permissions
ve OS-level sandbox gerektiğini belirtir
(https://code.claude.com/docs/en/memory,
https://code.claude.com/docs/en/permissions,
https://code.claude.com/docs/en/hooks-guide; erişim: 2026-08-15). AURAS'ın
proje ayarlarında bu katmanlar bulunmaz (`.claude/settings.json:1-92`). —
**doğrulanmış**

Beklenen başarısızlık noktaları — **[yorum]**:

- Profil dışında Bash/Read/Edit/Web/MCP kullanımı mekanik olarak engellenmez. — **[yorum]**
- Eşzamanlı oturumların event'leri karışabilir. — **[yorum]**
- Shell aracılığıyla yazılan dosya Stop guard'da edit görünmeyebilir. — **[yorum]**
- Proje hook'u managed policy değildir ve kullanıcı tarafından kapatılabilir. — **[yorum]**

### 8.2 OpenAI Codex

**Değerlendirme:** Talimat ve skill düzeyinde iyi, işlemsel kapılar düzeyinde
eksik. — **[yorum]**

Codex resmî olarak root/nested `AGENTS.md`, `.agents/skills`, symlink skill
dizinleri ve progressive disclosure'ı destekler
(https://learn.chatgpt.com/docs/agent-configuration/agents-md,
https://learn.chatgpt.com/docs/build-skills; erişim: 2026-08-15). —
**doğrulanmış**

Codex proje hook'larını `.codex/hooks.json` veya `.codex/config.toml` üzerinden
yükler; `.claude/settings.json` Codex hook konfigürasyonu değildir
(https://learn.chatgpt.com/docs/hooks,
https://learn.chatgpt.com/docs/config-file/config-advanced; erişim: 2026-08-15).
Repo içinde eşdeğer `.codex` hook adaptörü bulunmamıştır. — **doğrulanmış**

Beklenen başarısızlık noktaları — **[yorum]**:

- Skill'ler görünürken zorunlu router seçimi ve Stop kapısı çalışmayabilir. — **[yorum]**
- Capability profilleri Codex sandbox/rules/config'e çevrilmez. — **[yorum]**
- `codex-review.sh` kullanıcı-global Claude bridge'i olmayan ortamda çalışmaz. — **[yorum]**
- Codex tool/test kanıtı aynı event şemasına otomatik düşmez. — **[yorum]**

### 8.3 GitHub Copilot ve diğer ajanlar

GitHub Copilot `.agents/skills`i tanır; deterministik repository hook'ları için
`.github/hooks/*.json` kullanır
(https://docs.github.com/en/copilot/reference/customization-cheat-sheet;
erişim: 2026-08-15). Repo bu adaptörü taşımaz. Instruction ve skill
taşınabilirliği vardır; enforcement taşınabilirliği yoktur. — **doğrulanmış**

### 8.4 MCP ve harici tool entegrasyonu

Skills ile tool workflow'unu ayırma yaklaşımı MCP'ye uygundur. Ancak repoda
checked-in MCP server allowlist'i, tool bazlı approval, least-privilege scope,
timeout, required-server davranışı veya auth yaşam döngüsü bulunmamıştır. —
**doğrulanmış**

Codex bu politikaları server/tool bazında destekler
(https://learn.chatgpt.com/docs/extend/mcp; erişim: 2026-08-15). Güncel MCP
spesifikasyonu authorization issuer doğrulama, credential binding, protected
resource metadata ve minimum scope ilkelerine önem verir
(https://blog.modelcontextprotocol.io/posts/2026-07-28/,
https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization;
erişim: 2026-08-15). — **doğrulanmış**

MCP bugün AURAS için zorunlu değildir. Eklendiğinde skill içindeki kullanım
talimatı güvenlik sınırı sayılmamalı; auth, authorization ve approval server/client
politikasında zorlanmalıdır. — **[yorum]**

## 9. Sadeleştirme analizi

### 9.1 Silinebilecek veya deprecated yapılabilecek

- `project-onboarding`, `auras` ile birleştirilmeli veya geriye uyumluluk alias'ı
  olarak bırakılmalı (`.agents/routing.yml:271-279`).
- Eski raporlar silinmek yerine `superseded_by` metadata'sı almalı ve varsayılan
  recall'dan çıkarılmalı (`bin/hatirla.py:83-160`).
- `auras/SKILL.md` içindeki manifest-otoritesi anlatımı kaldırılmalı. — **[yorum]**

### 9.2 Birleştirilmesi gereken kurallar

- Risk politikası `AGENTS.md`, profil YAML ve `risk.py` arasında üç ayrı kaynak
  olmamalı. — **[yorum]**
- Router metadata'sı ve capability membership tek registry'den beslenmeli. — **[yorum]**
- Claude/Codex/Copilot hook adaptörleri ortak manifestten üretilmeli. — **[yorum]**

### 9.3 Her istekte yüklenmemesi gereken içerikler

- Uzun AurasPrime karşılama metni. — **[yorum]**
- Geçmiş raporlardan ham eşleşen cümleler. — **[yorum]**
- Owner/objection/response header talimatlarının ayrıntılı açıklamaları. — **[yorum]**
- İlgisiz review-loop, kernel-sync ve lifecycle geçmişi. — **[yorum]**

### 9.4 Skill/reference içine taşınması gerekenler

- `AGENTS.md`deki review döngüsü ölçüm geçmişi → review/kernel referansı. — **[yorum]**
- Secret/PII muafiyet örnekleri → `security-review/references`. — **[yorum]**
- Test discovery arıza hikâyesi → `implement-change/references`. — **[yorum]**
- Kernel sync ayrıntıları → `auras`/`kernel-work` referansı. — **[yorum]**

`AGENTS.md` 200 satırdır. Anthropic 200 satır üzerindeki instruction dosyalarının
context ve adherence maliyetini artırabileceğini belirtir
(https://code.claude.com/docs/en/memory; erişim: 2026-08-15). Codex'in 32 KiB
varsayılan proje talimat sınırının altında olsa da dosyanın büyütülmemesi ve
normatif çekirdeğin yaklaşık 100–130 satıra indirilmesi önerilir. —
**doğrulanmış kaynak + denetçi önerisi**

Somut hedef: router enjeksiyonunu %60–75, always-loaded kanonik metni %25–35
azaltmak; yalnız seçilen skill'in ayrıntısını yüklemek. — **[yorum]**

## 10. Öncelikli iyileştirme planı

### 10.1 İlk 48 saat

| İş | Etki | Efor | Bağımlılık |
|---|---|---:|---|
| `kernel` check'ini GitHub ruleset'te required yap | Kritik bypass yolunu kapatır | S | Repo admin yetkisi |
| Migration/veri silme/permission widening için gerçek deny testleri | Veri kaybı riskini azaltır | M | Risk sözleşmesi |
| Capability profillerinin advisory durumunu belgede düzelt | Yanlış güveni keser | S | Yok |
| Actions ve PyYAML sürümlerini sabitle | Supply-chain deterministikliği | S | Seçilecek SHA/sürüm |
| `auras` anlatımını ADR-0002 ile eşitle | Talimat çatışmasını kaldırır | S | Yok |
| Bilinen adversarial promptları router regression testi yap | Misroute tekrarını önler | S–M | Yok |

### 10.2 İlk 2 hafta

| İş | Etki | Efor | Bağımlılık |
|---|---|---:|---|
| Tek risk policy + provisional/final birleşimi | Politika-kod eşitliği | L | Issue parser |
| Issue Form→evidence entegrasyonu | Denetlenebilir contract | M | Schema kararı |
| Claude permissions/sandbox/PreToolUse | Capability enforcement | M–L | Profil compiler |
| Codex ve Copilot hook adaptörleri | Motorlar arası eşdeğerlik | L | Ortak hook manifesti |
| Session-isolated event log ve file lock | Eşzamanlı güvenilirlik | M | Event schema v2 |
| Structured review bridge | Injection ve portability | M | Reviewer interface |
| Router executable eval harness | Precision/recall ölçümü | M | Etiketli corpus |

### 10.3 İlk 1–2 ay

| İş | Etki | Efor | Bağımlılık |
|---|---|---:|---|
| 20–30 gerçek görevlik pilot | Dünya standardı iddiasını ölçer | L | Telemetri şeması |
| Multi-agent ownership/lease/overlap | Paralel yazma riskini yönetir | L | Session/task identity |
| Skill activation/output eval'leri | Skill kalitesini davranışta ölçer | L | Eval runner |
| Context bütçesi regression testi | Token maliyetini kontrol eder | M | Prompt snapshot'ları |
| Evidence provenance v2 | Audit ve reproducibility | M–L | Schema v2 |
| Motorlar arası conformance suite | Adaptör drift'ini yakalar | L | Adaptörlerin tamamlanması |

## 11. Adversarial kontrol

| Senaryo | Mevcut beklenen davranış | Başarısızlık ihtimali | Gerekli koruma |
|---|---|---|---|
| Çelişen risk talimatları | AGENTS teoride üstün; motor `risk.py`yi uygular | Yüksek | Tek risk kaynağı ve consistency test |
| `Token maliyetini analiz et` | Security review primary olur | Yüksek | Domain-aware router eval'i |
| Basit takipte AurasPrime töreni | Modelin töreni atlaması beklenir | Orta | Router seviyesinde takip/basit iş eşiği |
| İki ajan aynı dosyayı ayrı worktree'de değiştirir | Git text conflict yakalayabilir | Yüksek | Ownership lease ve overlap preflight |
| Router veya Stop hook'u çöker | Fail-open, iş devam eder | Orta | Hook health kanıtı; kritik policy fail-closed |
| Eksik kullanıcı bilgisiyle destructive işlem | Skill'in durması beklenir | Orta | Completeness check ve zorunlu approval |
| Diff içinde prompt injection | Bilinen regex eşleşirse insan kararına düşer | Orta | Untrusted-data channel ve structured output |
| Uzun görevde context compact olur | Kök talimat tekrar yüklenebilir | Orta | Active-contract checkpoint ve freshness |
| Test sonucu pipe ile maskelenir | Bazı kalıplar geçersiz kanıt sayılır | Orta | Doğrudan process exit/artifact |
| Kernel sync kullanıcı değişimini ezer | ADR-0002 git geçmişiyle korumayı amaçlar | Düşük–Orta | Dry-run, provenance ve three-way merge |
| Aynı worktree'de iki oturum | Ortak event günlüğü kullanılır | Yüksek | Session logu/filtre/kilit |
| Research profili rapor dışı dosya yazar | Profil yazılı olarak read-only; client engellemez | Yüksek | Enforced sandbox/permissions |

## 12. Doğrudan nihai cevaplar

| Soru | Cevap | Gerekçe |
|---|---|---|
| AURAS bugün production kullanımına hazır mı? | **Kısmen** | Kontrollü tek geliştirici akışında evet; yüksek riskte required check/enforcement gerekli. |
| Claude Code profesyonellerine önerilebilir mi? | **Kısmen** | Workflow güçlü; permissions/sandbox ile tamamlanmalı. |
| Codex profesyonellerine önerilebilir mi? | **Kısmen** | AGENTS ve skills iyi; Codex hook/gate adaptörü eksik. |
| Çoklu ajan görevlerinde güvenilir mi? | **Hayır** | İzolasyon ilkesi var, koordinasyon mekanizması yok. |
| Token/context açısından verimli mi? | **Kısmen** | Progressive disclosure iyi; router sabit yükü pahalı. |
| Güvenlik yaklaşımı yeterli mi? | **Kısmen** | Tarama güçlü; enforcement ve remote boundary eksik. |
| Test ve kalite sistemi yeterli mi? | **Kısmen** | Kod kapıları güçlü; router/skill davranış eval'i eksik. |
| Ağustos 2026 için dünya standartlarında mı? | **Hayır** | Ölçülmüş görev başarısı ve zorunlu güven sınırları yok. |
| Mevcut yapı son hâl kabul edilebilir mi? | **Hayır** | Production-blocking entegrasyon işleri sürüyor. |

## 13. Karar önerisi

**Mevcut puan:** 74/100  
**Önerilen düzeltmeler sonrası potansiyel:** 92/100 — **[yorum]**

En kritik üç değişiklik:

1. Remote required check ve protected merge yolunu etkinleştirmek. — **[yorum]**
2. Capability profillerini her motorun gerçek sandbox/permission/hook
   mekanizmasına bağlamak. — **[yorum]**
3. Risk, contract ve evidence zincirini tek kaynaklı ve uçtan uca test edilmiş
   hâle getirmek. — **[yorum]**

**Nihai hüküm:** AURAS, dünya standartlarına yaklaşan güçlü ve düşünülmüş bir
çekirdektir; fakat güvenlik vaatleri mekanik olarak uygulanıp gerçek görev
metrikleriyle doğrulanmadan production-grade veya son hâl sayılamaz. — **[yorum]**

## 14. Açık sorular

- GitHub branch protection/ruleset'in private-repo planında hangi özelliklerle
  uygulanabileceği repo yöneticisi yetkileriyle doğrulanmalıdır.
- Capability profillerinin Claude, Codex ve Copilot'a tek kaynaktan nasıl
  derleneceği için ayrı bir ADR gereklidir.
- Pilot görev corpus'unun hangi gerçek proje sınıflarını ve risk dağılımını
  temsil edeceği ürün sahibi tarafından belirlenmelidir.
- MCP entegrasyonu eklenirse yetki kapsamı, veri sınıflandırması ve approval
  UX'i ayrı threat model ile kararlaştırılmalıdır.

## 15. Meta — Kaynaklar

### Yerel birincil kaynaklar

- `AGENTS.md`
- `CLAUDE.md`
- `VIBE_CODING_TASARIM_TEMMUZ_2026.md`
- `.agents/routing.yml`
- `.agents/capability-profiles/*.yml`
- `.agents/skills/*/SKILL.md`
- `.claude/settings.json`
- `.github/workflows/evidence.yml`
- `bin/route.py`, `bin/secim.py`, `bin/risk.py`, `bin/incele.py`
- `bin/kapi.py`, `bin/run_event.py`, `bin/durum.py`, `bin/hatirla.py`
- `bin/validate.py`, `bin/make_evidence.py`, `bin/hooks/pre-push`
- `docs/decisions/ADR-0001..0004`
- `docs/yasam-dongusu-kapsami.md`

### Resmî dış kaynaklar

- Anthropic, Claude Code memory ve talimatlar:
  https://code.claude.com/docs/en/memory
- Anthropic, permissions:
  https://code.claude.com/docs/en/permissions
- Anthropic, hooks:
  https://code.claude.com/docs/en/hooks-guide
- OpenAI, Codex `AGENTS.md`:
  https://learn.chatgpt.com/docs/agent-configuration/agents-md
- OpenAI, Codex skills:
  https://learn.chatgpt.com/docs/build-skills
- OpenAI, Codex hooks:
  https://learn.chatgpt.com/docs/hooks
- OpenAI, Codex MCP:
  https://learn.chatgpt.com/docs/extend/mcp
- GitHub Copilot customization:
  https://docs.github.com/en/copilot/reference/customization-cheat-sheet
- Model Context Protocol, 2026-07-28 değişiklikleri:
  https://blog.modelcontextprotocol.io/posts/2026-07-28/
- Model Context Protocol authorization:
  https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
