# Mükemmel Vibe Coding Tasarımı — Temmuz 2026

**Kim için:** Tek kişi (solo kurucu) + dünya standartlarında çıktı hedefi
**Girdi:** `AURASAGENTS_PRODUCT_VISION.md` (v0.1) + Agent Ofis saha deneyimi + Temmuz 2026 derin web araştırması (2 bağımsız araştırma raporu)
**Durum:** Codex ile 2 turlu münazara sonrası **mutabakatlı sürüm** (bkz. §11)
**İlke:** Vizyonun ruhu korunur, platform inşası ertelenir. Karmaşıklık ancak somut bir başarısızlık modunu çözdüğü kanıtlanınca eklenir. Ama sadeleştirme, sözleşme semantiğini kaldırmak demek değildir: **motor yazılmaz, şema yazılır.**

---

## 0. Tek cümlelik tasarım

> GitHub omurga, Claude Code motor, Codex bağımsız risk sinyali; hafıza Git'te
> yaşar, skill/MCP seçimi statik capability profilleri içinde Claude'un native
> progressive-disclosure mekanizmasıyla yapılır, kanıt CI'dan `evidence.json`
> olarak gelir — control plane servisi yazılmaz, ince bir sözleşme çekirdeği yazılır.

---

## 1. Araştırmanın vizyon dokümanına söylediği şey

Vizyon dokümanı ilkesel olarak **doğru** (evidence over assertion, skills-first,
cloud-first, human above the loop). 2026 saha konsensüsü üç parçasını "erken"
ilan ediyor — ama her birinin **ince bir çekirdeği** Gün-1'de kalır:

| Vizyondaki parça | Karar | Gün-1'de kalan ince çekirdek |
|---|---|---|
| Capability Resolver (11.7) | Servis **yapılmaz** | `.agents/capability-profiles/` altında 3 statik profil (§5) |
| Control plane + Work Contract motoru | Motor **ertelenir** | GitHub Issue Form şeması + stable contract ID (§3) |
| Evidence Ledger (ayrı servis/DB) | Servis **yapılmaz** | CI'ın ürettiği `evidence.json` + kalıcı digest'ler (§6) |

Vizyonun **korunan** çekirdeği: agent kendi işini onaylayamaz, düşük risk
otomatik / yüksek risk onaylı, hafıza sohbette değil sürümlü depoda, açık
standart (Agent Skills, MCP) özel formatın önünde, no hidden local dependency.

---

## 2. Mimari — üç araç, sıfır platform servisi

```
İstek (her yüzeyden: terminal / claude.ai/code / mobil / GitHub issue)
   │
   ▼
Claude Code (yazar motor — local veya cloud session)
   │  plan mode (belirsiz kapsam) → spec-anchored iş → TDD döngüsü
   ▼
PR + kanıt paketi
   │
   ├── GitHub Actions  → bağımsız MAKİNE KANITI (typecheck, lint, test, build → evidence.json)
   ├── Codex Review    → çapraz-vendor RİSK SİNYALİ (P0/P1/P2; kanıt değil, sinyal)
   └── /code-review    → fresh-context Claude reviewer; kritik merge'de ultrareview
   │
   ▼
İnsan "above the loop": merge kararı = CI yeşil (zorunlu) + risk sinyalleri (bilgilendirici) + insan onayı
```

**Terminoloji (Codex mutabakatı):** Bağımsız LLM incelemesi tekrarlanabilir
check/artifact üretmediği sürece **kanıt katmanı değil, risk sinyalidir**.
Makine kanıtı yalnız deterministik kontrollerden (CI) gelir. Çapraz-vendor
review yine de değerlidir: yazar ve hakem farklı modelden, korelasyonlu hata
olasılığı düşer; iki model çelişirse otomatik çözülmez, insana gelir.

