# ADR-0003 — Skill doğrulayıcısı bir kapıya bağlanmak zorundadır

**Tarih:** 2026-08-05
**Durum:** Kabul edildi
**Bağlam belgeleri:** ADR-0001, `kernel-work` skill'i ("bekçisiz kural temennidir")

## Bağlam

Sistem 4 doğrulayıcı script'i taşıyordu (`scan_secrets.py` 129,
`check_test_first.py` 163, `check_citations.py` 159, `contrast_check.py` 72
satır). Ölçüm: **hiçbiri hiçbir kapı tarafından çağrılmıyordu.** Tek atıf
`run_event.py`'de bir regex'ti — elle koşulursa "test" saysın diye.

Sonuç: `implement-change` skill'i "test-önce" disiplinini normatif olarak
yazıyor, doğrulayıcısı da yazılmış, ama teslim standardı fiilen "herhangi bir
test koştu ve geçti"ydi. Kalite, kapıdan değil modelin o günkü disiplininden
geliyordu — yani standart değil, tercihti.

## Karar

1. **Adlandırma sözleşmesi:** `.agents/skills/*/scripts/` altında `check_*` ya
   da `scan_*` önekli script bir **kapı doğrulayıcısıdır**. Diğer adlar
   yardımcı araçtır (ör. `contrast_check.py` elle renk çifti alır, diff
   üstünde koşamaz).
2. **Bağlanma zorunluluğu:** her kapı doğrulayıcısı en az bir kapı dosyasında
   (`bin/hooks/pre-push`, `bin/kapi.py`, `bin/validate.py`,
   `.github/workflows/evidence.yml`) çağrılmalıdır. `validate.py`
   `test_skill_validators_wired` bunu reddederek zorlar.
3. **Bağlandığı yerler:**
   - `scan_secrets` → pre-push (blocking) + CI. Sızan secret geri alınamaz.
   - `check_test_first` → tur kapısı (BLOK) + CI (evidence check'i).
   - `check_citations` → tur kapısı, `.agents/reports/` değiştiğinde (UYARI —
     skill'in kendi tanımıyla hakem değil sinyal).
4. **Dışlama kapı konfigünde durur, tarayıcıda değil:** `scan_secrets`
   `--exclude GLOB` alır; kapılar `*/eval/*` geçer. Neyin taranmadığı gizli
   kalamaz.

## Reddedilen alternatifler

- *Skill metnini iyileştirmek:* prose bağlamaz; bu ADR'nin varlık sebebi zaten
  iyi yazılmış prose'un tutmamış olması.
- *Dışlamayı tarayıcıya gömmek (`eval` → SKIP_DIRS):* kapsam daralması sessiz
  olurdu; bağlı projelerin `eval/` dizinlerinde gerçek secret gizlenebilirdi.
- *`check_test_first`'ü UYARI yapmak:* mevcut kapı zaten "test koşmadı"da
  BLOK veriyor; daha zayıf bir eşik standardı geriye götürürdü.

## Sonuçlar

- Yeni skill doğrulayıcı getirdiğinde bağlamadan kernel doğrulaması geçmez.
- Bulgu: bu ADR'nin uygulanması sırasında `scan_secrets` skill'in KENDİ eval
  fixture'ını yakaladı; dışlama olmasa gate her push'u bloklayacaktı. Kapıyı
  bağlamadan önce koşturmak zorunludur.
- Açık kalan: kod kalitesi ölçümü (dosya/fonksiyon boyutu, karmaşıklık,
  kopya) ve ratchet hâlâ yok — ayrı iş.
