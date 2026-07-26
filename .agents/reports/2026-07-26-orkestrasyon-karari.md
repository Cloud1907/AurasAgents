# Orkestrasyon katmanı kararı — ağırlıklı analiz

| Alan | Değer |
|---|---|
| Tarih | 2026-07-26 |
| Sınıf | research |
| Karar sahibi | kullanıcı |
| Soru | "agent ofis daha iyiydi, iş dağıtıyordu" boşluğu nasıl kapatılmalı: orkestrasyonu AurasAgents'a taşımak mı, Agent Ofis'e devretmek mi, yalnız router'ı düzeltmek mi? |

## TL;DR

Boşluk gerçek: AurasAgents'ta iş dağıtımı ve görünür durum **hiç yazılmadı**;
bugüne kadar kurulan katman kural + kanıt + yönlendirme. Ancak "rolleri
AurasAgents içinde çoğalt" seçeneği tasarım sözleşmesiyle doğrudan çelişiyor —
sözleşme rol tiyatrosunu açıkça reddediyor ve orkestrasyonu Agent Ofis'te
bırakıyor. Önerilen yol, sözleşmeye uyan ince bir katman: **görünür run ledger
+ sözleşmenin izin verdiği iki subagent kullanımı + router'ın çok-katmanlı işi
Agent Ofis'e devretmesi** (ağırlıklı skor 86/100; en yakın alternatif 73).

## Bulgular

### B1 — Rol tiyatrosu sözleşmede yasak (doğrulanmış)
`VIBE_CODING_TASARIM_TEMMUZ_2026.md:62` (§2): "Rol tiyatrosu yok:
PM-agent/architect-agent/QA-agent'ın aynı işi paylaşması israf (Cognition:
'Don't Build Multi-Agents'). Subagent yalnız iki meşru işte: (a) context
izolasyonu (araştırma/keşif), (b) bağımsız doğrulama (fresh-context review).
Paralellik yalnız gerçekten bağımsız işlerde (git worktree)."
Çapraz doğrulama: `AGENTS.md:18` — "Tek yazar. Aynı iş roller arasında
bölünmez; paralellik yalnız bağımsız işlerde (ayrı worktree/session)."
DÜZELTME (Codex turu): bu ikisi **bağımsız kaynak değildir** — aynı karar
zincirinin çıktısı; yalnız kanonik tutarlılık gösterir (kaynak yankısı kuralı,
research-with-evidence skill'i).

### B2 — Agent Ofis ilişkisi zaten karara bağlanmış (doğrulanmış)
`VIBE_CODING_TASARIM_TEMMUZ_2026.md:258` (§12, ikinci Codex mutabakatı, el
sıkışma EVET): "Agent Ofis'in yerine değil, üzerine (hibrit): Agent Ofis kalır:
dashboard, intake, ideation, manifest routing. Üzerine güven katmanı: kalıcı
bilgi Git'e aynalanır; … kritik değişikliklere CI evidence + Codex sinyali."
Yani dashboard/intake/routing Agent Ofis'in, kanıt/kural katmanı
AurasAgents'ın — iş bölümü tasarımın kendisinde.

### B3 — Üstünlük iddiası ölçülmeden karara bağlanamaz (doğrulanmış)
`VIBE_CODING_TASARIM_TEMMUZ_2026.md:264`: "Nihai karar 20–30 gerçek görevlik
pilotta, görev sınıfı bazında metrikle: sonuç oranı, insan dakikası, çevrim
süresi, rollback, ideation kalitesi. 'Yeni sistem kesin daha iyi' iddiası geri
çekildi — kanıt karar verir." Bugün elimizde ne AurasAgents ne Agent Ofis için
bu metrikler var (arama kapsamı: repo kökü, `docs/`, `.agents/` — ölçüm dosyası
yok). Dolayısıyla "hangisi daha iyi" sorusunun kanıtlı cevabı **henüz yok**;
kullanıcının gözlemi geçerli bir sinyal ama ölçüm değil.

### B4 — Rol kadrosu var, AurasAgents'a bağlı değil (doğrulanmış)
`~/.claude/agents/` altında 15 rol tanımı duruyor (tech-lead, backend/frontend/
qa/security/database/devops-engineer, software-architect, code-auditor,
research-analyst, ux-designer, product-strategist, ml-ai, mobile,
sayfa-dokumanci). AurasAgents capability profilleri ise yalnız `skills`,
`tools`, `network`, `evidence_required`, `risk` alanlarını taşıyor
(`.agents/capability-profiles/code-change.yml:1`-`:20`) — **`roles` alanı yok**;
rol kadrosu listesi `~/.claude/agents/` dizin taramasından (doğrulanmış).
Bağlantı kurulmamış.

### B5 — Görünür durum yüzeyi yok (doğrulanmış)
Repoda run/progress/ledger dosyası veya dizini yok (arama: repo kökü ağacı,
`.agents/` altı). Tasarım bunu servis düzeyinde bilinçli reddediyor
(`VIBE_CODING_TASARIM_TEMMUZ_2026.md:29` — "Evidence Ledger (ayrı servis/DB): Servis yapılmaz"), ama
**dosya düzeyinde bir ilerleme kaydını yasaklamıyor**; kanonik katman zaten
"progress dosyaları"nı içeriyor (aynı belge, katman-1 tablosu).

### B6 — Router'ın niyet ayrımı yok (doğrulanmış — canlı vaka)
Bu oturumda kullanıcının "…ekrana bağlıyor…" cümlesi `designing-interfaces`
skill'ini tetikledi; cümle bir değerlendirme, iş talebi değil. Neden:
`bin/route.py:44` (`matches`) kelime-başı eşleşmesi yapıyor, soru/sohbet ile
iş isteğini ayırmıyor; tetik listeleri `.agents/routing.yml:19` ve sonrası
(doğrulanmış — bu oturumda canlı gözlendi).

### B7 — Agent Ofis canlı ve aradığımız run yüzeyi ZATEN onda (doğrulanmış)
Kaynak: MCP `agent-ofis` canlı sorgusu, 2026-07-26 (doğrulanmış). `list_projects` 15 kayıtlı proje,
`ofis_durum` 30 run döndürüyor — her run `run_id`, `project`, `status`
(completed/paused/blocked/in_progress), `current_phase`, `current_step`,
`request`, `updated_at` taşıyor. Örnekler: "4 VETO — kullanıcı kararı
bekleniyor" (blocked), "Token bütçesi nedeniyle duruldu… Hiç kod değişmedi"
(paused). Bu şema, Codex'in sıfırdan tasarlamayı önerdiği Run Contract'ın
neredeyse birebir karşılığıdır — **inşa edilecek değil, bağlanacak bir yüzey**.

### B8 — Görünürlük kaybının tarihi net (doğrulanmış)
Kaynak: `ofis_durum` çıktısı + `git log` (doğrulanmış). En yeni run 2026-07-23
(4flow, yetkilendirme sızıntısı).
AurasAgents çalışması 2026-07-23/24'te başladı (git log: ilk commit'ler
23-24 Temmuz). Yani AurasAgents'a geçildiği gün run kaydı kesildi; kullanıcının
"fark göremiyorum" gözlemi **kozmetik değil, ölçülebilir bir regresyon**:
önceden her iş ekranda satır üretiyordu, şimdi hiçbiri üretmiyor.