**Rol tiyatrosu yok:** PM-agent/architect-agent/QA-agent'ın aynı işi paylaşması
israf (Cognition: "Don't Build Multi-Agents"). Subagent yalnız iki meşru işte:
(a) context izolasyonu (araştırma/keşif), (b) bağımsız doğrulama (fresh-context
review). Paralellik yalnız gerçekten bağımsız işlerde (git worktree).

---

## 3. İş sözleşmesi — motor değil, form + şema

Work Contract v0 = **GitHub Issue Form** (serbest şablon değil; zorunlu
yapılandırılmış alanlar + stable contract ID). Metrikler serbest metinden
hesaplanamaz; form alanları makine-okunur olmalı:

| Alan | İçerik |
|---|---|
| Hedef | Tek cümle, sonuç odaklı |
| Kabul kriterleri | EARS formatı ("X olduğunda sistem Y yapmalı") — teste 1:1 eşlenir |
| Görev sınıfı | `code-change` / `research` / `incident` / `design` → capability profilini seçer (§5; `design` ADR-0005) |
| Kapsam | İzinli path'ler / kapsam dışı alanlar |
| Risk sınıfı | Ön (provisional) sınıf; diff sonrası statik kurallarla yeniden hesaplanır (§6) |
| Zorunlu kanıt | Hangi check/artifact başarıyı gösterir |

Kural: **diff'i tek cümleyle tarif edebiliyorsan formu ve plan mode'u atla**
(Anthropic resmi tavsiyesi) — ama atlanan işte de PR, contract-ID'siz "mikro iş"
olarak etiketlenir ki metrik kirlenmesin. Spec, kod ground-truth kalmak üzere
"spec-anchored"dır; spec-as-source ve pseudo-code seviyesinde spec israftır.

---

## 4. Hafıza — kanonik gerçek Git'te, adapter'lar kenarda

Üç katman, sıfır yeni altyapı; **kanonik kaynak her zaman Git**:

| Katman | Ne | Normatif kural |
|---|---|---|
| **1. Kanonik gerçek** (Git, reviewed) | `AGENTS.md` (motor-bağımsız kurallar), `docs/decisions/` (ADR), skill referansları, progress dosyaları, PR/commit geçmişi | Cihazdan bağımsız, cloud session'a otomatik taşınır, sürümlü. Her kalıcı kayıt: kaynak + kapsam + doğrulama tarihi + gözden geçirme tarihi taşır. Kalıcılaştırma yalnız **reviewed PR** ile olur |
| **2. Motor adapter'ı** (sen yazarsın) | `CLAUDE.md` < 200 satır + `.claude/rules/` path-scoped kurallar | CLAUDE.md kanonik gerçek değil, AGENTS.md'nin Claude adapter'ıdır (`@AGENTS.md` import). Kesin kural → hook'a, tavsiye → buraya. "/doctor trim" + "bu satırı silsem hata yapar mıydı?" testi |
| **3. Geçici öğrenme** (Claude yazar) | Auto-memory (`MEMORY.md` + konu dosyaları) | **Disposable, güvenilmeyen lokal cache** — hiçbir run doğru çalışmak için ona bağımlı olamaz (aksi "no hidden local dependency" ihlali). Ayda bir `/memory` hijyeni; değerli bulgu katman 1'e reviewed PR ile terfi eder. Secret/kullanıcı verisi/doğrulanmamış çıkarım otomatik terfi edemez |

Agent Ofis'ten taşınan iki ilke: **otorite hiyerarşisi** (AGENTS.md/ADR > run
notu > memory kaydı; çelişkide üstteki kazanır) ve **bayatlık kuralı** (90 günde
dokunulmamış kayıt gözden geçirilir). Harici memory MCP'si (mem0 vb.)
**başlangıçta yok** — "aynı bağlamı sürekli yeniden anlatma" belirtisi çıkarsa
değerlendirilir.

---

## 5. Skill ve MCP — özgürlük profil sınırları içinde

