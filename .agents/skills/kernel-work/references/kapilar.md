# Deterministik kapılar — tam davranış ve ölçüm geçmişi

`AGENTS.md` her oturumda TAM yüklenir; bu dosya yalnız kernel işinde okunur.
Bu yüzden ayrım şudur: AGENTS.md kapının NE olduğunu söyler, burası NASIL
çalıştığını ve HANGİ ölçümün onu bu hâle getirdiğini anlatır. Bir kapının
davranışını değiştiriyorsan **önce burayı oku** — çoğu kural bir kez ölçülmüş
bir hatanın karşılığıdır ve gerekçesi silinirse aynı hata geri gelir.

## `bin/hooks/pre-push` — yerel push kapısı

Kernel doğrulaması geçmeden push edilemez. Kurulum: `bash bin/install-hooks.sh`;
bilinçli atlama: `git push --no-verify`.

Dört tarama sırayla koşar, **hepsi fail-closed** (tarayıcı dosyası yoksa push
engellenir; "yok" hâli "geçti" olamaz):

1. `validate.py` — kernel doğrulaması. Exit 2 "araç hatası"dır ve "kural
   ihlali" ile aynı şey değildir; kapı ikisini de bloklar ama **doğru olanı
   söyler**. 2026-08-07: Homebrew python3'ü 3.14'e taşıdı, PyYAML yoktu ve
   kapı "doğrulama BAŞARISIZ" dedi — oysa doğrulama hiç koşamadı.
