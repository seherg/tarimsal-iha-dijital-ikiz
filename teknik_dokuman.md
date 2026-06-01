# Teknik Döküman — Tez Yazım Rehberi
**Öğrenci:** Seher GÜMÜŞAY (241137106)  
**Danışman:** Doç. Dr. Fatih ÖZYURT  
**Program:** Yazılım Mühendisliği YL — Fırat Üniversitesi  
**Tez Başlığı:** Tarımsal İlaçlama İnsansız Hava Araçları için Olay Güdümlü ve Enerji Odaklı Dijital İkiz Tabanlı Karar Destek Mimarisi  
**Son güncelleme:** 2026-05-31

---

## 1. FORM 30 / FORM 31 İLE KODUN ÇELIŞTIĞI NOKTALAR

Bunlar savunmada sana sorulabilecek, tezde mutlaka açıklanması gereken farklılıklardır.

---

### 1.1 Rotor Sayısı — KRİTİK

**Form 31 İP-2:** *"Dört rotorlu, değişken kütleli çok rotorlu model"*  
**Kod:** `config.yaml → rotor.sayi: 6` — hexarotor (altı rotor)

**Tezde ne yapmalısın:**  
Yöntem bölümünde bu değişikliği açıkla. Önce quadrotor planlandığını, ancak tarımsal ilaçlama dronlarının sektörel standardının hexarotor olduğunu (DJI Agras T10 vb. referanslarla) belirt. Quadrotor'a göre hexarotor'ın yük kapasitesi ve redundancy avantajını kısaca sun. Danışmanına haber ver — form üzerinde not olarak belirtilebilir.

---

### 1.2 Veri İletişim Protokolü — KRİTİK

**Form 31:** *"MQTT protokolü üzerinden geliştirdiğimiz matematiksel modele veri aktaracaktır"*  
**Kod:** MQTT yok. `digital_twin_v2.py` → MAVLink / pymavlink kullanılıyor. MQTT bağlantısı hiçbir dosyada mevcut değil.

**Tezde ne yapmalısın:**  
Yöntem bölümünde şunu açıkla: Planlama aşamasında MQTT düşünüldü, ancak ArduPilot SITL ile doğal entegrasyon MAVLink üzerinden sağlandığından mimari bu protokole göre yeniden şekillendirildi. MAVLink'in tarımsal İHA literatüründe de standart olduğunu belirt (DroneKit/pymavlink referansı ekle). Danışmanına bu değişikliği bildirmen gerekir.

---

### 1.3 Güç Modeli — Basit Lineer → Actuator Disk Teorisi

**Form 31 İP-1-B:** *"P(t) = k₁·m(t)·g + k₂·F_w(t); katsayılar en küçük kareler yöntemiyle kalibre edilecek"*  
**Kod:** `energy_model.py` → P = T^1.5 / √(2ρNA) (actuator disk teorisi) + aerodinamik sürükleme + sloshing + dikey rüzgar. En küçük kareler kalibrasyonu yapılmadı.

**Tezde ne yapmalısın:**  
Bu aslında pozitif bir evrim — tezde "yöntem geliştirme" olarak sun:
> "İlk tasarımda ampirik k₁-k₂ katsayılarına dayalı bir yaklaşım planlanmıştır. Ancak çalışma ilerledikçe, actuator disk teorisinin (Leishman 2006; Abdilla vd. 2015) fiziksel temele dayalı formülasyonunun daha güvenilir ve kalibrasyonsuz sonuçlar ürettiği görülmüş; model bu yöntemle güncellenmiştir."

Leishman (2006) ve Abdilla vd. (2015) kaynaklarını teze eklemeyi unutma — bunlar zaten `energy_model.py` içinde atıf yapılıyor.

---

### 1.4 Batarya Modeli — Doğrusal → Doğrusal Olmayan OCV