**Seçim hibriti (Codex mutabakatı):** Model skill *keşfeder*, izin sınırını
*belirleyemez*.

1. Issue Form'daki görev sınıfı → `.agents/capability-profiles/` altındaki 3
   statik profilden birini seçer: `code-change` / `research` /
   `incident` / `design` (dördüncüsü 2026-08-16'da eklendi — ADR-0005;
   tek taraflı değişiklik, gerekçesi orada).
2. Profil, izinli skill/tool/network kümesini belirler (düz YAML, servis yok).
3. Model **yalnız bu küme içinde** native progressive disclosure ile seçer
   (iyi yazılmış `description` = küme-içi resolver).
4. Seçilen skill/tool/model, run kaydına loglanır (Skill Lift metriği için).
5. Model kendi profilini veya risk seviyesini değiştiremez/yükseltemez.

**Skill'ler:** `.agents/skills/` kanonik kaynak (Agent Skills açık standardı —
Claude, Codex, Copilot, Cursor dahil 40+ üründe çalışıyor). Başlangıç seti
**capability odaklı 5 skill** (her biri gerçek kullanımdan doğma "gotcha"
bölümlü; evalsız skill yayınlanmaz):

1. `project-onboarding` — yeni repo/ortamı sisteme bağlama
2. `implement-change` — spec-anchored TDD döngüsü (test yaz → red → green → commit)
3. `security-review` — OWASP-temelli denetim; CRITICAL/HIGH bulguda merge durur
4. `research-with-evidence` — kaynaklı/doğrulanabilir araştırma çıktısı
5. Repo-özel 1 dar skill (ör. `secure-api-change`) — gerçek ihtiyaçtan doğar

Intake (issue form), verification (CI), cross-review (PR workflow) ve memory
hijyeni (aylık checklist/scheduled task) **skill değil, workflow primitive'idir**.

**MCP diyeti:** Her MCP sabit context vergisidir. Sayı kuralı değil ölçüt
kuralı: her bağlantı yetki kapsamı + credential modeli + context maliyeti +
audit edilebilirlik üzerinden gerekçelendirilir; pratikte başlangıç 3'ü geçmez:

- GitHub → `gh` CLI (4–32× ucuz, benchmark'ta daha güvenilir); **kimlik: kısa
  ömürlü GitHub App installation token** — kalıcı geniş PAT değil; PAT ancak
  süreli, dar yetkili, modele gösterilmeyen istisna (Codex mutabakatı)
- Browser doğrulama → Chrome DevTools MCP *veya* Playwright (ikisi birden değil)
- Güncel doküman → Context7 tarzı tek doküman-arama MCP'si
- DB → yalnız read-only, yalnız gerektiğinde

---

## 6. Risk ve enforcement — iki eşik anlatımı, üç deterministik sonuç

UX'te sade anlatım ("düşük/yüksek") kalır; **enforcement üç sonuç üretir** ve
contract alanları + gerçekte değişen path/action'lardan **statik kurallarla**
türer (model muhakemesinden değil — Codex mutabakatı):

| Sonuç | Tetik (örnek statik kural) | Davranış |
|---|---|---|
| **Auto-PR** | docs/test/küçük refactor; izinli path içinde | Agent uçtan uca; CI yeşilse merge'e hazır |
| **Approval-required** | uygulama kodu, dependency, auth-komşusu path | Plan onayı + insan merge |
| **Deny / break-glass** | production secret, veri silme, migration, permission genişletme | Varsayılan red; break-glass **süreli + gerekçeli + audit kayıtlı** |

Kurallar: `deny` her zaman önceliklidir; risk **iki kez** hesaplanır (ön sınıf
contract'tan, nihai sınıf diff'ten — diff daha riskli çıkarsa yukarı eskale
edilir, asla aşağı inmez). Enforcement araçları bugün var olanlar: PreToolUse
hook'ları, permission allowlist + sandbox, branch protection + required checks.

**Kanıt formatı:** CI her contract'lı koşuda küçük bir `evidence.json` üretir:
contract ID, commit SHA, kriter→check eşlemesi, artifact/run linki **+ kalıcı
sha256 digest'ler** (yalnız süresi dolabilen linklere dayanılmaz), skill+model
sürümü, approval kayıtları. GitHub Checks/artifacts/PR içinde saklanır — ayrı
ledger servisi yok. Bu dosya, 90 günlük metriklerin ham verisidir.

---

## 7. Günlük ritim (the vibe)

1. **Sabah:** İstekleri issue form'la ver — cihaz fark etmez (terminal,
   claude.ai/code, mobil). Uzun işler cloud session'da; laptop kapansa da sürer
   (`claude --cloud` / `--teleport`).
