#!/bin/bash
# ============================================================
# Tarimsal IHA Dijital Ikizi - Tam Analiz Paketi
# Calistir: ./run_all.sh
# ============================================================
cd ~/digital_twin
source dt_env/bin/activate

BASARILI=0
BASARISIZ=0
BASLANGI=$(date +%s)

log() { echo -e "\n\033[1;34m[$1/$TOPLAM] $2\033[0m"; }
ok()  { echo -e "\033[1;32m  ✓ TAMAM\033[0m"; BASARILI=$((BASARILI+1)); }
err() { echo -e "\033[1;31m  ✗ HATA: $1\033[0m"; BASARISIZ=$((BASARISIZ+1)); }

TOPLAM=9

echo "======================================================"
echo "  Tarimsal IHA Dijital Ikizi - Tam Analiz Paketi"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================================"

# 1. Ana birim testleri
log 1 "Ana birim testleri (27 test)"
python3 -m pytest test_models.py -v --tb=short -q 2>&1 | tail -3
[ ${PIPESTATUS[0]} -eq 0 ] && ok || err "test_models.py basarisiz"

# 2. Dead Reckoning + Sloshing + Dikey Ruzgar testleri
log 2 "DR / Sloshing / Dikey Ruzgar testleri (13 test)"
python3 -m pytest test_dead_reckoning.py -v --tb=short -q 2>&1 | tail -3
[ ${PIPESTATUS[0]} -eq 0 ] && ok || err "test_dead_reckoning.py basarisiz"

# 3. Ana senaryo analizi (A-B-C-D-E-F)
log 3 "Senaryo analizi (A-B-C-D-E-F)"
python3 scenario_runner.py 2>&1 | tail -5
[ ${PIPESTATUS[0]} -eq 0 ] && ok || err "scenario_runner.py basarisiz"

# 4. Dinamik kutle karsilastirmasi
log 4 "Dinamik kutle karsilastirmasi (C vs D)"
python3 plot_C_vs_D.py 2>&1 | tail -5
[ ${PIPESTATUS[0]} -eq 0 ] && ok || err "plot_C_vs_D.py basarisiz"

# 5. Ucus haritasi
log 5 "Ucus haritasi ve RTH noktalari"
python3 plot_flight_path.py 2>&1 | tail -5
[ ${PIPESTATUS[0]} -eq 0 ] && ok || err "plot_flight_path.py basarisiz"

# 6. Dinamik ruzgar senaryolari
log 6 "Dinamik ruzgar senaryolari (4 profil)"
python3 run_wind_scenarios.py 2>&1 | tail -5
[ ${PIPESTATUS[0]} -eq 0 ] && ok || err "run_wind_scenarios.py basarisiz"

# 7. Sloshing + Dikey Ruzgar enerji analizi
log 7 "Sloshing + Dikey Ruzgar enerji analizi"
python3 -c "
from energy_model import pnr_energy_required, sloshing_katsayisi
import pandas as pd

senaryolar = []
for doluluk in [0.0, 0.25, 0.5, 0.75, 1.0]:
    for perdeli in [True, False]:
        for v_dikey in [0.0, 2.0, -2.0]:
            e = pnr_energy_required(500, 2000, 5.0,
                v_dikey_ms=v_dikey, perdeli_tank=perdeli,
                payload_g=doluluk*1000, max_payload_g=1000)
            k = sloshing_katsayisi(doluluk, perdeli)
            senaryolar.append({
                'doluluk': f'%{doluluk*100:.0f}',
                'tank_turu': 'Perdeli' if perdeli else 'Perdesiz',
                'v_dikey': v_dikey,
                'k_slosh': round(k, 4),
                'E_pnr_wh': round(e, 4)
            })

df = pd.DataFrame(senaryolar)
df.to_csv('logs/sloshing_analiz.csv', index=False)
print('CSV: logs/sloshing_analiz.csv')
" 2>&1
[ ${PIPESTATUS[0]} -eq 0 ] && ok || err "Sloshing analizi basarisiz"

# 8. Sloshing grafigi
log 8 "Sloshing + Dikey Ruzgar grafigi"
python3 plot_sloshing.py 2>&1 | tail -3
[ ${PIPESTATUS[0]} -eq 0 ] && ok || err "plot_sloshing.py basarisiz"

# 9. HTML rapor
log 9 "HTML rapor uretimi"
python3 generate_report.py 2>&1 | tail -3
[ ${PIPESTATUS[0]} -eq 0 ] && ok || err "generate_report.py basarisiz"

# OZET
SURE=$(($(date +%s) - BASLANGI))
echo ""
echo "======================================================"
echo "  OZET: $BASARILI/$TOPLAM basarili | Sure: ${SURE}s"
echo "  Ciktilar:"
echo "    plots/  -> $(ls plots/*.png 2>/dev/null | wc -l) grafik"
echo "    logs/   -> $(ls logs/*.csv 2>/dev/null | wc -l) CSV, $(ls logs/*.html 2>/dev/null | wc -l) HTML rapor"
echo "    Tarih   : $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================================"