2. `scan_secrets.py --git` — yalnız git-İZLENEN içerik. Çalışma ağacının
   tamamı taranırsa `.gitignore`'lu yerel `.env.local` push'u bloklar
   (OICommand'da yaşandı) ve kullanıcı `--no-verify` alışkanlığı edinir.
3. `scan_personal_data.py` — AYRI boyut. Sır tarayıcısı "bu değer bir anahtar
   mı", bu "bu dosya bir insan listesi mi" diye sorar. 4Flow'da (2026-08-07)
   20 kişilik `users_list.json` sır taramasından temiz geçmişti; kapıda bu
   boyut hiç yoktu. Eşik: ≥8 benzersiz e-posta ya da TC kimlik no. `AUTHORS`
   gibi tanımı gereği kişi listesi olan dosyalar muaftır.
4. `scan_gecmis.py --push-range` — index taramasının kör noktası (bağımsız
   inceleme, Codex 2026-08-12): commit A'da eklenip B'de silinen sır index'te
   GÖRÜNMEZ ama iki commit de uzak geçmişe gider ve oradan geri alınamaz.
   Yeni dalda (remote_sha 40 sıfır) aralık `--not --remotes` olur.

Yorumlayıcı seçimi çıkış koduna değil **çıktıya** bakar: `AURAS_PYTHON=/usr/bin/true`
ile sırlı push kapıyı sessizce geçmişti (2026-08-07) — `true` argümanları yok
sayıp 0 döner. Süreç kendi hakkında yalan söyleyebiliyorsa çıkış kodu kanıt
değildir.

Worktree'den push'ta git kancayı KENDİ ortamıyla çalıştırır; `GIT_DIR` mirası
alt süreçlere geçip doğrulayıcının geçici depolardaki `git` çağrılarını yanlış
depoya yöneltiyordu (PR #17). Çözüm: ortamı temizle, keşfi normal yoldan yap.

### Proje kapısı (opsiyonel uzantı)

`bin/hooks/proje-kapisi` varsa pre-push onu koşar. Projeye özel pazarlıksız
yasaklar (ör. "localStorage'da token yok") motor dosyasını çatallamadan burada
mekanizmaya bağlanır. Dosya motorun değil projenindir: `/auras` ezmez.
Çalıştırılabilir değilse push engellenir — sessiz atlama yok.
`</dev/null` ZORUNLU: git ref listesini pre-push'a stdin ile verir; proje
kapısı stdin'i okursa ref'e dayanan her politika sessizce işlevsizleşir
(denetim bulgusu 2026-08-06).

## `bin/kapi.py` — tur sonu kanıt kapısı (Stop hook)

Bu turda ne değiştiğine bakar ve kanıt arar: kaynak kod değiştiyse SON
düzenlemeden sonra koşmuş ve GEÇMİŞ bir test; risk yüzeyi değiştiyse güvenlik
incelemesi; görünür yüzey değiştiyse tıklama kanıtı.

Codex eleştirisi (2026-07-26) doğrudan buraya işlendi:
- "test dosyası değişti" test kanıtı DEĞİLDİR → testin koştuğu ve geçtiği aranır.
- "skill yüklendi" inceleme kanıtı DEĞİLDİR → asgari koşuldur, yeterli değil.
- Uyarmak yetmez, bloklamak gerekir; yoksa gerekçe yazdırmak bürokrasidir.

Bloklanan tur KAPANMAZ ('stop' yazılmaz). Yazılsaydı bir sonraki değerlendirme
boş pencere görür ve kanıtsız düzenlemeler sessizce geçmiş tura gömülürdü
(Codex ölçümü 2026-08-12).

## `bin/incele.py` — merge yolu (bağımsız inceleme)

Diff'i Codex'e (farklı satıcı, farklı kör nokta) inceletir, bulguyu P0/P1/P2
ayırır, PR'a karar biçiminde yorum düşer. **P0 varsa merge REDDEDİLİR; P1
bloklamaz, kararı insana taşır.** `deny` sınıfı her zaman insana gider.
`auto` risk + P0 yok + CI yeşil ise `--merge` ile birleştirir.

Fail-closed: çıktı ayrıştırılamazsa ENGEL — "okunamadı" ≠ "temiz". Biçim
bozuksa BİR KEZ daha sorulur; zaman aşımı/çağrı hatası tekrarlanmaz (bütçeyi
ikiye katlardı). Merge komutu incelenen head SHA'ya sabitlenir
(`--match-head-commit`): inceleme sonrası dala eklenen commit aynı hükmü
devralmaz.

Bütçe `INCELE_BUTCE` (varsayılan 900s) — diff boyutuna göre ölçeklenmez;
ölçüm boyutun sürücü olmadığını gösterdi (4.4KB→147s, 9.0KB→156s). Zaman
aşımında ilk bakılacak yer asılı `codex exec` sürecidir.

Diff inceleyiciye TALİMAT veriyorsa (enjeksiyon şüphesi) hüküm otomatik merge
için yeterli sayılmaz — ENGEL değil İNSAN, çünkü aracın kendi format dizesini
içeren meşru PR'lar da eşleşir ve ENGEL kalıcı öz-blok üretirdi.

### Döngünün sonu

Ölçüm 2026-08-12: 9 PR'da 62 tur, ~17 saat, 62 hükmün 2'si temiz — her tur
birikmiş diff'i yeniden inceliyordu. Üç çıkış:
- **artımlı diff** — son incelenen SHA'dan beri; P0 görülmüş PR'da KAPALI.
- **tur tavanı** — `INCELE_TUR_TAVANI` (varsayılan 3); aşılınca ENGEL İNSAN'a
  döner, asla `merge` üretmez, `deny`/kırmızı CI'ı gevşetmez.
- **dal kıpırdamadıysa yeniden inceleme yok.**

Sayaç PR yorumundaki markerdadır; kaybolursa sıfırlanır — fazladan inceleme,
açılan merge değil (`bin/tur.py`).

## `bin/kalite.py --check` — kod kalitesi ratchet'i (ADR-0004)

Dosya/fonksiyon boyutu, karmaşıklık ve borç işaretlerini deterministik sayar.
Mevcut borç kabul edilir, **büyümesi bloklanır**. Taban
`.agents/kalite-baseline.json` (proje sahibi; motor ezmez). Tabanı yükseltmek
bilinçli karardır, gerekçesi commit mesajına yazılır.

## Muafiyet sözleşmesi

`.agents/secret-allowlist.txt` — her satır `yol-deseni  # gerekçe`.
**Gerekçe zorunludur**; gerekçesiz satır kullanım hatasıdır (exit 2), "temiz"
değildir. Bastırılan bulgu çıktıda `muaf:` etiketiyle GÖRÜNÜR kalır — sessiz
susturma, kapının olduğu ama korumadığı hâldir. **Kapsam kapı bazındadır**:
işaretsiz satır yalnız secret kapısına uygulanır; başka kapı için gerekçe
`kapı: pii` (ya da `kapı: hepsi`) ile başlar.

## Test kapsamı daralmaz

`validate.py` testleri koşmadan önce KEŞFEDER; bir test dosyası import'ta
çökerse ya da keşif desenine uymuyorsa kesilir. Gerekçe: eksilen test kırmızı
testten tehlikelidir — kırmızı bağırır, yok olan test yalnız "Ran N"i sessizce
küçültür (ölçüm 2026-08-07: PyYAML'sız yorumlayıcıda 220 yerine 186).

Ortam bağımlılığı `tests/ortam.py` üstünden GÖRÜNÜR atlamaya çevrilir ve
`tests/test_ortam.py` eksik ortamı tek bir yüksek sesli hataya bağlar.
Paylaşılan yardımcıyı import eden test önce `tests/` dizinini `sys.path`'e
ekler — yoksa `python3 -m unittest tests.test_x` ModuleNotFoundError verir ve
okuyan "test bozuk" sanar (bekçi: `TekModulImportTest`).

Keşif kuralı METİN DESENİ değil `ast` + `tokenize` ile uygulanır: desen beş
turda beş kez sızdı (takma adlı taban, `async def test_*`, dış taban, fixture
string'i, `self` olmayan ilk parametre). Deseni büyütmek her seferinde yeni
kaçak bıraktı; çözüm dili kendi aracıyla okumaktı (`bin/kapsam_bekcisi.py`).

## Skill doğrulayıcı sözleşmesi (ADR-0003)

`check_*` / `scan_*` önekli skill script'i KAPI doğrulayıcısıdır ve en az bir
kapıya bağlanmak zorundadır (`validate.py` bağlanmamışı reddeder). Yazılmış
ama çağrılmayan doğrulayıcı = kural belgede var sistemde yok (2026-08-05
bulgusu: 3 doğrulayıcı yazılmış, 0'ı çağrılıyordu). Diğer adlar yardımcı
araçtır (ör. `contrast_check.py` — elle renk çifti alır, diff üstünde koşamaz).

## Kernel senkronu çift yönlüdür (ADR-0002)

`/auras` kanonikten projeye taşır; kurulum ÖNCE kaynağı upstream'e ileri
sarar, saramazsa ENGEL — eski çalışma ağacından kurmak bağlı repoya eski
motoru "güncel" damgasıyla yayardı (2026-08-15 ölçümü). Ezme kararı manifest'e
DEĞİL kanonik git geçmişine dayanır: manifest yanılabiliyordu (2026-08-05,
4cast'te projenin kendi içeriğini "el değmemiş" sanıp yerel düzeltmeyi ezmek
üzereydi). Güvenilir ayraç: hedefin içeriği kanonik geçmişte HİÇ görülmediyse
o yerel iştir. Ters yön `bin/auras_geri.py` (commit insanındır).

## Router (UserPromptSubmit) — kapı DEĞİL

Skill yönlendirmesini her isteğe enjekte eder. Proje hook'u
(`.claude/settings.json`, repoyla taşınır) + kullanıcı-global yedek
(`--global-fallback`, proje hook'u varsa susar). **Router asla bloklamaz**
(hatada sessiz exit 0) — kapı değil, pusuladır.

Enjeksiyon TALİMAT taşır, GEREKÇE taşımaz: maliyeti tur sayısıyla çarpılır.
Tavan bekçisi `tests/test_baglam_butcesi.py`; gerekçenin yeri AGENTS.md
"Davranış sözleşmesi" bölümüdür.

## Bilinen açık

Private repo + Free plan'da dal koruması kapalıdır; koruma yerel kanca +
CI'dır. `kernel` required check yapılamadığı sürece **uzak bütünlük sınırı
yoktur** ve bu açık P1 olarak görünür kalır. Repo public olur ya da Pro
alınırsa ilk iş budur.