2. **Gün içi:** Paralel bağımsız işler ayrı worktree/cloud session. Sen kod
   satırı değil, PR + `evidence.json` + risk sinyalleri görürsün.
3. **Akşam:** Merge kararları (tek insan-onay noktası). Checkpoint/`Esc Esc`
   güvenlik ağı sayesinde cesur denemeler ucuz.
4. **Haftalık:** 30 dk bakım — `/memory` hijyeni, `/doctor` trim, skill
   gotcha'larını güncelle, katman-3→katman-1 terfi PR'ları.

---

## 8. 90 günlük yol (vizyonun Aşama 0–2'sinin sade hali)

| Hafta | İş | Başarı ölçütü |
|---|---|---|
| 1–2 | İskelet: AGENTS.md + CLAUDE.md adapter + Issue Form + capability profilleri + CI/evidence.json + branch protection + Codex Review app + GitHub App token kimliği | Yeni cihazdan yalnız login ile doğrulanmış PR alınıyor (vizyon Aşama 1 ölçütü) |
| 3–6 | 5 capability skill'i gerçek işlerde piş; threat model taslağı (vizyon §15) | Skill'li koşu, skillsiz baseline'dan ölçülebilir iyi (Skill Lift) |
| 7–12 | evidence.json'dan metrik topla: Verified Outcome Rate, First-pass Acceptance, Cost per Accepted Outcome, Human Interruption Load | Veri, "control plane gerekli mi?" sorusuna cevap veriyor |

**Control plane / auras CLI / özel dashboard tetiği:** Ancak şu ikisi ölçülerek
kanıtlanırsa: (a) GitHub-native akış haftada N kez yetersiz kalıyor, (b) ikinci
çalışma motoru aynı skill'lerle gerçekten koşuyor. Kanıt yoksa yazılmaz —
vizyonun 12. kesin kararı: "Yeni altyapı yalnızca ihtiyaç kanıtlanınca eklenir."

---

## 9. Bilinçli olarak yapılmayanlar

- Capability Resolver **servisi**, control plane **servisi**, Evidence Ledger **servisi/DB** → ince şema çekirdekleri (profil YAML, Issue Form, evidence.json) yeterliyken değil
- Model seçimi / fallback zinciri / maliyet-bazlı routing → solo ölçekte erken
- Rol bazlı agent ekibi (aynı iş üstünde) → yalnız yazar + bağımsız doğrulayıcılar
- Harici memory MCP → belirti yokken değil
- A2A, çoklu-motor adapter katmanı → ikinci motor kanıtlanmış ihtiyaç olana dek
- Spec Kit tarzı ağır seremoni → Issue Form + EARS yeter

---

## 10. Bu tasarımın araştırma dayanakları (özet)

- **Anthropic resmi:** plan mode koşullu; "agent'a çalıştırılabilir kontrol ver";
  evidence göstert; CLAUDE.md < 200 satır; kesin kural = hook; git-tabanlı
  progress/memory deseni (long-running agents harness).
