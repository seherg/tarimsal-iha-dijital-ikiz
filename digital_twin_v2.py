"""
Tarimsal IHA Dijital Ikizi v2.0
Moduler mimari - baglanti kopma yonetimi dahil
"""
from pymavlink import mavutil
from energy_model import pnr_energy_required, haversine
from modules.payload_model  import total_mass, payload_mass, estimated_current
from modules.battery_model  import energy_remaining, terminal_voltage
from modules.re_simulation  import re_simulate_pnr
from modules.dead_reckoning import DeadReckoning
import time, csv, os, yaml, math
from modules.dt_logger import get_logger
logger, _log_path = get_logger('DigitalTwinV2')

with open('config.yaml') as f:
    cfg = yaml.safe_load(f)

V_WIND          = cfg['ruzgar']['baslangic_ms']
WIND_EVENT_TIME = cfg['ruzgar']['olay_zamani_s']
WIND_EVENT_SPD  = cfg['ruzgar']['olay_hizi_ms']
LOG_FILE        = cfg['log']['dosya']
TAKEOFF_ALT     = cfg['iha']['takeoff_alt_m']
TARGET_DIST     = cfg['iha']['target_distance_m']
DR_TIMEOUT          = cfg['guvenlik']['dead_reckoning_s']
BATARYA_KRITIK_PCT  = cfg['batarya']['kritik_esik_pct']
RECONNECT_LIMIT     = 3   # maksimum yeniden baglanti denemesi

os.makedirs('logs', exist_ok=True)
os.makedirs('plots', exist_ok=True)

def baglanti_kur(adres='udpin:127.0.0.1:14551', deneme=1):
    """
    SITL baglantisini kurar. Basarisiz olursa yeniden dener.
    deneme: kacinci deneme oldugunu gosterir (loglama icin).
    """
    print(f"  Baglanti deneniyor ({deneme}/{RECONNECT_LIMIT})...")
    mav = mavutil.mavlink_connection(adres)
    mav.wait_heartbeat(timeout=10)
    return mav

print("=" * 60)
print("Tarimsal IHA Dijital Ikizi v2.0")
print(f"  Ruzgar: {V_WIND} m/s  |  Olay: {WIND_EVENT_SPD} m/s @ {WIND_EVENT_TIME}s")
print("=" * 60)

# --- Ilk baglanti ---
mav = None
for i in range(1, RECONNECT_LIMIT + 1):
    try:
        mav = baglanti_kur(deneme=i)
        print("Baglanti kuruldu!\n")
        break
    except Exception as e:
        print(f"  Baglanti hatasi: {e}")
        if i == RECONNECT_LIMIT:
            print("KRITIK: Baglanti kurulamadi, sistem durduruluyor.")
            exit(1)
        time.sleep(3)

# --- Ev konumu ---
HOME = None
while HOME is None:
    msg = mav.recv_match(type='GPS_RAW_INT', blocking=True, timeout=2)
    if msg:
        HOME = (msg.lat / 1e7, msg.lon / 1e7)
print(f"Ev: {HOME[0]:.6f}, {HOME[1]:.6f}")

# --- Kalkis ---
for cmd, params, label in [
    (mavutil.mavlink.MAV_CMD_DO_SET_MODE,          [1,4,0,0,0,0,0], "Guided mod"),
    (mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, [1,0,0,0,0,0,0], "Arm"),
    (mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,          [0,0,0,0,0,0,TAKEOFF_ALT], "Kalkis"),
]:
    mav.mav.command_long_send(mav.target_system, mav.target_component,
                              cmd, 0, *params)
    time.sleep(3 if "Arm" in label else 2)
    print(f"  {label}")

time.sleep(8)

hedef_lon_offset = TARGET_DIST / 111320.0 / math.cos(math.radians(HOME[0]))
mav.mav.set_position_target_global_int_send(
    0, mav.target_system, mav.target_component,
    mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
    0b0000111111111000,
    int(HOME[0] * 1e7), int((HOME[1] + hedef_lon_offset) * 1e7), TAKEOFF_ALT,
    0,0,0,0,0,0,0,0)
print(f"  Hedefe gidiliyor ({TARGET_DIST}m)\n")

# --- CSV ---
with open(LOG_FILE, 'w', newline='') as f:
    csv.writer(f).writerow([
        'timestamp','bat_pct','alt','lat','lon','distance_m',
        'mass_g','payload_g','est_current_A','v_terminal',
        'E_kalan_wh','E_pnr_wh','v_wind',
        'pnr_tetiklendi','dead_reckoning','re_sim_tetiklendi',
        'baglanti_koptu','kutle_bitti','ruzgar_asim','batarya_kritik'
    ])

# --- Ana dongu ---
t0              = time.time()
rth_gonderildi  = False
resim_yapildi   = False
baglanti_koptu  = False
kopma_zamani    = None
yeniden_sayi    = 0
kutle_bitti     = False
ruzgar_asim     = False
ruzgar_asim_sure = 0.0
batarya_kritik  = False
son_veri_t      = time.time()

