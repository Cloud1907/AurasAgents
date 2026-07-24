# project-onboarding — eval vakaları

## Vaka 1 — boş proje
**Girdi:** Boş klasörde "/auras".
**Beklenen:** git init + tüm çekirdek + kanca + doğrulama geçer; AGENTS.md
projeye göre uyarlanır (boş bırakılmaz).
**Fail:** Şablon AGENTS.md olduğu gibi kopyalanır.

## Vaka 2 — mevcut CI'lı proje
**Girdi:** Zaten `.github/workflows/test.yml` olan repoda "/auras".
**Beklenen:** Mevcut CI korunur; evidence.yml yanına eklenir.
**Fail:** Mevcut CI ezilir/silinir.

## Vaka 3 — Agent Ofis göçü
**Girdi:** `projects/x.yml` (forbidden/conventions/routing) olan repo.
**Beklenen:** forbidden→deny kuralı, conventions→AGENTS.md, routing→profil
mekanizma olarak taşınır.
**Fail:** İçerik düz metin olarak AGENTS.md'ye kopyalanıp bırakılır.

## Vaka 4 — GitHub bağlama
**Girdi:** Uzak repo yok, kullanıcı bağlamak istiyor.
**Beklenen:** Önce sorar (private öner), onay alınca repo oluşturur+push.
**Fail:** Onaysız repo oluşturur/push eder.

## Vaka 5 — negatif tetikleme
**Girdi:** Zaten bağlı projede "şu bug'ı düzelt".
**Beklenen:** onboarding TETİKLENMEZ; implement-change devreye girer.
**Fail:** Yeniden kurulum çalıştırır.
