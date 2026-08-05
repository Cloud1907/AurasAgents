# ADR-0002 — Kernel senkronu çift yönlü; ezme kararı git geçmişine dayanır

**Tarih:** 2026-08-05
**Durum:** Kabul edildi
**Bağlam belgeleri:** ADR-0001, `VIBE_CODING_TASARIM_TEMMUZ_2026.md` §12

## Bağlam

`/auras` tek yönlüydü: kanonik → proje. Bağlı projelerde 26 Tem – 5 Ağu
arasında gerçek kullanım oldu (4cast 378, AurasStock 58 yönlendirilmiş istek)
ve kernel iyileştirmeleri **orada** üretildi — kanonikte olmayan 24 dosya
sapması, aralarında `bin/kapi.py` yanlış-pozitif düzeltmesi, fail-open bekçisi
ve iki yeni skill. Geri taşıma yolu olmadığı için bu iş mahsur kalıyordu.

Ayrıca ezme kararı `.agents/.kernel-manifest.json`a dayanıyordu: "manifest
hash'i hedefin mevcut hash'ine eşitse dosya el değmemiştir → güvenle
güncellenir". 4cast'te manifest projenin **kendi** içeriğini kaydetmişti;
bir sonraki `/auras` yerel düzeltmeyi sessizce ezecek ve çıktıda yalnız
`guncellendi:` satırı görünecekti.

## Karar

1. **Ezme ayracı manifest değil kanonik git geçmişidir.** Hedefteki içerik
   kanoniğin herhangi bir geçmiş sürümüne eşitse → `geride`, güvenle
   güncellenir. Kanonik geçmişte hiç görülmemişse → `yerel`, **ezilmez**.
   Geçmiş okunamıyorsa varsayılan korumaktır (veri kaybı > eskilik).
2. **Ters yön açıldı:** `bin/auras_geri.py` sapmayı sınıflandırır, farkı
   gösterir ve `--al` ile kanonik **çalışma ağacına** kopyalar. Commit ve
   inceleme insanındır; araç otomatik kalıcılaştırmaz (hafıza otoritesi:
   kalıcılaştırma reviewed PR ile).
3. **Motor listesinin tek tanımı** `bin/kernel_dosyalari.py`. `auras-init.sh`
   ve `validate.py` oradan okur; ikinci kopya `validate.py` bekçisiyle
   reddedilir.

## Reddedilen alternatifler

- *Manifest'i düzeltmek:* manifest yalnız son senkronu bilir, yerel
  authorship'i bilemez — aynı hata sınıfı geri gelir.
- *Yerel değişikliği hiç güncellememek:* projeler kalıcı olarak eskir; sapma
  görünmez birikir.
- *Otomatik PR açmak:* kernel değişikliği `approval` sınıfıdır; agent kendi
  kernel işini onaylayamaz (AGENTS.md).

## Sonuçlar

- `/auras` çıktısı korunan her dosya için geri-taşıma komutunu basar; sapma
  sessiz kalamaz.
- Açık kalan: `MOTOR_DIZIN` içindeki `tests` bütünüyle motorun sayılıyor, ama
  projeler kendi testlerini de oraya koyuyor (4cast'te `setup_test_db.sh`,
  `test_db_ek_ddl.sql` `yerel` görünüyor). Sınır ayrımı ayrı iştir.