**Form 31 İP-2:** *"Doğrusal boşalma eğrisi; parametreler açık kaynaklı İHA teknik şartnamesinden alınacaktır"*  
**Kod:** `battery_model.py` → 4. dereceden polinom OCV eğrisi + Peukert etkisi + SoH degradasyonu. Tattu 3S datasheet'e fit edilmiş.

**Tezde ne yapmalısın:**  
Güç modeli değişikliğinde olduğu gibi bunu da "model iyileştirmesi" olarak sun:
> "Batarya modeli, başlangıçta doğrusal deşarj eğrisi olarak planlanmıştır. Gerçek LiPo davranışının yüksek ve düşük SoC'da önemli sapma gösterdiği (Chen ve Rincon-Mora 2006) görüldüğünden, polinom fit tabanlı OCV modeli uygulanmıştır."

Chen ve Rincon-Mora (2006) kaynağını teze ekle — `battery_model.py`'de referans zaten var.

---

### 1.5 Simülasyon Platformu — Eksik Entegrasyon

**Form 31 İP-2:** *"Gazebo + ArduPilot SITL veya Microsoft AirSim + ArduPilot SITL"*  
**Kod:** Gazebo veya AirSim entegrasyonu yok. `digital_twin_v2.py` doğrudan MAVLink UDP üzerinden SITL'e bağlanıyor ama görsel fizik motoru (Gazebo/AirSim) aktif değil. `matematiksel` mod ise SITL'siz tamamen Python simülasyonu.

**Tezde ne yapmalısın:**  
Form 31'de platform esnekliği maddesi zaten yazıyor: *"Dijital İkiz katmanı MAVLink tabanlı olduğundan Gazebo veya AirSim'den bağımsız çalışır."* Bu notu tezinde kullan. Yöntemde şunu açıkla:
> "SITL entegrasyonu MAVLink protokolü düzeyinde gerçekleştirilmiş, görsel fizik motoru ek katman oluşturduğundan tez kapsamında matematiksel simülasyon modu önceliklendirilmiştir."

---

### 1.6 Rüzgar Yönü — Eksik

**Form 31 İP-2:** *"Rüzgar sahneleri: 0–360° yön"*  
**Kod:** `energy_model.py:138` → `v_etkin = V_SEYIR + v_wind_ms` — rüzgar hep başa (worst-case) alınıyor. Yön açısı (θ) modellenmemiş.

**Tezde ne yapmalısın:**  
Sınırlılıklar bölümünde belirt:
> "Bu çalışmada rüzgar, hesaplama basitliği açısından daima başa gelen worst-case konfigürasyonda modellenmiştir. 0–360° yön açısına göre değişen enerji tüketimi, gelecek çalışma kapsamında ele alınabilir."

---

### 1.7 Tarla Geometrisi — Basitleştirme

**Form 31 İP-2:** *"Gerçekçi büyüklükte (200×200 m) düz tarım alanı sahnesi"*  
**Kod:** `config.yaml → iha.target_distance_m: 500` — tek doğrultulu lineer 500 m gidiş-dönüş. 2D alan yoktur.

**Tezde ne yapmalısın:**  
Sınırlılıklar bölümünde belirt ve gerekçelendir:
> "Çalışma kapsamında görev profili, enerji analizini izole biçimde değerlendirmek amacıyla doğrusal 500 m gidiş-dönüş rotası olarak modellenmiştir. Serpantinli saha profili PNR hesabını değiştirmez; temel enerji ve güvenlik ilişkisi korunur."

---

### 1.8 PNR Gecikme Ölçümü — Kavramsal Not

**Form 31 İP-6:** *"PNR eşiğinin matematiksel olarak aşıldığı an ile sistemin komutu ürettiği an arasındaki fark (ms cinsinden) raporlanacaktır"*  
**Kod:** `scenario_runner.py:109` → `gecikme_ms = DT * 1000 = 1000 ms` — gecikme her zaman sabit 1 saniye çünkü simülasyon adımı DT=1s.