state = {
    'lat': HOME[0], 'lon': HOME[1],
    'alt': 584.0, 'bat_pct': 100,
    'gs': 0.0, 'heading': 0.0
}
dr = DeadReckoning()
dr.update(HOME[0], HOME[1], 0.0, 0.0, 584.0)

print(f"{'Sure':>6} | {'Bat':>4} | {'Irt':>6} | {'Mes':>6} | "
      f"{'E_kal':>6} | {'E_pnr':>6} | {'Akim':>5} | {'Rzg':>4} | Karar")
print("-" * 78)

try:
    while True:
        msg        = None
        dr_active  = False
        resim_suan = False
        kopma_suan = False

        # --- Veri al ---
        try:
            msg = mav.recv_match(
                type=['GPS_RAW_INT','BATTERY_STATUS','VFR_HUD'],
                blocking=False)

            if msg:
                son_veri_t = time.time()
                if baglanti_koptu:
                    # Baglanti geri geldi
                    sure_kaybedilen = time.time() - kopma_zamani
                    print(f"\n[BAGLANTI] Yeniden kuruldu! "
                          f"Kesinti: {sure_kaybedilen:.1f}s | "
                          f"DR konum tahmini kullanildi.\n")
                    baglanti_koptu = False

                t = msg.get_type()
                if t == 'GPS_RAW_INT':
                    state['lat'] = msg.lat / 1e7
                    state['lon'] = msg.lon / 1e7
                    state['alt'] = msg.alt / 1000.0
                elif t == 'BATTERY_STATUS':
                    state['bat_pct'] = msg.battery_remaining
                elif t == 'VFR_HUD':
                    state['gs']      = msg.groundspeed
                    state['heading'] = msg.heading
                    dr.update(state['lat'], state['lon'],
                              msg.groundspeed, msg.heading, state['alt'])

        except Exception as e:
            # --- Baglanti kopma algilama ---
            if not baglanti_koptu:
                kopma_zamani   = time.time()
                baglanti_koptu = True
                kopma_suan     = True
                print(f"\n[UYARI] MAVLink baglantisi koptu! Dead Reckoning aktif.")
                logger.warning("MAVLink baglantisi koptu! Dead Reckoning aktif.")

            # --- Yeniden baglanti ---
            if baglanti_koptu and yeniden_sayi < RECONNECT_LIMIT:
                yeniden_sayi += 1
                print(f"[BAGLANTI] Yeniden baglanti deneniyor "
                      f"({yeniden_sayi}/{RECONNECT_LIMIT})...")
                try:
                    mav = baglanti_kur(deneme=yeniden_sayi)
                    print("[BAGLANTI] Basarili!")
                    yeniden_sayi  = 0
                    baglanti_koptu = False
                except Exception:
                    print(f"[BAGLANTI] Basarisiz, DR ile devam ediliyor...")

        # --- Veri zaman asimi: DR devreye al ---
        if time.time() - son_veri_t > DR_TIMEOUT:
            est = dr.estimate()
            if est[3]:
                state['lat'] = est[0]
                state['lon'] = est[1]
                state['alt'] = est[2]
                dr_active    = True

        # --- Hesaplamalar ---
        sure    = time.time() - t0
        mass    = total_mass(sure)
        payload = payload_mass(sure)
        bat     = state['bat_pct']
        dist    = haversine(state['lat'], state['lon'], HOME[0], HOME[1])
        i_est   = estimated_current(mass, V_WIND)
        v_term  = terminal_voltage(bat, i_est)
        e_kal   = energy_remaining(bat, i_est)
        e_pnr   = pnr_energy_required(max(dist, 10), mass, V_WIND)

        # --- Ruzgar olayi ---
        if sure >= WIND_EVENT_TIME and not resim_yapildi:
            old_wind = V_WIND
            V_WIND   = WIND_EVENT_SPD
            print(f"\n{'*'*55}")
            print(f"RUZGAR OLAYI: {old_wind} --> {V_WIND} m/s")
            ok, margin, report = re_simulate_pnr(state, V_WIND, HOME, sure)
            for line in report:
                print(line)
            if not ok:
                print("  [Re-Sim] KRITIK: Hemen RTH gerekiyor!")
            print(f"{'*'*55}\n")
            resim_yapildi = True
            resim_suan    = True
            e_pnr = pnr_energy_required(max(dist, 10), mass, V_WIND)
        # --- KÜTLE_BİTTİ olayı ---
        if payload <= 0.0 and not kutle_bitti:
            print(f"\n[OLAY] KÜTLE_BİTTİ — İlaç tükendi t={sure:.1f}s")
            logger.info(f"KÜTLE_BİTTİ — İlaç tükendi t={sure:.1f}s")
            kutle_bitti = True

        # --- RÜZGAR_AŞIM olayı ---
        if V_WIND > 12.0:
            ruzgar_asim_sure += 0.1
            if ruzgar_asim_sure >= 3.0 and not ruzgar_asim:
                print(f"\n[OLAY] RÜZGAR_AŞIM — {V_WIND} m/s, güvenli irtifa moduna geç")
                logger.warning(f"RÜZGAR_AŞIM — {V_WIND} m/s, güvenli irtifa moduna geç")
                ruzgar_asim = True
        else:
            ruzgar_asim_sure = 0.0

        # --- BATARYA_KRİTİK olayı ---
        if bat < BATARYA_KRITIK_PCT and not batarya_kritik:
            print(f"\n[OLAY] BATARYA_KRİTİK — %{bat:.0f} < %{BATARYA_KRITIK_PCT}, acil iniş")
            logger.critical(f"BATARYA_KRİTİK — %{bat:.0f} < %{BATARYA_KRITIK_PCT}, acil iniş")
            land_ok = False
            for _ in range(3):
                try:
                    mav.mav.command_long_send(
                        mav.target_system, mav.target_component,
                        mavutil.mavlink.MAV_CMD_NAV_LAND,
                        0, 0, 0, 0, 0, 0, 0, 0)
                    land_ok = True
                    break
                except Exception:
                    time.sleep(1)
            if land_ok:
                print("  MAV_CMD_NAV_LAND komutu gonderildi.")
            else:
                print("  [KRITIK] LAND komutu gonderilemedi - baglanti yok!")
            batarya_kritik = True

        # --- PNR karari ---
        if e_kal <= e_pnr and not rth_gonderildi:
            print(f"\n{'!'*55}")
            print(f"PNR TETIKLENDI!")
            print(f"  E_kalan={e_kal:.3f}Wh  E_pnr={e_pnr:.3f}Wh")
            print(f"  Mesafe={dist:.1f}m  Kutle={mass:.0f}g")
            print(f"  Voltaj={v_term:.2f}V  Ruzgar={V_WIND}m/s")
            if dr_active:
                print(f"  [UYARI] Bu karar Dead Reckoning konumuna dayanıyor!")
            print(f"{'!'*55}\n")
            logger.critical(
                f"PNR TETIKLENDI — E_kalan={e_kal:.3f}Wh E_pnr={e_pnr:.3f}Wh "
                f"Mesafe={dist:.1f}m Kutle={mass:.0f}g "
                f"Voltaj={v_term:.2f}V Ruzgar={V_WIND}m/s"
                + (" [Dead Reckoning konumu]" if dr_active else "")
            )

            # RTH komutunu gondermeyi dene, baglanti kopmussа tekrar dene
            rth_ok = False
            for _ in range(3):
                try:
                    mav.mav.command_long_send(
                        mav.target_system, mav.target_component,
                        mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
                        0,0,0,0,0,0,0,0)
                    rth_ok = True
                    break
                except Exception:
                    time.sleep(1)

            if rth_ok:
                print("  RTH komutu basariyla gonderildi.")
            else:
                print("  [KRITIK] RTH gonderilemedi - baglanti yok!")
            rth_gonderildi = True

        # --- Ekran ---
        if dr_active:
            karar = "*DR*"
        elif baglanti_koptu:
            karar = "KOPUK"
        elif rth_gonderildi:
            karar = "<<RTH>>"
        else:
            karar = "Devam"

        print(f"{sure:>6.1f}s | {bat:>4}% | {state['alt']:>6.1f}m | "
              f"{dist:>6.1f}m | {e_kal:>5.2f}Wh | {e_pnr:>5.2f}Wh | "
              f"{i_est:>4.1f}A | {V_WIND:>3.0f} | {karar}", end='\r')

        # --- CSV kayit ---
        with open(LOG_FILE, 'a', newline='') as f:
            csv.writer(f).writerow([
                round(time.time(),3), bat,
                round(state['alt'],2), round(state['lat'],7),
                round(state['lon'],7), round(dist,2),
                round(mass,1), round(payload,1),
                round(i_est,3), round(v_term,3),
                round(e_kal,4), round(e_pnr,4), V_WIND,
                1 if rth_gonderildi else 0,
                1 if dr_active else 0,
                1 if resim_suan else 0,
                1 if baglanti_koptu else 0,
                1 if kutle_bitti else 0,
                1 if ruzgar_asim else 0,
                1 if batarya_kritik else 0
            ])
        time.sleep(0.1)

except KeyboardInterrupt:
    print(f"\nDurduruldu.")
    print(f"RTH           : {rth_gonderildi}")
    print(f"Re-Sim        : {resim_yapildi}")
    print(f"Baglanti koptu: {baglanti_koptu}")
    print(f"Batarya kritik: {batarya_kritik}")
    print(f"Log           : {LOG_FILE}")
