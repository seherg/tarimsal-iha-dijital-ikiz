"""
Dinamik Ruzgar Modulu v2.1
Sabit ruzgar yerine gercekci zamana bagli ruzgar profili.
Akademik dogrulama icin 'seed' bazli tekrarlanabilirlik eklendi.
"""
import math
import random

# Deneylerin her seferinde ayni ruzgar profilini uretmesi icin sabit seed
random.seed(42) 

def sinusoidal_wind(t, base=5.0, amplitude=3.0, period=60.0, noise_std=0.5):
    """
    Sinusoidal + Gaussian gurultu ruzgar modeli.
    Base: Ortalama, Amplitude: Dalgalanma, Period: Salinim suresi
    """
    # math.sin radyanda calisir, t saniye cinsinden periyoda oranlanir
    gusty = amplitude * math.sin(2 * math.pi * t / period)
    noise = random.gauss(0, noise_std)
    return max(0.0, base + gusty + noise)

def step_wind(t, steps):
    """
    Basamakli ruzgar profili - Belirli anlarda keskin (discrete) degisim.
    steps: [(zaman_s, hiz_ms), ...]
    """
    # Baslangic degeri olarak ilk adimi alalim
    current_speed = steps[0][1]
    # Zaman esigini gecen en son hizi bulur
    for t_threshold, speed in steps:
        if t >= t_threshold:
            current_speed = speed
    return float(current_speed)

def turbulent_wind(t, base=5.0):
    """
    Turbulansli ruzgar - Basitlestirilmis Von Karman yaklasimi.
    Farkli frekanslarin superpozisyonu.
    """
    # Dusuk frekansli ana akim dalgalanmasi
    low_freq  = 2.0 * math.sin(2 * math.pi * t / 45.0)
    # Yuksek frekansli titresim (titreme etkisi)
    high_freq = 0.8 * math.sin(2 * math.pi * t / 7.0)
    # Ani esinti (Spike) - mod islemi yerine zaman araligi kontrolu daha saglikli
    spike = 3.0 if (200 < t < 205 or 450 < t < 455) else 0.0
    
    noise = random.gauss(0, 0.4)
    return max(0.0, base + low_freq + high_freq + spike + noise)

# --- PROFIL YONETICISI ---
# Bildiride 'Scenario A', 'Scenario B' olarak atif yapmak icin kullanisli
PROFILLER = {
    'sabit':       lambda t: 5.0,
    'sinusoidal':  lambda t: sinusoidal_wind(t, base=5.0, amplitude=4.0, period=80),
    'basamakli':   lambda t: step_wind(t, [(0, 3), (100, 12), (250, 6)]),
    'turbulansli': lambda t: turbulent_wind(t, base=6.0),
}

def get_wind_speed(profile_name, t):
    """Gecersiz profil ismi girilirse hata vermemesi icin koruma."""
    func = PROFILLER.get(profile_name, PROFILLER['sabit'])
    return func(t)
def gercekci_ruzgar(t, ortalama_yatay=5.0, ortalama_dikey=0.0,
                    std_yatay=1.5, std_dikey=0.5, seed=None):
    """
    Gerçekçi 3D rüzgar modeli.
    Yatay: Gaussian süreç + sinüsoidal esinti
    Dikey: Updraft/downdraft Gaussian gürültüsü

    Dönüş: (v_yatay, v_dikey) tuple
    """
    import random
    if seed is not None:
        random.seed(seed + int(t))

    # Yatay bileşen
    esinti   = std_yatay * math.sin(2 * math.pi * t / 47)
    gurultu  = random.gauss(0, std_yatay * 0.5)
    v_yatay  = max(0.0, ortalama_yatay + esinti + gurultu)

    # Dikey bileşen (updraft pozitif, downdraft negatif)
    v_dikey = random.gauss(ortalama_dikey, std_dikey)
    # Ani updraft olayı (arazi etkisi)
    if int(t) % 89 == 0:
        v_dikey += random.gauss(2.0, 0.5)

    return round(v_yatay, 3), round(v_dikey, 3)


PROFILLER['gercekci_3d'] = lambda t: gercekci_ruzgar(t)[0]
