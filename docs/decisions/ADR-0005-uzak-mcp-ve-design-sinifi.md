# ADR-0005 — Uzak MCP sunucuları ve dördüncü görev sınıfı (`design`)

**Tarih:** 2026-08-16
**Durum:** Uygulandı — uzak MCP ayrımı ve `design` sınıfı YÜRÜRLÜKTE
(profil 2026-08-16'da kullanıcı eliyle konuldu). Yönlendirme AÇIK DEĞİL: sebep
ölçüldü ve `routing.yml` `not_routed`'a yazıldı (bkz. §5)
**Bağlam belgeleri:** AGENTS.md "Skill ve capability mekanizması",
`VIBE_CODING_TASARIM_TEMMUZ_2026.md` §5, ADR-0004

## Bağlam

Kullanıcı MCP'leri tasarım, video, pazarlama ve UI/UX işlerinde kullanmak
istedi. Ölçüm (2026-08-16) iki yapısal engel gösterdi.

**Engel 1 — kernel yalnız YEREL sunucu tanıyor.** `bin/yetki.py` `.mcp.json`
üretirken `tasinabilir` **ve** `komut` alanı arıyordu. Figma, Canva ve Nim
uzak OAuth connector'larıdır: başlatma komutları yoktur. Yani kayda alınsalar
bile üretici onları atlardı — ve bunu *kazayla* yapardı, çünkü ayrımı
adlandıran bir alan yoktu. Sessiz doğruluk sözleşme değildir: `komut` alanı
bir gün varsayılan alsa, kimlik doğrulamalı bir SaaS sessizce repo
yapılandırmasına inerdi.

**Engel 2 — üç görev sınıfı bu işi karşılamıyor.** `code-change | research |
incident` üçlüsü sabit. Tasarım/video/pazarlama işi:
- `research` değil — `research` salt-okunur ve yalnız YEREL MCP'lere açık
  (`codegraph`, `agent-ofis`, `agentmemory`). Figma/Canva/Nim'i oraya koymak,
  HER araştırma turunun yüzeyini kimlik doğrulamalı dış servislere açardı.
- `code-change` değil — repo mutasyonu yok, `tests/lint/build` kanıtı
  üretilemez; o profilin `evidence_required` sözleşmesi karşılanamaz.

## Karar

### 1. `.agents/mcp.yml` → zorunlu `tur: yerel | uzak`

`yerel`: stdio sunucusu, `komut` ile başlatılır, motor `.mcp.json` üretir.
`uzak`: OAuth connector, yapılandırma OTURUM düzeyindedir, **motor üretmez**.

`bin/yetki.py` artık uzak sunucuyu AÇIK bir koşulla eler (`tur != "yerel"` →
`continue`), alan eksikliğine güvenmez. Bekçiler (`tests/test_mcp_kaydi.py`):
- her sunucu `tur` beyan eder,
- `tur: uzak` sunucu `.mcp.json`'a **inemez**,
- `tur: uzak` sunucu `tasinabilir: true` olamaz — taşınacak yapılandırma yok.

Kayıt uzak sunucuyu yine de **yönetir**: amaç, görev sınıfı, ağ beyanı ve
profil sınırı kayıtta durur. Yönetmek ile kurmak ayrı şeylerdir.

### 2. Dördüncü sınıf: `design`

Sınıfın adı KONU, sınırı YETENEK. Bu sınıfı diğer üçünden ayıran şey "tasarım
hakkında olması" değil, **kimlik doğrulamalı dış üretken SaaS çağırması**ve
**repoya yazmaması**dır. Kural tek cümle: *repoya yazan tasarım işi `design`
değil `code-change`'tir* — ve routing bunu zaten öyle yapıyor
(`designing-interfaces` → `code-change`).

Bu ayrım bilinçlidir çünkü konu bazlı okunan sınıf çöp kutusuna döner:
"tasarımla ilgili" her iş oraya akar ve salt-okunur sınır, kimlik doğrulamalı
SaaS erişimiyle birleşerek sessizce genişler.

### 3. Sınıf listesinin tek tanımı

Liste dört ayrı yerde elle tekrarlanıyordu (`validate.py` üç nokta +
`tests/test_mcp_kaydi.py`), issue form ve profiller de aynı kümeyi ayrıca
beyan ediyordu. Artık tek tanım `bin/dogrula_sema.py::GOREV_SINIFLARI`.

O modül ayrıca `test_profiles` ve `test_issue_form`'u `validate.py`'den
devraldı (`dogrula_ci.py` emsali): `validate.py` 922/922 ile ratchet tabanının
tam üstündeydi ve tek satır büyüyemiyordu. Taban yükseltilmedi, borç ödendi —
922 → 878.

### 4. `design` neden yürürlükte DEĞİL

`.agents/capability-profiles/**` `permissions.deny` yüzeyindedir
(`bin/yetki.py::YASAK_YAZMA`): **ajan kendi yetki sınırını yazamaz.** Profil
dosyasını yazma denemesi motor tarafından reddedildi ve bu doğru davranıştır.
Kabuk üzerinden dolanmak mümkündü (AGENTS.md bu sınırı zaten yazıyor) ama
yapılmadı: bir kuralı, tam da engellemek için var olduğu durumda dolanmak,
kuralı yok etmektir.

Yürürlüğe girmesi için `design.yml`'ı **insan eli** koymalıdır. Sonrasında
tek satırlık değişiklikle açılır: `GOREV_SINIFLARI`'na `"design"`.

## Sonuçlar

**Kazanç.** Uzak connector'lar yönetime girebilir hâle geldi; sınıf listesi
tek kaynak oldu; `validate.py` 44 satır borç ödedi.

**Bedel.** `VIBE_CODING_TASARIM_TEMMUZ_2026.md` §5 üçlüyü sayıyor ve o belge
"Codex mutabakatlı". Dördüncü sınıf tek taraflı bir değişikliktir; bu ADR onu
kayda geçirir ve gerekçesini taşır. Belge sınıf açıldığında güncellenmelidir.

**Kalan sınır.** MCP yapılandırması OTURUM genelindedir; `mcp:` alanı hangi
sınıfın hangi sunucuyu kullanmasının DOĞRU olduğunu söyler, motor bunu tur
başına zorlayamaz. `design` sınıfı bu sınırı değiştirmez.

**Kapı değil yetenek.** `docs/yasam-dongusu-kapsami.md` tasarım aşamasında
kapı OLMADIĞINI yazıyor. Bu ADR onu değiştirmez: Figma/Canva/Nim kapı
getirmez, yetenek getirir. O satır ancak bir doğrulayıcı kapıya bağlandığında
değişir (ör. `contrast_check.py` — yazılı, hâlâ bağlı değil).

## 5. Ek karar (aynı gün) — sınıfın kaynağı ve açık kalan yönlendirme

**Sınıfın kaynağı `routing.yml` oldu.** `design.yml` eklenince İKİ sessiz
kayma ölçüldü: `research-with-evidence` incident → design, `security-review`
None → code-change. Hiçbir profile dokunulmamıştı; sınıf
`sorted(os.listdir())`'in İLK elemanından türetiliyordu ve yeni dosya adı
("design") alfabede öne geçmişti. Aynı şans `implement-change`i doğru
gösteriyordu ("code-change" < "incident") — test yeşildi, mekanizma yanlıştı.

`skill_task_class` artık önce `routing.yml`'deki ilk kurala bakar (yazarın
gözden geçirilmiş beyanı), yalnız kuralsız skill'de profile düşer ve birden
çok profilde geçiyorsa None döner. Bekçi: `test_sinif_profil_ALFABESINE_bagli_degil`.

