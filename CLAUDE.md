@AGENTS.md

# Claude adapter notları

- Yukarıdaki AGENTS.md kanonik kaynaktır; bu dosya yalnız Claude-özel ayarları taşır.
- Kesin yasaklar (deny path'leri) bağlam değil mekanizmadır — hook/permission
  katmanında uygulanır; AGENTS.md'deki tablo referanstır.
- Kernel doğrulama: `python3 bin/validate.py` (her değişiklikte koş).
- Kanıt üretimi lokal deneme: `python3 bin/make_evidence.py --out /tmp/evidence.json`
- Skill'ler `.claude/skills` üzerinden görünür (`.agents/skills`'e symlink);
  yeni skill eklerken symlink'i bozma, `.agents/skills/` altına yaz.
- Skill yönlendirmesi iki katmanlıdır:
  - Proje: `.claude/settings.json` UserPromptSubmit hook'u projenin
    `bin/route.py`'sini çalıştırır (repoyla taşınır, `auras-init.sh` kurar).
  - Global yedek: `~/.claude/settings.json` kanonik route.py'yi
    `--global-fallback` ile çağırır — bağlı olmayan projelerde de yönlendirir,
    projenin kendi hook'u varsa sessizce çekilir (çift yönlendirme olmaz).
  Tablo sırası: proje `.agents/routing.yml` → kanonik AurasAgents tablosu.
  Elle deneme: `echo '{"prompt":"..."}' | python3 bin/route.py`
  Hook yeni eklendiyse çalışan oturum görmeyebilir — `/hooks` aç ya da
  Claude Code'u yeniden başlat.
