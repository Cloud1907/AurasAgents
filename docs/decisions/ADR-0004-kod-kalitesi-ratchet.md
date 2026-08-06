# ADR-0004 — Kod kalitesi deterministik ölçülür, ratchet ile kilitlenir

**Tarih:** 2026-08-06
**Durum:** Kabul edildi
**Bağlam belgeleri:** ADR-0003, `kernel-work` skill'i, Agent Ofis `ofis-metrics` deseni

## Bağlam

Teslim standardı denetlendiğinde (2026-08-06) şu çıktı: kapı zinciri test
kanıtı, tıklama kanıtı, risk incelemesi ve secret taramasını zorluyordu ama
**kod kalitesi için tek bir sayı yoktu**. `.claude/rules/` altındaki 92
satırlık konvansiyon ve skill metinleri normatifti, hiçbir kapı okumuyordu.

Ölçülmeyen kuralın standardı yoktur, tercihi vardır: aynı sistem farklı bir
gün, farklı bir modelle çok daha zayıf kod üretebilir ve hiçbir kapı fark
etmez.

## Karar

1. **`bin/kalite.py` — deterministik sayaç.** LLM yorumu üretmez, sayar:
   `buyuk_dosya`, `uzun_fonksiyon`, `karmasik_fonksiyon` (dal sayısı),
   `borc_isareti` (TODO/FIXME/XXX/HACK), `debug_artigi`.
2. **Ratchet — mevcut borç kabul, büyümesi yasak.** `.agents/kalite-baseline.json`
   sayaçları dondurur; `--check` herhangi bir sayacın tabanı aşmasında exit 1.
   Düşürmek serbest. Tabanı yükseltmek mümkün ama **bilinçli** ve gerekçesi
   commit'te.
3. **CI'da blocking**, `evidence.json`'a `kod-kalitesi` check'i olarak girer.
4. **Eşik ve taban proje sahibidir** (`.agents/kalite.yml`,
   `.agents/kalite-baseline.json`) — motor listesinde değil; `/auras` ezmez.
   Aracın kendisi motordur, herkese aynı ölçüm gider.
5. **Kapsam dürüstlüğü zorunlu.** Fonksiyon analizi yalnız Python (girinti) ve
   süslü-parantezli dillerde yapılır. Her rapor kaç dosyanın analiz edildiğini,
   kaçının yalnız satır sayıldığını yazar. "Hepsini ölçtüm" demek yasak.

## Reddedilen alternatifler

- *Sert eşik (ratchet yok):* mevcut kernel 24 bulgu taşıyor; sert eşik ilk
  gün her PR'ı bloklar → eşik gevşetilir → kapı ölür. Ratchet borcu kabul
  edip yönünü kilitler.
- *LLM'e kalite puanı verdirmek:* yorumsal skor kapı olamaz (AGENTS.md:
  LLM incelemesi risk sinyalidir, kanıt değildir).
- *Dış linter'a bağlanmak (eslint/ruff):* dil başına kurulum ve sürüm
  bağımlılığı getirir; kernel bağımlılıksız kalmalı. Proje kendi linter'ını
  `proje-kapisi`'na ekleyebilir (ADR: proje kapısı uzantı noktası).

## Sonuçlar

- Kernel'in kendi borcu artık görünür ve kilitli: 1 büyük dosya
  (`bin/validate.py` 601 satır), 9 uzun fonksiyon, 14 karmaşık fonksiyon,
  4 borç işareti. Bunlar düşürülmeli — ama önce büyümeleri durdu.
- Ölçüm doğrulandı: kasten eklenen uzun fonksiyon `uzun_fonksiyon: 9 → 10`
  ile kapıyı düşürdü, geri alınınca yeşile döndü.
- Açık kalan: kopya kod (duplication) ölçülmüyor; güvenilir dil-agnostik
  tespit ayrı iştir.
