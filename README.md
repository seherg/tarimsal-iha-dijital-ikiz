# Tarımsal İHA Dijital İkizi v2.0

6 rotorlu (hexarotor) bir tarım ilaçlama dronu için fizik tabanlı dijital ikiz. Gerçek zamanlı enerji takibi, Dönüş Noktası (PNR) kararı ve GPS kaybında konum tahmini (dead reckoning) yapar. Yüksek lisans tez projesi.

## Ne Yapar?

- **Enerji modeli:** Actuator disk teorisine dayalı rotor gücü + Peukert etkisiyle batarya deşarjı
- **PNR hesabı:** Her saniye "eve dönmek için yeterli enerji var mı?" sorusunu yanıtlar
- **Dinamik kütle:** İlaç püskürtüldükçe azalan ağırlık gerçek zamanlı hesaplanır
- **Rüzgar modeli:** Sinüzoidal, kademeli ve türbülanslı rüzgar profilleri
- **Dead reckoning:** GPS verisi 2 saniyeden fazla kesilirse kinematik konum tahmini devreye girer
- **Dashboard:** Streamlit arayüzüyle canlı telemetri izleme ve log analizi

## Kurulum

```bash
# Sanal ortamı aktive et
dt_env\Scripts\activate          # Windows
source dt_env/bin/activate       # Linux/Mac

# Bağımlılıkları yükle (zaten kuruluysa atla)
pip install -r requirements.txt
```

## Çalıştırma

```bash
# Tez senaryolarını çalıştır (A–E)
python scenario_runner.py

# Streamlit dashboard
streamlit run dashboard.py

# Rüzgar senaryoları
python run_wind_scenarios.py

# Görselleştirmeler
python plot_sloshing.py
python plot_flight_path.py
python plot_C_vs_D.py

# HTML rapor üret (logs/ klasöründen)
python generate_report.py

# Birim testler
python -m pytest test_models.py test_dead_reckoning.py -v --tb=short  # 51 test
```

Çalışma modu `config.yaml` → `sistem.mod` anahtarıyla belirlenir:

| Mod | Açıklama |
|-----|----------|
| `matematiksel` | Saf Python simülasyonu, donanım gerekmez (varsayılan) |
| `simulation` | ArduPilot SITL'e MAVLink UDP bağlantısı |
| `donanim` | Gerçek drone |

## Dosya Yapısı

```
├── config.yaml              # Tüm ayarlar (kütle, batarya, rüzgar, güvenlik)
├── energy_model.py          # Actuator disk + Peukert enerji modeli
├── digital_twin_v2.py       # Ana döngü: telemetri → fizik → PNR → log
├── scenario_runner.py       # Tez senaryoları A–E toplu çalıştırıcı
├── dashboard.py             # Streamlit arayüzü
├── generate_report.py       # HTML rapor üretici
├── run_wind_scenarios.py    # 4 rüzgar profili testi
├── plot_*.py                # Görselleştirme scriptleri
├── test_models.py           # Fizik modeli birim testleri
├── test_dead_reckoning.py   # Dead reckoning + sloshing testleri
├── modules/
│   ├── battery_model.py     # LiPo SoH, yük altı voltaj
│   ├── payload_model.py     # İlaç tüketimi, dinamik kütle
│   ├── wind_model.py        # Rüzgar profilleri
│   ├── dead_reckoning.py    # GPS yedek konum tahmini
│   ├── re_simulation.py     # PNR yeniden simülasyon motoru
│   └── dt_logger.py         # Yapısal loglama (dosya + terminal, seviyeli)
├── logs/                    # Uçuş logları (CSV) ve HTML raporlar
└── plots/                   # Üretilen PNG grafikler
```

## Tez Senaryoları

| Senaryo | Kütle | Rüzgar | Amaç |
|---------|-------|--------|------|
| A | Sabit | Yok | Referans baseline |
| B | Dinamik | Yok | Yalnızca kütle etkisi |
| C | Sabit | 3 / 7 / 12 m/s | Yalnızca rüzgar etkisi |
| D | Dinamik | 3 / 7 /12 m/s | Gerçekçi operasyonel koşul |
| E | Dinamik | Değişken | PNR karar doğruluk testi (3 tekrar) |
| F1 | Dinamik | 3 m/s | Yeni batarya (0 cycle) |
| F2 | Dinamik | 3 m/s | Orta yaşlı batarya (300 cycle) |
| F3 | Dinamik | 3 m/s | Yaşlı batarya (500 cycle) |

**Başarı kriteri:** PNR anında kalan enerji ≥ eve dönüş için gereken minimum enerji.

## Ana Bulgular

- **Senaryo A vs B:** Dinamik kütle modeli PNR kararını 168 saniye geciktiriyor (+%291).
  Sabit kütle varsayımı görevi gereksiz yere kısaltıyor.
- **Senaryo C vs D:** Statik kütle modeli RTH kararını ortalama 98 saniye erken veriyor.
  Görev süresinin %55.9'u boşa gidiyor.
  3 m/s rüzgarda +151s, 7 m/s'de +106s, 12 m/s'de +37s fark.
- **Senaryo F (SoH):** 300 cycle sonra görev süresi %20 azalıyor, 500 cycle'da %32 azalıyor.
  Eski batarya PNR'ı 77 saniye daha erken tetikliyor.
- **Dead reckoning:** 2 saniyelik GPS kaybında konum hatası 500 m parkurda 15 m altında kalıyor.
- **51/51 test** başarıyla geçiyor.

## Tam Pipeline

Projeyi sıfırdan çalıştırmak için:

```bash
# 1. Testler
python -m pytest test_models.py test_dead_reckoning.py -v

# 2. Tez senaryoları (A-F)
python scenario_runner.py

# 3. Rüzgar senaryoları
python run_wind_scenarios.py

# 4. Görselleştirmeler
python plot_C_vs_D.py
python plot_flight_path.py
python plot_sloshing.py

# 5. Kapsamlı HTML rapor
python generate_report.py
# → logs/rapor_*.html dosyasını tarayıcıda aç
```