### B9 — Skorlama metodolojisi kusurlu (Codex bulgusu, kabul edildi)
Kaynak: Codex münazara turu 1, 2026-07-26 — LLM görüşü **ikincil** sinyaldir,
makine kanıtı değil (AGENTS.md:11). D seçeneği B ve C'nin bileşenlerini içeren bir paket; paketi kendi alt
bileşenleriyle yarıştırmak sonucu baştan belirler. Ayrıca hassasiyet analizi
yok (B ile C arasındaki 1 puan ağırlık oynamasıyla ters döner) ve D'nin kalite
puanı "sözleşmede izinli olması"na dayandırılmış — izin, kalite ölçümü değildir.
Bu tablo bu haliyle **karar kanıtı sayılmamalı**, yalnız seçenek haritası.

## Ağırlıklı karşılaştırma

Ağırlıklar ve skorlar analistin yargısıdır — kanıt değil, **spekülatif**
karar girdisi; kullanıcı ağırlıkları değiştirirse sıralama değişebilir.

| Ölçüt (ağırlık) | A: Orkestrasyonu AurasAgents'a taşı | B: Agent Ofis'e devret | C: Yalnız router fix | D: Sözleşme-uyumlu ince katman |
|---|---|---|---|---|
| Tasarım sözleşmesine uyum (25) | 1 — B1/B2 ile doğrudan çelişir | 5 — §12'nin aynısı | 5 — nötr | 5 |
| Hissedilen fark (25) | 5 | 3 — dağıtım gelir, görünürlük AurasAgents'ta yok | 1 | 4 |
| Kalite / hata yakalama (20) | 2 — bölünmüş bağlam tutarsızlık üretir (B1) | 3 | 3 | 5 — bağımsız doğrulama sözleşmede meşru |
| Maliyet: inşa + token (15) | 1 — en pahalı | 5 | 5 | 3 |
| Tek doğruluk kaynağı / bakım (15) | 3 — Agent Ofis'i kopyalar | 2 — iki sistem, iki hafıza | 5 | 4 |
| **Ağırlıklı toplam (100)** | **50** | **73** | **72** | **86** |

