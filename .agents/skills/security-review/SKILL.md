---
name: security-review
description: Diff'i OWASP temelli denetler; erişim kontrolü, injection, secret sızıntısı, misconfig arar. Diff auth/kimlik/ödeme/upload/migration yüzeyine dokunduğunda veya risk sınıfı approval/deny olduğunda kullan. Genel kod kalitesi incelemesi için kullanma.
---

# security-review

## Prosedür

1. Diff'in dokunduğu yüzeyi sınıfla: erişim kontrolü / injection yüzeyi /
   kimlik-oturum / secret-config / bağımlılık.
2. Her sınıf için kontrol listesi:
   - Erişim: IDOR, tenant sızıntısı, yetkisiz endpoint, eksik authorize.
   - Injection: SQL/XSS/path traversal/upload doğrulama.
   - Kimlik: token ömrü, oturum sabitleme, parola/secret loglanması.
   - Config: CORS, header'lar, rate-limit, debug bayrakları.
   - Bağımlılık: yeni paketin bilinen CVE'si, sürüm sabitleme.
3. Her bulgu dosya:satır + somut istismar senaryosu ile yazılır — "olabilir"
   değil "şöyle sömürülür".
4. Hüküm: CRITICAL/HIGH bulgu = merge durur (veto). MEDIUM/LOW = PR'a not,
   merge kararı insanda.

## Gotcha'lar

- Bulgu üretme baskısıyla gürültü yapma: yalnız doğruluğu/güvenliği gerçekten
  etkileyen bulguları raporla; teorik/erişilemez senaryoları "bilgi" olarak ayır.
- Kendi yazdığın kodu denetliyorsan bu skill geçersizdir — taze bağlamlı ayrı
  koşu ister.

## Eval

Bilinen-açıklı örnek diff seti (`tests/` altına eklenecek) üzerinde
yakalama oranı; yanlış-pozitif oranı gürültü eşiği olarak izlenir.