- **Saha konsensüsü:** çapraz-vendor yazar/reviewer döngüsü (~$20/ay ile) en
  övülen solo desen; "Don't Build Multi-Agents" (Cognition) — rol tiyatrosu israf;
  spec-anchored kazandı, spec-as-source kaybetti; EARS fiili standart.
- **Benchmark:** GitHub işlerinde CLI, MCP'den 4–32× ucuz ve %100 vs %72 güvenilir;
  MCP yalnız CLI eşdeğeri olmayan yeteneklere.
- **Agent Skills standardı:** 40+ üründe çalışıyor — skill yatırımı motor-bağımsız.

---

## 11. Codex mutabakat kaydı (el sıkışma)

**Süreç:** 2 tur münazara (Codex `codex exec`, salt-okunur, repo bağlamıyla).
**Sonuç:** Tur 1 KISMEN → revizyonlar → Tur 2 **ŞARTLI EL SIKIŞMA** → şartlar
işlendi → **MUTABAKAT**.

Codex'in kabul ettirdiği revizyonlar:
1. "Şemasız GitHub-native" düzeltildi: Issue Form şeması + stable contract ID +
   CI-üretimi `evidence.json` (kalıcı digest'li) Gün-1'de var.
2. Üç deterministik enforcement sonucu (auto / approval / deny+break-glass);
   model kendi profil/riskini yükseltemez; deny öncelikli; risk diff sonrası
   yeniden hesaplanır.
3. Skill seti capability odaklı yeniden kuruldu; intake/verify/review/hijyen
   workflow primitive'i sayıldı.
4. Auto-memory "disposable cache" olarak normatifleşti; kanonik kaynak
   AGENTS.md + Git (CLAUDE.md yalnız adapter).
5. Terminoloji: LLM review = risk sinyali; makine kanıtı yalnız deterministik CI.
6. Kimlik: kısa ömürlü GitHub App installation token; kalıcı geniş PAT yasak.

Claude'un savunup koruduğu noktalar (Codex itiraz etmedi/kabul etti):
- Resolver'ın kalan sorumlulukları (model routing, fallback) solo ölçekte erken.
- GitHub işleri `gh` CLI ile (token maliyeti + güvenilirlik verisi).
- Control plane/dashboard yalnız metrik-kanıtlı ihtiyaçla yazılır.

---

## 12. İkinci mutabakat — Agent Ofis ilişkisi ve push politikası (24 Tem 2026)

İkinci Codex münazarası (1 tur + kapanış, EL SIKIŞMA: EVET) iki soruyu bağladı:

**Agent Ofis'in yerine değil, üzerine (hibrit):**
- Agent Ofis kalır: dashboard, intake, ideation, manifest routing.
- Üzerine güven katmanı: kalıcı bilgi Git'e aynalanır; uzun/asenkron işler
  cloud runner'a; kritik değişikliklere CI evidence + Codex sinyali.
- Manifest göçü **mekanizma-mekanizmaya** (düz metne değil): `forbidden` →
  hook/allowlist, VETO → branch protection, routing → capability profili,
  conventions → AGENTS.md; + conformance testleri.
- Nihai karar 20–30 gerçek görevlik pilotta, görev sınıfı bazında metrikle:
  sonuç oranı, insan dakikası, çevrim süresi, rollback, ideation kalitesi.
  "Yeni sistem kesin daha iyi" iddiası geri çekildi — kanıt karar verir.

**Push/PR politikası (yorgunluk önleme):**
- Araştırma / ideation / mikro iş → local checkpoint, push yok.
- Bütünlüklü değişiklik → tek PR (git işini agent yapar).
- Kritik veya cloud-continuity işi → contract + PR + CI evidence.
- Auto-merge yalnız dar path-allowlist'li, deploy tetiklemeyen mekanik işler.
- Diğer düşük riskliler → auto-ready; kullanıcı günde bir toplu bakışla onaylar.
- "Günlük toplu PR" anti-pattern (bisect/rollback/kanıt izini bozar) — yapılmaz.