**D'nin içeriği:** (1) `.agents/state/run-<tarih>.md` görünür ledger — hangi
adım, hangi kanıt, ne bekliyor; (2) subagent yalnız sözleşmenin izin verdiği
iki işte: araştırma context izolasyonu ve fresh-context bağımsız doğrulama
(kendi işini onaylama yasağıyla uyumlu, `AGENTS.md:24`); (3) capability
profillerine `roles` alanı + routing tablosunun çok-katmanlı işi Agent Ofis
orkestratörüne devretmesi; (4) B6'daki router niyet ayrımı düzeltmesi.

## Karar önerisi (Codex münazarası sonrası revize: E′)

**Revize öneri E′** — D'nin yerine (dayanak: B7 `ofis_durum` çıktısı, B8 `git log`,
B9 Codex turu — **ikincil**). Değişim gerekçesi: B7/B8 (run yüzeyi zaten
var ve görünürlük kaybının tarihi belli) + Codex'in üç haklı eleştirisi (B9
skorlama kusuru, `roles` alanının rol tiyatrosunu başka adla geri getirmesi,
elle yazılan Markdown ledger'ın bayatlaması).

E′ içeriği (sözleşme dayanağı: `VIBE_CODING_TASARIM_TEMMUZ_2026.md:62` ve `:258`):
(1) capability profillerine `roles` alanı EKLENMEZ; subagent kullanımı dar
enum: `none | isolated_research | independent_review | independent_worktree`
(sözleşme §2 ile birebir). (2) AurasAgents run olaylarını Claude Code hook'ları
ile (UserPromptSubmit/PostToolBatch/SubagentStop/Stop) append-only, gitignore'lu
`.agents/runtime/*.jsonl`'e yazar — elle ledger yok, ayrı servis yok. (3) Bu
olaylar Agent Ofis'in mevcut run şemasına (B7) projekte edilir: dashboard
yeniden dolar; AurasAgents politika/izin/kanıt otoritesi olarak kalır (§12
hibrit kararının aynısı). (4) Router yalnız karar zarfı üretir, orkestratör
olmaz; ilk iş `chat/question` ile `actionable work` ayrımı (B6).
(5) Kullanılabilirlik ağırlık değil **geçiş kapısı**: kullanıcı ekranı açtıktan
sonra ≤10 saniyede "ne çalışıyor / neyi bekliyor / sıradaki hareket / hangi
kanıt" sorularını cevaplayamıyorsa E′ geçmemiştir.

Eski öneri **D** (aşağıdaki tabloda 86 puan) geri çekildi. Gerekçe (dayanak: B1 `AGENTS.md:18`, B2
`VIBE_CODING_TASARIM_TEMMUZ_2026.md:258`): kullanıcının şikâyetinin iki bileşeninden (görünürlük, dağıtım)
görünürlük tamamen, dağıtım sözleşmenin izin verdiği ölçüde karşılanır; A'nın
tek üstünlüğü olan "hissedilen fark" farkı 1 puan, buna karşılık sözleşme
ihlali ve maliyet bedeli ağır.

A'yı seçmek istiyorsanız yolu açık ama bedelli: `VIBE_CODING_TASARIM_TEMMUZ_2026.md:62` (§2) ve `:258` (§12)'yi
geçersiz kılan bir ADR gerekir ve sözleşmenin kendi kuralı gereği bu, iddiayla
değil 20–30 görevlik pilot metriğiyle savunulmalıdır (B3).

## Açık sorular

0. (KAPANDI) Agent Ofis'in canlılığı: doğrulandı, canlı — B7.
1. Ölçüm yokluğu: hangi sistemin daha iyi olduğu bugün kanıtlanamaz (B3).
   Pilot metriklerini toplamaya başlamalı mıyız — yoksa karar sezgiyle mi
   verilecek? (Sezgi meşru bir yöneticilik kararıdır, ama kanıt olarak
   etiketlenmemeli.)
2. YAZMA arayüzü: `ofis_durum` okuma yönü doğrulandı; AurasAgents'ın run
   olaylarını Agent Ofis'e hangi arayüzle YAZACAĞI doğrulanmadı (mevcut MCP
   araçları salt-okunur görünüyor). E′'nin tek gerçek teknik riski budur.
3. Codex'in kendi uyarısı (kabul): hook'lar hareketi iyi, ANLAMI kötü gözler.
   `next_action` ve "blocked" nedeni yaşam-döngüsü olaylarından güvenilir
   çıkarılamaz; yanlış tasarlanırsa "aktivite tiyatrosu" üretir.
3. Ledger dosyasının hangi ayrıntıyı taşıyacağı: her adım mı, yalnız karar
   noktaları mı? Fazla ayrıntı gürültü, az ayrıntı görünmezlik.
