---
name: implement-change
description: Contract'lı kod değişikliğini spec-anchored TDD döngüsüyle uygular. Issue form'da kabul kriterleri (EARS) tanımlı bir code-change işi başladığında kullan. Araştırma, salt inceleme veya doküman işinde kullanma.
---

# implement-change

## Prosedür

1. Contract'ı oku: hedef, EARS kriterleri, kapsam (izinli path'ler), zorunlu kanıt.
2. Kapsam dışı hiçbir dosyaya dokunma. Kapsamın yetmediğini görürsen durup
   contract güncellemesi iste — kendi başına genişletme.
3. Her EARS kriterini bir teste çevir ("X olduğunda sistem Y yapmalı" → test case).
4. TDD döngüsü: failing test yaz → koş, RED gör → minimum kodu yaz → GREEN gör
   → küçük tek amaçlı commit. Kriter başına en az bir döngü.
5. Testlere dokunmadan yeşile getir; test değiştirmen gerekiyorsa nedenini PR
   gövdesine yaz.
6. Bitişte kanıt topla: test çıktısı, koşulan komutlar ve sonuçları; UI işiyse
   ekran görüntüsü. "Bitti" beyanı tek başına geçersizdir.
7. PR aç: gövdede contract ID + kriter→test eşlemesi. CI `evidence.json` üretir.

## Gotcha'lar

- RED aşamasını atlama: testin gerçekten başarısız olduğunu görmeden yazılan
  test, hiçbir şeyi kanıtlamaz.
- Diff auth/ödeme/migration path'ine dokunursa risk yukarı eskale olur —
  bunu görmezden gelip devam etme, akış approval'a döner.
- Mevcut kod stilini taklit et; bu repo için tr-TR yorum, İngilizce tanımlayıcı.

## Eval

`tests/` altındaki kernel testleri + gerçek işlerde kriter→test eşleme oranı.
Skill Lift ölçümü: bu skill'le/skill'siz koşuların First-pass Acceptance kıyası.
