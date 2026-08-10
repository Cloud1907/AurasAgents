---
name: grilling
description: Belirsiz kapsamlı bir planı, kararı veya fikri karar-ağacı yöntemiyle acımasızca sorgulayarak netleştirir — her turda cevaplanabilir tüm soruları önerili cevaplarıyla sorar, kapsam netleşene dek sürer. YALNIZ kullanıcı açıkça istediğinde kullan ("beni sorguya çek", "planımı stres testine sok", "beni grill'le", "/grilling"); açık istek yokken ASLA kendiliğinden başlatma. Net kapsamlı işte, kod yazan/dosya değiştiren işte kullanma.
---

# grilling — plan sorgulama (opt-in)

Amaç: belirsiz kapsamı, kullanıcıyı yormadan ama hiçbir varsayımı sessiz
bırakmadan **paylaşılan anlayışa** çevirmek. Çıktı bir karar değil, netleşmiş
bir karar ağacıdır; iş sözleşmesine (EARS kabul kriterleri) hammadde üretir.

Uyarlama kaynağı: [mattpocock/skills `grilling`](https://github.com/mattpocock/skills)
(MIT). Yöntem korunmuş, sistem kurallarına bağlanmıştır.

## Ne zaman geçerli

- Kullanıcı AÇIKÇA istedi: "beni sorguya çek", "beni grill'le", "planımı
  stres testine sok", ya da doğrudan "/grilling". Soru biçimi de istektir
  ("çeker misin?"). Açık istek tek kapıdır:
  kullanıcının "ara soru sorma" iletişim tercihi varsayılandır; bu skill'i
  istemek o tercihi o oturum için bilinçli askıya almaktır. Router yalnız bu
  açık istek ifadelerini yönlendirir (skill seçimi takdire bırakılmaz —
  AGENTS.md); bu ifadeler yokken kendiliğinden başlatma.
- Kapsam gerçekten belirsizken (AGENTS.md: plan mode tetiği ile aynı eşik).

## Ne zaman geçerli DEĞİL (negatif tetik)

- Kullanıcı istemeden. Soru yağmuru varsayılan davranış değildir.
- Kapsam zaten netse (diff tek cümleyle tarif edilebiliyorsa → micro iş).
- Kod/dosya değişikliği → `implement-change`. Bu skill hiçbir dosyaya yazmaz;
  çıktısı yazışmadaki karar ağacı ve istenirse EARS taslağıdır.
- İki modelin tartışması istenmişse → `codex-debate` (o skill modeli
  tartıştırır; bu skill kullanıcıyı sorgular — karıştırma).

## İş akışı

1. **Konuyu karar ağacı olarak modelle.** Her karar, ona bağlı alt kararları
   dallandırır. Ağaç zihinsel modeldir; kullanıcıya diyagram dayatma.
2. **Frontier'ı hesapla.** Frontier = ön koşulu ÇÖZÜLMÜŞ olduğu için ŞİMDİ
   sorulabilecek soruların tamamı. Cevabı bu turda açık başka bir soruya
   bağlı olan soru frontier'da değildir — sonraki tura kalır.
3. **Turu tek seferde sor.** Frontier'daki TÜM soruları numaralı ve önerili
   cevaplı sor, sonra kullanıcının cevaplarını bekle. Biçim:

   ```
   ❓ **S1 — <soru başlığı>**: <gövde; gerekirse çok paragraf, çoktan seçmeli olabilir>

   ➡️ <senin önerdiğin cevap>
   ```

4. **Olguyu kendin bul, kararı kullanıcıya bırak.** Ortamdan öğrenilebilecek
   şeyi (dosya sistemi, kod, araç çıktısı) kullanıcıya sorma — kendin bak,
   gerekirse `research-analyst` alt-ajanına ver. Süren keşif çözülmemiş ön
   koşuldur: yalnız ona bağlı sorular bekler, frontier'ın kalanını şimdi sor.
5. **Her cevaptan sonra ağacı yeniden şekillendir.** Çözülen karar frontier'ı
   dışa iter; yeni turu hesapla ve sor.
6. **Bitiş: frontier boş.** Her dal gezildi, hiçbir varsayım sessiz kalmadı.
   Kullanıcı "anlaştık" demeden hiçbir aksiyona geçme. İş devam edecekse
   sonucu EARS kabul kriteri taslağına çevirmeyi öner (iş sözleşmesi formuna
   girer) — bu öneridir, dayatma değil.

## High-signal gotcha'lar

- **Bağımlı soruyu erken sorma.** Cevabı başka açık soruya bağlı soruyu aynı
  turda sormak kullanıcıya tahmin yaptırır — yöntemin ana hatası budur.
  Şüphedeysen soruyu sonraki tura bırak.
- **Öneri vermeyen soru eksiktir.** Her soruya kendi önerini ekle (➡️).
  Öneri, kullanıcının "evet/hayır/şu" diye hızlı cevaplamasını sağlar;
  önerisiz soru yağmuru sorgu değil anket olur.
- **Olgu sorusu kullanıcıya gitmez.** "Hangi dosyada?" tipi soru senin işin;
  kullanıcıya yalnız KARAR sorulur. Karışırsa oturum yorucu olur ve
  kullanıcının "ara soru sorma" tercihini gerçekten ihlal etmeye başlarsın.
- **Turu parçalama.** Frontier'daki soruları teker teker sormak tur sayısını
  şişirir; tamamını tek mesajda numaralı sor.
- **Sessiz varsayım bitirme sayılmaz.** "Kalanını ben varsaydım" diyerek
  kapatmak yöntemin inkârıdır; varsayım yapacaksan onu da soru olarak yaz ve
  onayını al.
- **LLM cevabı kanıt değildir.** Sorgu sırasında ürettiğin öneriler risk
  sinyalidir; kullanıcı onayladı diye olgusal doğruluk kazanmaz
  (kanıt > beyan — AGENTS.md).

## Eval

1. **Pozitif — açık çağrı.** Girdi: "yeni bildirim sistemini nasıl
   kurgulayacağımı bilmiyorum, beni sorguya çek." Beklenen: karar ağacı
   kurulur, ilk frontier turu numaralı + önerili cevaplı gelir, cevap
   beklenir; tek mega-soru veya hemen çözüm önerisi GELMEZ.
2. **Süreç — frontier disiplini.** Tur 1'de "push mu e-posta mı" açıkken
   "push sağlayıcısı hangisi" sorusu SORULMAZ; kullanıcı "push" deyince
   sağlayıcı sorusu tur 2'de gelir.
3. **Negatif — kendiliğinden tetiklenme yok.** Girdi: "bu bug'ı düzelt."
   Beklenen: grilling devreye GİRMEZ (`implement-change` işidir); belirsizlik
   olsa bile en fazla tek netleştirme sorusu sorulur, sorgu oturumu açılmaz.
4. **Negatif — olgu sorusu kullanıcıya gitmez.** Sorgu sırasında "X nerede
   tanımlı" ihtiyacı doğarsa kullanıcıya sorulmaz, koda bakılır/alt-ajana
   verilir; kullanıcıya yalnız karar soruları düşer.
