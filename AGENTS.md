# AurasAgents — kanonik çalışma kuralları

Bu dosya motor-bağımsız tek doğruluk kaynağıdır (Claude, Codex, Copilot aynı
kuralları buradan okur). Motor-özel notlar adapter dosyalarındadır
(`CLAUDE.md` vb.). Çelişkide bu dosya kazanır.

## Kimlik ve amaç

AurasAgents, tek kişilik kurucu için kanıt-temelli agent çalışma sistemidir.
Tasarım sözleşmesi: `VIBE_CODING_TASARIM_TEMMUZ_2026.md` (Codex mutabakatlı).
Mimari kararlar: `docs/decisions/` (ADR).

## Kapsam sınırı — sistem neyi zorlamaz

Bu sistem **doğruluk ve güvenliği** deterministik olarak zorlar. Tasarım,
operasyon ve ürün ölçümü aşamalarında **kapı yoktur** — oralarda skill'ler
tavsiye verir, hiçbir mekanizma uyulduğunu denetlemez. "Kanıt > beyan" ilkesi
yalnız kapı olan aşamalarda geçerlidir.

Aşama aşama ölçülmüş kapsam: `docs/yasam-dongusu-kapsami.md`. Bir aşamaya kapı
eklenirse o belge güncellenir; güncellenmemesi belgeyi yanlış-güven kaynağına
çevirir.

## Çalışma ilkeleri

1. Kanıt > beyan. "Bitti" demek kanıt değildir; kanıt CI'dan `evidence.json`
   olarak gelir. LLM incelemeleri (Codex review, /code-review) risk sinyalidir,
   kanıt değildir.
2. Tek yazar. Aynı iş roller arasında bölünmez; paralellik yalnız bağımsız
   işlerde (ayrı worktree/session).
3. Spec-anchored. Kod ground-truth'tur; sözleşme GitHub Issue Form'dur
   (hedef + EARS kabul kriterleri + görev sınıfı + risk). Diff tek cümleyle
   tarif edilebiliyorsa form ve plan atlanır; PR `micro` etiketi alır.
4. Plan mode yalnız belirsiz kapsam veya yüksek riskte zorunludur.
5. Agent kendi işini onaylayamaz, kendi risk/profil sınıfını yükseltemez.

## Hafıza otoritesi

Hiyerarşi (çelişkide üstteki kazanır):

1. `AGENTS.md` + `docs/decisions/` (kanonik, reviewed)
2. Run/PR kayıtları
3. Auto-memory (disposable yerel önbellek — hiçbir iş ona bağımlı olamaz)

Kalıcılaştırma yalnız reviewed PR ile olur. Secret, kullanıcı verisi ve
doğrulanmamış çıkarım kalıcı hafızaya giremez. 90 gün dokunulmamış kayıt
gözden geçirilir. Bakım robotu: `python3 bin/memory_hygiene.py` bayat/
kaynaksız/çelişen kaydı işaretler (silmez — emeklilik reviewed PR ile).

## Risk politikası — üç deterministik sonuç

Risk iki kez hesaplanır: ön sınıf issue form'dan, nihai sınıf diff'ten.
Eskalasyon yalnız yukarı olur. `deny` her zaman önceliklidir.

