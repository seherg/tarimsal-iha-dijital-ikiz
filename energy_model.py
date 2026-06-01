"""
Enerji Modeli v3 — Fiziksel Formül Güncellendi
===============================================
Güç modeli bileşenleri:
  P(t) = P_hover + P_forward + P_sloshing + P_dikey

Değişiklik (v2 → v3):
  ESKİ: P_itki = (m * g * v_seyir) / eta   ← fiziksel olarak yanlış
  YENİ: P_hover = T^1.5 / sqrt(2 * rho * N * A_disk)  ← actuator disk teorisi

Referanslar:
  - Leishman, J.G. (2006). Principles of Helicopter Aerodynamics.
    Cambridge University Press. (Actuator disk teorisi temeli)
  - Abdilla, A., Richards, A., Burrow, S. (2015). Power and endurance
    modelling of battery-powered rotorcraft. IROS 2015.
  - Gatti, M., Giulietti, F., Turci, M. (2015). Maximum endurance for
    battery-powered rotary-wing aircraft. Aerospace Science and Technology.
  - Schacht-Rodriguez et al. (2019). Mission planning strategy for
    multirotor UAV based on flight endurance estimation. ICUAS 2019.

Donanım notu:
  Rotor parametreleri config.yaml → rotor bloğundan okunur.
  Gerçek drone bağlandığında sadece config güncellenir, kod değişmez.
"""

import math
import yaml
import os
import logging

logger = logging.getLogger(__name__)

# ── Fiziksel sabitler ─────────────────────────────────────────
G   = 9.81    # Yerçekimi ivmesi (m/s²)
RHO = 1.225   # Deniz seviyesinde hava yoğunluğu (kg/m³)

# ── Config yükle ─────────────────────────────────────────────
def _load_cfg():
    cfg_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    if not os.path.exists(cfg_path):
        cfg_path = 'config.yaml'
    with open(cfg_path) as f:
        return yaml.safe_load(f)

_cfg = _load_cfg()

N_ROTOR    = _cfg['rotor']['sayi']          # Rotor sayısı
A_DISK     = _cfg['rotor']['disk_alani_m2'] # Tek rotor disk alanı (m²)
A_REF      = _cfg['rotor']['ref_alan_m2']   # Gövde referans alanı (m²)
ETA        = _cfg['rotor']['eta']           # Motor + pervane verimlilik
CD_GOVDE   = 0.3                            # Gövde sürükleme katsayısı
                                            # (multirotor literatür değeri)
PNR_MARJ   = _cfg['guvenlik']['pnr_marji_pct'] / 100.0
V_SEYIR    = _cfg['iha']['cruise_speed_ms']


# ══════════════════════════════════════════════════════════════
# YARDIMCI FONKSİYONLAR
# ══════════════════════════════════════════════════════════════

