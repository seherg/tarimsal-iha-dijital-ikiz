"""
Olay Gudumlu Re-Simulation Modulu.
Ruzgar aniden degisince PNR anlık yeniden hesaplanir.
Sistemi basit izleme aracinden Karar Destek Sistemine donusturur.
"""

from energy_model import pnr_energy_required, haversine
from modules.battery_model import energy_remaining
from modules.payload_model import total_mass, estimated_current, payload_mass

def re_simulate_pnr(state, new_v_wind, home, t_elapsed):
    """
    Ruzgar olayi algilaninca PNR'yi yeni parametrelerle yeniden hesaplar.

    Parametreler:
        state      : Anlik IHA durumu (lat, lon, bat_pct)
        new_v_wind : Yeni ruzgar hizi (m/s)
        home       : Ev GPS koordinatlari (lat, lon)
        t_elapsed  : Ucus suresi (saniye)

    Donus:
        can_return (bool)  : Geri donebilir mi?
        margin_wh  (float) : Enerji marji (+ guvenli, - tehlike)
        report     (list)  : Adim adim simuelasyon raporu
    """
    lat  = state.get('lat', home[0])
    lon  = state.get('lon', home[1])
    bat  = state.get('bat_pct', 100)
    mass = total_mass(t_elapsed)
    dist = haversine(lat, lon, home[0], home[1])

    i_est    = estimated_current(mass, new_v_wind)
    e_avail  = energy_remaining(bat, i_est)
    payload  = payload_mass(t_elapsed)
    e_needed = pnr_energy_required(
        max(dist, 10), mass, new_v_wind,
        payload_g=payload,
        max_payload_g=1000.0,
    )
    margin   = e_avail - e_needed

    verdict = "GUVENLI - devam edebilir" if margin > 0 else "TEHLIKE - hemen geri don!"

    report = [
        f"  [Re-Sim] Yeni ruzgar      : {new_v_wind} m/s",
        f"  [Re-Sim] Eve mesafe       : {dist:.1f} m",
        f"  [Re-Sim] Anlik kutle      : {mass:.0f} g",
        f"  [Re-Sim] Tahmini akim     : {i_est:.2f} A",
        f"  [Re-Sim] Kullanilabilir   : {e_avail:.3f} Wh",
        f"  [Re-Sim] Gerekli          : {e_needed:.3f} Wh",
        f"  [Re-Sim] Marj             : {margin:+.3f} Wh",
        f"  [Re-Sim] Sonuc            : {verdict}",
    ]
    return (margin > 0), margin, report