| Sonuç | Tetik (path/aksiyon kuralı) | Davranış |
|---|---|---|
| auto | docs/**, tests/**, *.md, küçük refactor (izinli path içinde) | Uçtan uca; CI yeşilse merge'e hazır |
| approval | uygulama kodu, bağımlılık değişikliği, auth/ödeme komşusu path | Plan onayı + insan merge |
| deny | secret/credential dosyaları, veri silme, prod migration, permission genişletme | Varsayılan red; break-glass süreli + gerekçeli + kayıtlı |

## Push politikası

- Araştırma / ideation / mikro iş → push yok (yerel checkpoint yeter).
- Bütünlüklü değişiklik → tek PR; git işlemlerini agent yapar.
- Kritik veya cloud'da süren iş → contract + PR + CI kanıtı.
- Auto-merge yalnız dar path-allowlist'li mekanik işlerde.
- İlgisiz işleri tek PR'da toplama (bisect/rollback/kanıt izini bozar).

## Skill ve capability mekanizması

- Kanonik skill kaynağı: `.agents/skills/` (Agent Skills açık standardı).
- Görev sınıfı (`code-change` | `research` | `incident`) →
  `.agents/capability-profiles/<sınıf>.yml` profili → izinli skill/araç/ağ
  kümesi. Agent seçimini yalnız bu küme içinde yapar ve seçim loglanır.
- Skill seçimi takdire bırakılmaz: `.agents/routing.yml` tabloya bağlar,
  `bin/route.py` her istekte (UserPromptSubmit hook'u) görev sınıfı + zorunlu
  skill üretir. Yönlendirilen skill yüklenmeden işe başlanmaz; yanlış
  yönlendirme sessizce atlanmaz, gerekçelendirilip kullanıcıya söylenir.
- Yeni skill kuralı: aynı iş tipi üçüncü kez elle tarif ediliyorsa skill'dir.
  Yayın koşulu üçlüdür: eval + routing.yml tetiği + en az bir profil kaydı.
  Kasten yönlendirilmeyen skill `routing.yml` `not_routed`'a gerekçesiyle yazılır.

## Deterministik kapılar

- `bin/hooks/pre-push`: kernel doğrulaması geçmeden push edilemez
  (kurulum: `bash bin/install-hooks.sh`; bilinçli atlama: `git push --no-verify`).
- CI `evidence` job'ı: aynı doğrulamayı bağımsız makinede tekrarlar.
- UserPromptSubmit hook'u: skill yönlendirmesini her isteğe enjekte eder.
  Proje hook'u (`.claude/settings.json`, repoyla taşınır) + kullanıcı-global
  yedek (`--global-fallback`, proje hook'u varsa susar). Router asla
  bloklamaz (hatada sessiz exit 0) — kapı değil, pusuladır.
- `bin/codex-review.sh`: diff'i Codex'e inceletip PR'a yorum düşer — risk
  sinyalidir, makine kanıtı değildir.
- Bağımsız inceleme (merge yolu): `python3 bin/incele.py <pr>` — diff'i
  Codex'e (farklı satıcı, farklı kör nokta) inceletir, bulguyu P0/P1/P2
  ayırır, PR'a karar biçiminde yorum düşer. P0/P1 varsa merge REDDEDİLİR;
  `deny` sınıfı her zaman insana gider. `auto` risk + temiz inceleme + CI
  yeşil ise `--merge` ile birleştirir. İnceleme çıktısı ayrıştırılamazsa
  ENGEL (fail-closed) — "okunamadı" ile "temiz" aynı şey değildir.
  Not: bu bir süreç kuralıdır; `gh pr merge` ile doğrudan birleştirmek
  mekanik olarak hâlâ mümkündür.
  Bütçe `INCELE_BUTCE` (varsayılan 900s) — diff boyutuna göre ölçeklenmez,
  çünkü ölçüm boyutun sürücü olmadığını gösterdi (4.4KB→147s, 9.0KB→156s).
  Zaman aşımı ENGEL'dir ve ne yapılacağını yazar; ilk bakılacak yer asılı
  `codex exec` sürecidir — sızan inceleme sonrakini yavaşlatır.
- Kod kalitesi ratchet'i (ADR-0004): `bin/kalite.py` dosya/fonksiyon boyutu,
  karmaşıklık ve borç işaretlerini deterministik sayar; CI `--check` ile
  koşar. Mevcut borç kabul edilir, **büyümesi bloklanır**. Taban
  `.agents/kalite-baseline.json` (proje sahibi). Tabanı yükseltmek bilinçli
  karardır, gerekçesi commit mesajına yazılır.
- Proje kapısı (opsiyonel): `bin/hooks/proje-kapisi` varsa pre-push onu koşar.
  Projeye özel pazarlıksız yasaklar (ör. "localStorage'da token yok") motor
  dosyasını çatallamadan burada mekanizmaya bağlanır. Dosya motorun değil
  projenindir: `/auras` ezmez, geri-taşıma yukarı götürmez. Çalıştırılabilir
  değilse push engellenir — sessiz atlama yok.
- Secret kapısı proje muafiyeti: `.agents/secret-allowlist.txt` — her satır
  `yol-deseni  # gerekçe`. **Gerekçe zorunludur**; gerekçesiz satır kullanım
  hatasıdır (exit 2), "temiz" değildir. Bastırılan bulgu çıktıda `muaf:`
  etiketiyle GÖRÜNÜR kalır — sessiz susturma, kapının olduğu ama korumadığı
  hâldir. Dosya projenindir, motor ezmez.
- Test kapsamı daralmaz: `validate.py` testleri koşmadan önce KEŞFEDER; bir
  test dosyası import'ta çökerse ya da keşif desenine uymuyorsa kesilir.
  Gerekçe: eksilen test kırmızı testten tehlikelidir — kırmızı bağırır, yok
  olan test yalnız "Ran N"i sessizce küçültür (ölçüm 2026-08-07: PyYAML'sız
  yorumlayıcıda 220 yerine 186). Ortam bağımlılığı `tests/ortam.py` üstünden
  GÖRÜNÜR atlamaya çevrilir ve `tests/test_ortam.py` eksik ortamı tek bir
  yüksek sesli hataya bağlar: atlanan test "geçti" diye okunamaz.
- Skill doğrulayıcı sözleşmesi (ADR-0003): `check_*` / `scan_*` önekli skill
  script'i KAPI doğrulayıcısıdır ve en az bir kapıya bağlanmak zorundadır
  (`validate.py` bağlanmamışı reddeder). Yazılmış ama çağrılmayan doğrulayıcı
  = kural belgede var sistemde yok. Diğer adlar yardımcı araçtır.
- Kernel senkronu çift yönlüdür (ADR-0002). `/auras` kanonikten projeye
  taşır; ezme kararı manifest'e değil kanonik git geçmişine dayanır — projede
  üretilmiş içerik ezilmez, korunur. Ters yön `bin/auras_geri.py`: projede
  kalan kernel işini kanonik çalışma ağacına alır (commit insanındır).
- Not: private repo + Free plan'da GitHub dal koruması kapalıdır; koruma
  yerel kanca + CI ile sağlanır. Repo public olur veya Pro alınırsa
  `kernel` check'i required status check yapılmalıdır.

## Kapıların gerçek sınıfı

Bir kapının gücünü olduğundan büyük yazmak, olmayan korumaya güvendirir.
Bu tablo her kapının NE OLDUĞUNU söyler; abartma yasaktır.

| Kapı | Sınıf | Neyi engelleyemez |
|---|---|---|
| `bin/kapi.py` (tur/Stop) | yerel workflow guard | Agent olay kaydını silebilir/yazabilir, doğrulayıcıyı değiştirebilir; kayıt yoksa kapı sessizce geçer |
| `bin/hooks/pre-push` | yerel workflow guard | `git push --no-verify` ile atlanır; kanca kurulu değilse hiç koşmaz |
| `bin/incele.py` (merge) | süreç kuralı | `gh pr merge` ile doğrudan birleştirmeyi engellemez |
| CI `evidence` job'ı | bağımsız makine kanıtı | Required check olmadığından merge'ü durduramaz |

Yerel kapılar **güvenlik sınırı değildir**: hepsi agent'ın yazabildiği aynı
dosya sisteminde, aynı kullanıcı yetkisiyle çalışır — ortak güven kökü
agent'ın kendisidir. İşlevleri hatayı ucuzken yakalamaktır, kötü niyeti
durdurmak değil. Gerçek bütünlük sınırı yalnız remote'ta, agent'ın
değiştiremediği zorunlu check ile kurulur; o kurulana kadar bu sistem
dürüstçe **yerel workflow guard** setidir.

Sonuç: kapı çıktısı "doğrulandı" değil "bu turda şu kanıt görüldü" demektir.
Kanıtın kaynağı kayda yazılır (`src`: `exit` = gerçek çıkış kodu, `event` =
hook olay türü). Çıkış kodu maskeleyen komut (`pytest || true`,
`pytest | tail`) "geçti" sayılmaz — kabuğun kodu testin kodu değildir.

## Kimlik ve erişim

- GitHub işleri `gh` CLI ile; kimlik kısa ömürlü GitHub App installation
  token (kalıcı geniş PAT yasak).
- Ağ erişimi profil allowlist'ine tabidir; varsayılan kapalıdır.
- Production secret agent ortamına girmez.

## Konvansiyonlar

- Dil: tr-TR (kod tanımlayıcıları İngilizce).
- Commit: küçük, tek amaçlı, açıklayıcı mesaj; contract'lı işte PR
  gövdesinde contract ID.
- Kanıt: her contract'lı PR'da CI `evidence.json` üretir
  (şema: `schemas/evidence.schema.json`).