def haversine(lat1, lon1, lat2, lon2):
    """İki GPS koordinatı arasındaki mesafe (metre). Haversine formülü."""
    R    = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a    = (math.sin(dphi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def sloshing_katsayisi(doluluk_orani, perdeli_tank=False):
    """
    Sıvı çalkantı (sloshing) katsayısı.

    Fiziksel temel:
        Sloshing, tankın %30-70 doluluk aralığında maksimuma ulaşır.
        Tam dolu veya tam boşta sıfıra yaklaşır (çan eğrisi davranışı).
        Perdeli (baffled) tank sloshing etkisini ~4x azaltır.

    Parametreler:
        doluluk_orani : 0.0 (boş) – 1.0 (tam dolu)
        perdeli_tank  : True ise baffle var

    Dönüş: boyutsuz katsayı k (0 – k_max)

    Not: k_max değerleri tarımsal İHA literatüründe deneysel olarak
    doğrulanmış değildir; CFD veya saha testi ile kalibre edilmesi
    gerekir. Mevcut değerler muhafazakâr tahmin olarak kullanılmaktadır.
    """
    k_max = 0.02 if perdeli_tank else 0.08
    k     = k_max * 4 * doluluk_orani * (1 - doluluk_orani)
    return k


# ══════════════════════════════════════════════════════════════
# ANA GÜÇ MODELİ
# ══════════════════════════════════════════════════════════════

def hover_gucu(mass_kg):
    """
    Actuator disk teorisine göre hover (askıda kalma) gücü.

    P_hover = T^1.5 / sqrt(2 * rho * N * A_disk)

    Burada T = m * g (toplam thrust, Newton cinsinden).
    Bu ifade ideal (kayıpsız) hover gücüdür; verimlilik ETA ile bölünür.

    Referans: Leishman (2006), Bölüm 2; Abdilla et al. (2015).

    Parametreler:
        mass_kg : Anlık toplam kütle (kg)

    Dönüş: Watt cinsinden hover gücü (verimlilik dahil)
    """
    T       = mass_kg * G                          # Toplam thrust (N)
    P_ideal = T ** 1.5 / math.sqrt(2 * RHO * N_ROTOR * A_DISK)
    return P_ideal / ETA


def ileri_guc(v_wind_ms):
    """
    Seyir hızında aerodynamik direnç gücü (parasitik drag).

    P_forward = 0.5 * rho * Cd * A_ref * v^3

    Rüzgar hızı ile birlikte bileşik hız etkisi modellenmektedir:
    rüzgar başa geliyorsa (worst-case) v_etkin = v_seyir + v_wind.

    Referans: Gatti et al. (2015), Abdilla et al. (2015).

    Parametreler:
        v_wind_ms : Yatay rüzgar hızı (m/s)

    Dönüş: Watt cinsinden ileri itme gücü
    """
    v_etkin = V_SEYIR + v_wind_ms   # Başa rüzgar worst-case
    P_drag  = 0.5 * RHO * CD_GOVDE * A_REF * v_etkin ** 3
    return P_drag / ETA


def dikey_ruzgar_gucu(mass_kg, v_dikey_ms):
    """
    Dikey hava akımı (updraft/downdraft) karşısında irtifa koruma gücü.

    Updraft  (+): İHA aşağı itilir → daha fazla thrust gerekir
    Downdraft (-): İHA yukarı itilir → daha az thrust, ama kontrol güçleşir
    Her iki durumda da ek güç tüketimi abs() ile modellenir.

    P_dikey = |m * g * v_dikey| / eta

    Referans: Lei et al. (2024), US Patent 11,919,637 B2.

    Parametreler:
        mass_kg    : Anlık toplam kütle (kg)
        v_dikey_ms : Dikey rüzgar hızı (m/s), pozitif=updraft

    Dönüş: Watt cinsinden dikey rüzgar kompansasyon gücü
    """
    return abs(mass_kg * G * v_dikey_ms) / ETA


# ══════════════════════════════════════════════════════════════
# PNR ENERJİ HESABI
# ══════════════════════════════════════════════════════════════

def pnr_energy_required(
    distance_m: float,
    mass_g: float,
    v_wind_ms: float,
    v_dikey_ms: float = 0.0,
    perdeli_tank: bool = False,
    payload_g: float = 0.0,
    max_payload_g: float = 1000.0
) -> float:
    """
    Eve dönüş için gereken minimum enerji (PNR eşiği).
    ...
    """
    if distance_m <= 0:
        logger.warning(f"Geçersiz mesafe: {distance_m}m, 10m olarak ayarlandı")
        distance_m = 10.0
    if mass_g <= 0:
        raise ValueError(f"Kütle sıfır veya negatif olamaz: {mass_g}g")
    if v_wind_ms < 0:
        logger.warning(f"Negatif rüzgar hızı: {v_wind_ms}, 0 olarak ayarlandı")
        v_wind_ms = 0.0

    mass_kg = mass_g / 1000.0

    # ── Bileşen 1: Hover gücü (actuator disk teorisi)
    P_hover = hover_gucu(mass_kg)

    # ── Bileşen 2: Aerodynamik direnç (parasitik drag)
    P_forward = ileri_guc(v_wind_ms)

    # ── Bileşen 3: Sloshing (sıvı çalkantı)
    doluluk    = max(0.0, min(1.0,
                    payload_g / max_payload_g if max_payload_g > 0 else 0.0))
    k_slosh    = sloshing_katsayisi(doluluk, perdeli_tank)
    P_sloshing = (P_hover + P_forward) * k_slosh

    # ── Bileşen 4: Dikey rüzgar kompansasyonu
    P_dikey = dikey_ruzgar_gucu(mass_kg, v_dikey_ms)

    # ── Toplam güç
    P_toplam = P_hover + P_forward + P_sloshing + P_dikey

    # ── Dönüş enerjisi
    t_donus = distance_m / V_SEYIR   # saniye
    E_wh    = P_toplam * t_donus / 3600.0

    # ── Güvenlik marjı (config'den)
    return E_wh * (1.0 + PNR_MARJ)


# ══════════════════════════════════════════════════════════════
# DOĞRULAMA (standalone çalıştırıldığında)
# ══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("=" * 55)
    print("Enerji Modeli v3 — Doğrulama Çıktısı")
    print("=" * 55)
    print(f"Rotor sayısı   : {N_ROTOR}")
    print(f"Disk alanı     : {A_DISK} m² (tek rotor)")
    print(f"Referans alan  : {A_REF} m²")
    print(f"Verimlilik     : {ETA}")
    print(f"Seyir hızı     : {V_SEYIR} m/s")
    print(f"PNR marjı      : %{PNR_MARJ*100:.0f}")
    print()

    test_cases = [
        (500, 2500, 0,  "Baseline — rüzgar yok"),
        (500, 2500, 5,  "Orta rüzgar (5 m/s)"),
        (500, 2500, 12, "Güçlü rüzgar (12 m/s)"),
        (500, 1500, 5,  "İlaç bitmiş, orta rüzgar"),
    ]

    print(f"{'Senaryo':<35} {'E_pnr (Wh)':>12}")
    print("-" * 50)
    for dist, mass, wind, label in test_cases:
        e = pnr_energy_required(dist, mass, wind)
        print(f"  {label:<33} {e:>10.4f}")

    print()
    print("Hover gücü karşılaştırması (v2 vs v3):")
    mass_kg = 2.5
    P_v2 = (mass_kg * G * V_SEYIR) / 0.7   # eski formül
    P_v3 = hover_gucu(mass_kg)              # yeni formül
    print(f"  v2 (yanlış) : {P_v2:.2f} W")
    print(f"  v3 (doğru)  : {P_v3:.2f} W")
    print(f"  Fark        : {abs(P_v2-P_v3):.2f} W "
          f"(%{abs(P_v2-P_v3)/P_v3*100:.1f})")
    print()
    print("Mesafe testi (haversine):")
    d = haversine(39.0, 35.0, 39.005, 35.005)
    print(f"  İstanbul–Ankara yaklaşık: {haversine(41.01,28.96,39.93,32.85)/1000:.0f} km")
    print(f"  Kısa mesafe testi       : {d:.1f} m")