**Tezde ne yapmalısın:**  
Bulgular bölümünde bunu açıkla:
> "Matematiksel simülasyonda PNR kararı her simülasyon adımında (Δt = 1 s) değerlendirildiğinden sistem gecikmesi teorik maksimum Δt = 1000 ms'dir. Gerçek zamanlı donanım entegrasyonunda bu süre donanım latansına bağlı olarak azalacaktır."

---

## 2. FORM 31'DE VAAT EDİLMEYEN AMA KODda OLAN EKSTRA KATKILAR

Bunlar tezinde "orijinal katkılar" olarak öne çıkarmalısın.

| Özellik | Nerede | Tezde nasıl sun |
|---------|--------|-----------------|
| **Sloshing modeli** | `energy_model.py:73` | Güç modelinin 4. bileşeni; tarımsal İHA literatüründe nadir ele alınan katkı. `payload_g` / `max_payload_g` parametreleri `scenario_runner.py` ve `re_simulation.py` üzerinden tam olarak beslendiğinden tüm PNR hesaplama yollarında aktif. |
| **Dead reckoning fallback** | `modules/dead_reckoning.py` | GPS güvenilirliği için kritik mekanizma; Steindl vd. (2024) referansını kullan |
| **Batarya yaşlanması (SoH)** | Senaryo F | Gerçek operasyonel kullanımda görev ömrüne etkisi; orijinal katkı |
| **Olay güdümlü yeniden simülasyon** | `modules/re_simulation.py` | Rüzgar değiştiğinde PNR anlık güncelleniyor — bu tezin asıl özgün katkısı. Yeniden simülasyon sırasında da sloshing aktif (payload_g besleniyor). |
| **40 birim test (V-Model)** | `test_models.py`, `test_dead_reckoning.py` | Yazılım doğrulama bölümünde V-Model metodolojisi olarak sun |
| **Config-driven mimari** | `config.yaml` | Tek yapılandırma dosyasıyla donanım/simülasyon/matematiksel mod geçişi |
| **Yapılandırılmış loglama** | `modules/dt_logger.py` → `digital_twin_v2.py` | Tüm kritik olaylar (PNR, BATARYA_KRİTİK, RÜZGAR_AŞIM, KÜTLE_BİTTİ, MAVLink kopması) hem konsola hem log dosyasına seviyeli şekilde yazılıyor. Yazılım kalitesi kanıtı olarak sun. |
| **Tek rüzgar modeli** | `modules/wind_model.py` → `run_wind_scenarios.py` | Sinüsoidal, basamaklı ve türbülanslı profiller tek modülden geliyor; çift kaynak problemi giderildi. Mimari tutarlılık katkısı olarak belirt. |

---

## 3. TEZ BÖLÜMÜ BÖLÜMÜ NOTLAR