**Yönlendirme AÇILDI (aynı gün, ayrı PR).** Önce kural yazıldı, canlı denendi
ve geri alındı: `bin/niyet.py::_okuma_sinifi` `"research"`i TEK salt-okunur
sınıf sayıyordu ve okuma niyetli her kuralı oraya düşürüyordu — `design`
profilindeki chrome-devtools'u kaybeden bir SEO kuralı olurdu. Çalışmayan ama
çalışır görünen yönlendirme yayınlanmadı; sebep `routing.yml`'e yazıldı.

Sonra sebep giderildi. Salt-okunur sınıf kümesi artık profillerin KENDİ
beyanından okunuyor (`tools.filesystem == "read-only"` →
`skill_kayit.salt_okunur_siniflar`), sabit listeden değil. Düşürme kuralı İKİ
YÖNLÜ ve daima kısıtlayıcı:

  · salt-okunur sınıftaki kural KENDİ sınıfını korur (design aracını kaybetmez),
  · yazma sınıfındaki kural EN KISITLI salt-okunur sınıfa (`research`) iner —
    `design`e indirmek, kısıtlama adı altında dış SaaS yetkisi vermek olurdu.

Bekçi: `tests/test_niyet_salt_okunur.py` (13 vaka; RED önce görüldü). Canlı:
`seo denetimini yap` → `design`, `kod yaz` → `code-change`,
`bunu araştır` → `research`, `prod çöktü` → `incident`.

**Bedel — `route.py` bölündü.** Bu değişiklik `route.py`'yi 399'dan 406 satıra
çıkardı ve ratchet'i deldi; dosya zaten haftalardır pusulada "sıradaki duvar"
olarak duruyordu (`bin/marj.py`). Enjeksiyon METNİ `bin/enjekte.py`'ye ayrıldı
(route.py 317). Bir bekçi bu taşınmayı yakaladı ve bu doğru davranıştı —
`"karsilama_kayitlari" in route.py` diyen kontrol, davranış hiç değişmediği
hâlde kırmızı yandı. Bekçi kuralı ölçecek biçimde düzeltildi: artık ROUTER
KATMANINA bakıyor (`route.py` + `enjekte.py`), dosya yerleşimine değil.
