---
name: auras
description: Bir projeyi AurasAgents çalışma sistemine bağlar — AGENTS.md kuralları, capability profilleri, iş sözleşmesi formu, CI kanıt üretimi, push kapısı ve Codex risk sinyali kurulur. Kullanıcı "/auras", "bu projeyi bağla", "sisteme al", "kur" dediğinde veya yeni/boş bir projede çalışma sistemi istendiğinde kullan. Zaten bağlı projede eksikleri tamamlar. Günlük geliştirme işinde kullanma.
---

# auras — projeyi sisteme bağla

Çekirdek kaynak: `~/Developer/GitHub/AurasAgents` (kanonik şablon).

## Prosedür

1. Hedef klasörü doğrula: kullanıcının bulunduğu proje klasörü. Kaynak reponun
   kendisiyse dur — orada zaten kurulu.
2. Kurulum motorunu çalıştır:
   `bash ~/Developer/GitHub/AurasAgents/bin/auras-init.sh`
   Var olan dosyaları ezmez; eksikleri tamamlar, kancayı kurar, doğrulamayı koşar.
3. Projeyi tanı ve `AGENTS.md`'yi ona göre uyarla — şablonu olduğu gibi bırakma:
   - Dil/framework, test/lint/build komutları
   - Riskli path'ler (auth, ödeme, migration, secret) → risk tablosunun
     `deny` ve `approval` satırlarını bu projeye göre doldur
   - Repoya özgü konvansiyonlar ve tuzaklar
   `CLAUDE.md`'ye projenin gerçek komutlarını yaz.
4. `.github/workflows/evidence.yml` içindeki check listesine projenin gerçek
   komutlarını ekle (typecheck/lint/test/build). Var olan CI'ı silme, yanına ekle.
5. `python3 bin/validate.py` koş — geçmeden bitmiş sayma.
6. GitHub bağlantısı: uzak repo yoksa kullanıcıya sor (private öner), onay
   alırsan `gh repo create <ad> --private --source=. --remote=origin --push`.
   Onay almadan repo oluşturma veya push etme.
7. Kapanışta kullanıcıya sade özet ver: ne kuruldu, CI yeşil mi, sırada ne var.

## Gotcha'lar

- Boş projede bile AGENTS.md'yi genel bırakma; genel kural = uygulanmayan kural.
- Mevcut projelerde eski yapılandırma varsa (ör. Agent Ofis `projects/*.yml`)
  bilgiyi mekanizmaya taşı: forbidden→hook/deny kuralı, conventions→AGENTS.md,
  routing→capability profili. Düz metne kopyalayıp geçme.
- Kurulum tek iştir; proje koduna davranış değişikliği karıştırma.
- Private repo + Free plan'da GitHub dal koruması çalışmaz; koruma yerel
  pre-push kancası + CI'dır. Bunu kullanıcıya söyle, sessiz geçme.

## Eval

Kurulum sonrası ölçüt: `python3 bin/validate.py` geçiyor, ilk push'ta CI
`evidence.json` üretiyor ve kullanıcı hiçbir git komutu yazmadan iş verebiliyor.