### 3.1 Giriş
- Tarımsal İHA pazarının büyüklüğünü Türkiye bağlamında ver (GAP bölgesi, Malatya — Form 31'de yazdıklarını genişlet).
- Literatür boşluğunu net yaz: "Dinamik kütle azalışı + rüzgar etkisi + olay güdümlü PNR" kombinasyonu daha önce bir arada ele alınmamış. Form 31'de bunu iyi ifade etmişsin, teze olduğu gibi aktarabilirsin.

### 3.2 İlgili Çalışmalar (Literatür)
Tezindeki 9+1 kaynak yetersiz kalabilir. Eklenmesi gereken kaynaklar:
- **Leishman (2006)** — actuator disk teorisi temel referansı (`energy_model.py`'de var)
- **Abdilla vd. (2015)** — çok rotorlu İHA güç ve dayanıklılık modellemesi (`energy_model.py`'de var)
- **Gatti vd. (2015)** — batarya güçlü döner kanatlı araç menzili (`energy_model.py`'de var)
- **Chen ve Rincon-Mora (2006)** — LiPo batarya modeli (`battery_model.py`'de var)
- **Schacht-Rodriguez vd. (2019)** — çok rotorlu İHA için görev planlama ve menzil tahmini (`energy_model.py`'de var)
- Bunları Form 30/31 kaynak listesine ek olarak teze ekle.

### 3.3 Yöntem
Güç modelini açıklarken 4 bileşeni tablo halinde göster:

| Bileşen | Formül | Kaynak |
|---------|--------|--------|
| Hover gücü | P_hover = T^1.5 / √(2ρNA) | Leishman (2006), Abdilla vd. (2015) |
| İleri itme gücü | P_forward = 0.5ρCdAv³ | Gatti vd. (2015) |
| Sloshing gücü | P_slosh = (P_hover + P_fwd) × k | Muhafazakâr tahmin |
| Dikey rüzgar gücü | P_dikey = |mgv_dikey| / η | Lei vd. (2024) |

### 3.4 Sistem Mimarisi
Üç çalışma modunu açıkla:

```
matematiksel modu  → Saf Python simülasyonu (tezin ana doğrulama ortamı)
simulation modu    → ArduPilot SITL bağlantısı (MAVLink UDP 14551)
donanim modu       → Gerçek drone (gelecek çalışma)
```

Mimari diyagramda şu akışı göster:  
`Telemetri → Enerji Modeli → PNR Hesabı → Olay Yöneticisi → Re-Simulation → Log/Dashboard`

### 3.5 Senaryolar ve Bulgular
6 senaryonun hepsini teze dahil et:

| Senaryo | Değişken | Amaç |
|---------|----------|------|
| A | Sabit kütle, rüzgar yok | Baseline |
| B | Dinamik kütle, rüzgar yok | Kütle etkisi izolasyonu |
| C | Sabit kütle, 3/7/12 m/s | Rüzgar etkisi izolasyonu |
| D | Dinamik kütle, 3/7/12 m/s | Gerçekçi operasyonel koşul |
| E | Dinamik kütle, değişken rüzgar, 3 tekrar | PNR karar doğruluk testi |
| F | SoH 0/300/500 döngü | Batarya yaşlanması etkisi |

Form 31'deki İP-6 analiz stratejisini (A vs B, A vs C, D vs B+C) bulgular bölümünde uygula.

### 3.6 Doğrulama (V-Model)
40 birim testin V-Model doğrulama felsefesiyle örtüştüğünü göster:

```
Gereksinim → Tasarım → Kodlama → Birim Test → Entegrasyon Test → Sistem Doğrulama
              ↕           ↕           ↕               ↕                  ↕
          (Form 31)  (config.yaml)  (test_models)  (senaryo A-D)     (senaryo E)
```

### 3.7 Sınırlılıklar (MUTLAKA YAZ)
Bu bölümü atlarsan savunmada zor durumda kalırsın. Aşağıdakileri yaz:

1. **Sloshing katsayıları deneysel olarak doğrulanmamıştır.** k_max değerleri (perdeli: 0.02, perdesiz: 0.08) muhafazakâr tahmin olup CFD analizi veya saha testi ile kalibre edilmelidir. Kod içinde de bu not var.
2. **Rüzgar yalnızca başa gelen (worst-case headwind) olarak modellenmiştir.** 0-360° yön senaryoları kapsam dışındadır.
3. **Simülasyon parametreleri (9.5 Wh batarya, 2.5 kg) ölçeklendirilmiş temsili değerlerdir.** Gerçek tarım dronu donanımı (97.2 Wh, ~15-20 kg) farklı parametrelere sahiptir; mimari config.yaml güncellemesiyle bu ölçeğe taşınabilir.
4. **Dead reckoning sabit hız ve yön varsayımına dayanmaktadır.** İvme ve manevra etkisi dahil edilmemiştir.
5. **PNR gecikme süresi simülasyon adım boyutuna (1 s) bağlıdır.** Gerçek zamanlı sistemde bu süre donanım latansıyla şekillenecektir.
6. **Protokol değişikliği:** Planlanan MQTT yerine MAVLink kullanılmıştır (Bölüm X'te gerekçelendirilmiştir).

---

## 4. KAYNAK LİSTESİ — FORM'DA YOK AMA GEREKLI

Aşağıdaki kaynaklar kodda kullanılıyor, tez kaynak listesine eklenmeli:

```
[11] Leishman, J.G. (2006). Principles of Helicopter Aerodynamics.
     Cambridge University Press.

[12] Abdilla, A., Richards, A., Burrow, S. (2015). Power and endurance
     modelling of battery-powered rotorcraft. IROS 2015.

[13] Gatti, M., Giulietti, F., Turci, M. (2015). Maximum endurance for
     battery-powered rotary-wing aircraft. Aerospace Science and Technology.

[14] Chen, M., Rincon-Mora, G.A. (2006). Accurate electrical battery model
     capable of predicting runtime and IV performance.
     IEEE Transactions on Energy Conversion, 21(2), 504-511.

[15] Schacht-Rodriguez, R. ve diğ. (2019). Mission planning strategy for
     multirotor UAV based on flight endurance estimation. ICUAS 2019.

[16] Tattu. 3S 3000mAh 25C LiPo Battery Datasheet. (Public, web erişimi)
```

---

## 5. KOD'DA KALAN KÜÇÜK SORUNLAR (tez öncesi düzeltilmeli)

| Sorun | Dosya | Durum | Düzeltme |
|-------|-------|-------|----------|
| `scenario_runner.py` başlığı "5 senaryo" diyor | Satır 2 | ⏳ Açık | "6 senaryoyu (A–F)" yap |
| `guvenik` yazım hatası | `config.yaml:55` + 4 py dosyası | ⏳ Açık | `guvenlik` yap (config ve tüm .py dosyalarında birlikte değiştir) |

> **Not:** `guvenik` anahtarını değiştirirken şu dosyaları birlikte güncelle:  
> `config.yaml`, `energy_model.py`, `scenario_runner.py`, `dashboard.py`, `generate_report.py`, `digital_twin_v2.py`

### Giderilen sorunlar (2026-05-31)

| Sorun | Dosya | Düzeltme |
|-------|-------|----------|
| `pnr_energy_required` çağrısında `payload_g` iletilmiyordu → sloshing pasifti | `scenario_runner.py:88` | `payload_mass(t)` hesaplanıp `payload_g` / `max_payload_g` olarak iletildi |
| Yeniden simülasyonda `payload_g` iletilmiyordu → sloshing pasifti | `modules/re_simulation.py:34` | `payload_mass(t_elapsed)` hesaplanıp `payload_g` / `max_payload_g=1000.0` olarak iletildi |
| `run_wind_scenarios.py` `wind_model.py`'yi kullanmıyor, dört inline fonksiyon tanımlıyordu | `run_wind_scenarios.py:34-59` | `WIND_PROFILLER` import edildi; inline tanımlar kaldırıldı |
| Unicode hata: `→` karakteri terminal kodlamasını çöküyordu | `run_wind_scenarios.py` | `sys.stdout.reconfigure(encoding='utf-8')` eklendi |
| `digital_twin_v2.py` kritik olayları yalnızca `print()` ile bildiriyordu; `dt_logger.py` kullanılmıyordu | `digital_twin_v2.py` | `get_logger('DigitalTwinV2')` eklendi; 5 olay `logger.warning/info/critical` ile de kaydediliyor |

---

## 6. SAVUNMADA GELEBİLECEK SORULAR VE HAZIR CEVAPLAR

**S: "Formda MQTT yazıyor ama MAVLink kullandınız, neden?"**  
C: ArduPilot SITL, MAVLink üzerinden haberleşmektedir. MQTT ekstra bir katman oluşturacak ve gecikme yaratacaktı; sektörel standart olan MAVLink doğrudan entegrasyonu seçildi.

**S: "Formda dört rotorlu yazıyor, siz altı rotor kullandınız?"**  
C: Sektörel tarım dronu standardı (DJI Agras T10, T30 vb.) hexarotordur. Yük kapasitesi ve güvenlik redundancy açısından hexarotor daha uygundur; model bu gerçekliği yansıtmaktadır.

**S: "Sloshing katsayılarını nasıl doğruladınız?"**  
C: Mevcut değerler literatür muhafazakâr tahminidir. Sınırlılıklar bölümünde belirtilmiştir; CFD veya saha testi ile kalibre edilmesi gelecek çalışma kapsamındadır.

**S: "9.5 Wh batarya gerçek bir tarım dronu için çok küçük değil mi?"**  
C: Bu değer ArduPilot SITL çalışma ortamından kalibre edilmiş ölçeklendirilmiş bir parametredir. Mimari config.yaml üzerinden gerçek donanım değerlerine (97.2 Wh) kolayca taşınabilir; donanım modu için bu değer config'de tanımlıdır.

**S: "Formda en küçük kareler kalibrasyonu yapacaktınız, yapmadınız?"**  
C: Ampirik k₁-k₂ modelinin yerine actuator disk teorisi kullanılmıştır. Bu daha güçlü bir fiziksel temeldir ve kalibrasyon verisi gerektirmez; model parametreleri doğrudan rotor geometrisinden türetilmektedir.

**S: "PNR gecikmeniz her zaman 1000ms, bu yeterli mi?"**  
C: Matematiksel simülasyonda adım boyutu Δt=1s'dir; gecikme bu adımla sınırlıdır. Gerçek zamanlı donanım entegrasyonunda MAVLink mesaj frekansı (10 Hz) gecikmeyi 100ms'ye indirir.

---

## 7. ÖNERİLEN TEZ BÖLÜM SIRASI

1. Özet (TR + İNG)
2. İçindekiler
3. Şekiller/Tablolar Dizini
4. Semboller ve Kısaltmalar
5. Giriş
   - 5.1 Problemin Tanımı
   - 5.2 Çalışmanın Amacı ve Kapsamı
   - 5.3 Tezin Özgün Katkıları
   - 5.4 Tezin Yapısı
6. İlgili Çalışmalar
7. Sistem Mimarisi
   - 7.1 Genel Mimari
   - 7.2 Çalışma Modları (matematiksel / SITL / donanım)
   - 7.3 Veri Akışı
8. Matematiksel Modeller
   - 8.1 Dinamik Kütle Modeli
   - 8.2 Enerji Tüketim Modeli (Actuator Disk Teorisi)
   - 8.3 Batarya Modeli (Peukert + OCV)
   - 8.4 PNR Hesabı
   - 8.5 Sloshing Modeli
   - 8.6 Dead Reckoning
   - 8.7 Rüzgar Modeli
9. Olay Güdümlü Karar Mekanizması
   - 9.1 Olay Tanımları ve Tetikleyiciler
   - 9.2 Yeniden Simülasyon (Re-Simulation) Motoru
10. Doğrulama ve Test
    - 10.1 V-Model Metodolojisi
    - 10.2 Birim Testler (40 test)
    - 10.3 Senaryo Tanımları (A–F)
11. Bulgular ve Analiz
    - 11.1 Senaryo Karşılaştırmaları (A vs B, A vs C, D vs B+C)
    - 11.2 PNR Karar Doğruluk Analizi (Senaryo E)
    - 11.3 Batarya Yaşlanması Etkisi (Senaryo F)
12. Tartışma
13. Sonuç ve Gelecek Çalışmalar
14. Kaynaklar
15. Ekler (kod yapısı, config parametreleri)
