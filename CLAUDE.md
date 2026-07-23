@AGENTS.md

# Claude adapter notları

- Yukarıdaki AGENTS.md kanonik kaynaktır; bu dosya yalnız Claude-özel ayarları taşır.
- Kesin yasaklar (deny path'leri) bağlam değil mekanizmadır — hook/permission
  katmanında uygulanır; AGENTS.md'deki tablo referanstır.
- Kernel doğrulama: `python3 bin/validate.py` (her değişiklikte koş).
- Kanıt üretimi lokal deneme: `python3 bin/make_evidence.py --out /tmp/evidence.json`
- Skill'ler `.claude/skills` üzerinden görünür (`.agents/skills`'e symlink);
  yeni skill eklerken symlink'i bozma, `.agents/skills/` altına yaz.
