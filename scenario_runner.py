"""
Tez planındaki 5 senaryoyu (A-B-C-D-E) sistematik olarak çalıştırır.

Senaryo A: Sabit kütle,   Rüzgar yok   → Baseline referans
Senaryo B: Dinamik kütle, Rüzgar yok   → Yalnızca kütle etkisi
Senaryo C: Sabit kütle,   3/7/12 m/s   → Yalnızca rüzgar etkisi
Senaryo D: Dinamik kütle, 3/7/12 m/s   → Gerçekçi operasyonel koşullar
Senaryo E: Dinamik kütle, Değişken     → PNR karar doğruluk testi (3 tekrar)

Başarı kriteri:
    E_kalan(t_PNR) >= E_min_donus  her denemede sağlanmalıdır.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import yaml
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'DejaVu Sans'
import os
from datetime import datetime
from modules.dt_logger import get_logger
logger, log_dosya = get_logger('ScenarioRunner')

# ── Config ────────────────────────────────────────────────────
with open('config.yaml') as f:
    cfg = yaml.safe_load(f)

from modules.payload_model import estimated_current, payload_mass
from modules.battery_model import terminal_voltage
from energy_model import pnr_energy_required
from modules.payload_model import total_mass, estimated_current, payload_mass
from modules.battery_model import soh_faktoru, efektif_kapasite

os.makedirs('logs', exist_ok=True)
os.makedirs('plots', exist_ok=True)

# ── Sabitler ──────────────────────────────────────────────────
BAT_KAP     = 9.5        # Wh — SITL kalibrasyonlu
V_NOM       = 12.6       # V
M_FRAME     = cfg['iha']['m_frame_g']       # gram
M_PAYLOAD0  = cfg['iha']['m_payload_g']     # gram
FLOW_RATE   = cfg['iha']['flow_rate_gs']    # gram/s
CRUISE      = cfg['iha']['cruise_speed_ms'] # m/s
DT          = 1.0
MAX_T       = 800
MESAFE      = 500.0
PNR_MARJ    = cfg['guvenlik']['pnr_marji_pct'] / 100.0

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

# ── Yardımcı fonksiyonlar ─────────────────────────────────────

def dinamik_kitle(t):
    return total_mass(t)

def sabit_kitle():
    return M_FRAME + M_PAYLOAD0

def simulate(mass_fn, wind_fn, label, tekrar=1, cycle=0):
    """
    Tek senaryo simülasyonu.
    mass_fn : t -> gram cinsinden kütle
    wind_fn : t -> m/s cinsinden rüzgar hızı
    tekrar  : kaç kez çalıştırılacak (Senaryo E için 3)
    """
    tum_sonuclar = []

    for run in range(tekrar):
        bat_kap_efektif = efektif_kapasite(cycle)
        bat_wh  = bat_kap_efektif
        t       = 0.0
        pnr_t   = None
        pnr_ok  = None
        recs    = []

        while t < MAX_T:
            mass   = mass_fn(t)
            vw     = wind_fn(t)
            i_est  = estimated_current(mass, vw)
            bat_wh = max(0.0, bat_wh - (i_est * V_NOM) * DT / 3600.0)
            bat_pct = (bat_wh / BAT_KAP) * 100.0
            dist   = min(t * CRUISE, MESAFE)
            payload = payload_mass(t) if mass_fn == dinamik_kitle else M_PAYLOAD0
            e_pnr  = pnr_energy_required(
                max(dist, 10), mass, vw,
                payload_g=payload,
                max_payload_g=M_PAYLOAD0,
            )
            v_term = terminal_voltage(bat_pct, i_est)

            recs.append({
                't'        : t,
                'mass_g'   : round(mass, 1),
                'v_wind'   : round(vw, 2),
                'bat_pct'  : round(bat_pct, 2),
                'e_kalan'  : round(bat_wh, 4),
                'e_pnr'    : round(e_pnr, 4),
                'i_est'    : round(i_est, 3),
                'v_term'   : round(v_term, 3),
                'dist_m'   : round(dist, 1),
                'pnr_flag' : 0,
                'run'      : run + 1,
                'senaryo'  : label,
            })

            if bat_wh <= e_pnr and pnr_t is None:
                pnr_esik_t = t
                komut_t    = t + DT
                gecikme_ms = DT * 1000
                pnr_t = t
                recs[-1]['pnr_flag'] = 1
                recs[-1]['gecikme_ms'] = gecikme_ms

                # Başarı kriteri: E_kalan >= E_min_donus
                e_min_donus = pnr_energy_required(
                    max(dist, 10), mass, vw) / (1 + PNR_MARJ)
                pnr_ok = bat_wh >= e_min_donus
                break

            if bat_wh <= 0:
                break
            t += DT

        df_run = pd.DataFrame(recs)
        tum_sonuclar.append({
            'run'       : run + 1,
            'label'     : label,
            'pnr_t'     : pnr_t,
            'pnr_ok'    : pnr_ok,
            'gecikme_ms'  : gecikme_ms if pnr_t else None,
            'bat_pnr'   : recs[-1]['bat_pct'] if recs else None,
            'e_kalan'   : recs[-1]['e_kalan'] if recs else None,
            'e_pnr'     : recs[-1]['e_pnr']   if recs else None,
            'df'        : df_run,
        })

    return tum_sonuclar


# ══════════════════════════════════════════════════════════════
# SENARYO TANIMLARI
# ══════════════════════════════════════════════════════════════

senaryolar = {

    'A_baseline': {
        'label'   : 'Scenario A — Baseline\n(Static mass, No wind)',
        'mass_fn' : lambda t: sabit_kitle(),
        'wind_fn' : lambda t: 0.0,
        'tekrar'  : 3,
    },

    'B_dynamic_mass': {
        'label'   : 'Scenario B — Dynamic Mass\n(Dynamic mass, No wind)',
        'mass_fn' : lambda t: dinamik_kitle(t),
        'wind_fn' : lambda t: 0.0,
        'tekrar'  : 3,
    },

    'C_wind_3': {
        'label'   : 'Scenario C1 — Wind 3 m/s\n(Static mass, 3 m/s)',
        'mass_fn' : lambda t: sabit_kitle(),
        'wind_fn' : lambda t: 3.0,
        'tekrar'  : 3,
    },

    'C_wind_7': {
        'label'   : 'Scenario C2 — Wind 7 m/s\n(Static mass, 7 m/s)',
        'mass_fn' : lambda t: sabit_kitle(),
        'wind_fn' : lambda t: 7.0,
        'tekrar'  : 3,
    },

    'C_wind_12': {
        'label'   : 'Scenario C3 — Wind 12 m/s\n(Static mass, 12 m/s)',
        'mass_fn' : lambda t: sabit_kitle(),
        'wind_fn' : lambda t: 12.0,
        'tekrar'  : 3,
    },

    'D_real_3': {
        'label'   : 'Scenario D1 — Realistic 3 m/s\n(Dynamic mass, 3 m/s)',
        'mass_fn' : lambda t: dinamik_kitle(t),
        'wind_fn' : lambda t: 3.0,
        'tekrar'  : 3,
    },

    'D_real_7': {
        'label'   : 'Scenario D2 — Realistic 7 m/s\n(Dynamic mass, 7 m/s)',
        'mass_fn' : lambda t: dinamik_kitle(t),
        'wind_fn' : lambda t: 7.0,
        'tekrar'  : 3,
    },

    'D_real_12': {
        'label'   : 'Scenario D3 — Realistic 12 m/s\n(Dynamic mass, 12 m/s)',
        'mass_fn' : lambda t: dinamik_kitle(t),
        'wind_fn' : lambda t: 12.0,
        'tekrar'  : 3,
    },
    'E_pnr_accuracy_3': {
        'label'   : 'Scenario E1 — PNR Accuracy\n(Dynamic mass, 3 m/s)',
        'mass_fn' : lambda t: dinamik_kitle(t),
        'wind_fn' : lambda t: 3.0,
        'tekrar'  : 1,
    },

    'E_pnr_accuracy_7': {
        'label'   : 'Scenario E2 — PNR Accuracy\n(Dynamic mass, 7 m/s)',
        'mass_fn' : lambda t: dinamik_kitle(t),
        'wind_fn' : lambda t: 7.0,
        'tekrar'  : 1,
    },

    'E_pnr_accuracy_12': {
        'label'   : 'Scenario E3 — PNR Accuracy\n(Dynamic mass, 12 m/s)',
        'mass_fn' : lambda t: dinamik_kitle(t),
        'wind_fn' : lambda t: 12.0,
        'tekrar'  : 1,
    },
    'F_soh_yeni': {
        'label'   : 'Scenario F1 — New Battery\n(Dynamic mass, 3 m/s, 0 cycles)',
        'mass_fn' : lambda t: dinamik_kitle(t),
        'wind_fn' : lambda t: 3.0,
        'tekrar'  : 1,
        'cycle'   : 0,
    },

    'F_soh_orta': {
        'label'   : 'Scenario F2 — Aged Battery\n(Dynamic mass, 3 m/s, 300 cycles)',
        'mass_fn' : lambda t: dinamik_kitle(t),
        'wind_fn' : lambda t: 3.0,
        'tekrar'  : 1,
        'cycle'   : 300,
    },

    'F_soh_yasli': {
        'label'   : 'Scenario F3 — Old Battery\n(Dynamic mass, 3 m/s, 500 cycles)',
        'mass_fn' : lambda t: dinamik_kitle(t),
        'wind_fn' : lambda t: 3.0,
        'tekrar'  : 1,
        'cycle'   : 500,
    },
}

# ══════════════════════════════════════════════════════════════
# KOŞTUR
# ══════════════════════════════════════════════════════════════

print("=" * 65)
print("Senaryo Analizi")
print(f"Zaman: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 65)

tum_df      = []
ozet_satirlar = []

for key, cfg_s in senaryolar.items():
    sonuclar = simulate(
            mass_fn = cfg_s['mass_fn'],
            wind_fn = cfg_s['wind_fn'],
            label   = cfg_s['label'],
            tekrar  = cfg_s['tekrar'],
            cycle   = cfg_s.get('cycle', 0),
    )

    for s in sonuclar:
        tum_df.append(s['df'])
        pnr_str = f"{s['pnr_t']:.0f}s" if s['pnr_t'] else "—"
        ok_str  = "[OK] GECTI" if s['pnr_ok'] else ("[!!] BASARISIZ" if s['pnr_ok'] is False else "-")
        logger.info(f"[{key}] Run {s['run']}: PNR={pnr_str} | Bat@PNR=%{s['bat_pnr']:.1f} | Kriter: {'[OK]' if s['pnr_ok'] else '[!!]'}")
        print(f"  [{key}] Run {s['run']}: PNR={pnr_str} | Bat@PNR=%{s['bat_pnr']:.1f} | Kriter: {'[OK]' if s['pnr_ok'] else '[!!]'}")

        ozet_satirlar.append({
            'senaryo_key' : key,
            'run'         : s['run'],
            'label'       : cfg_s['label'].replace('\n', ' '),
            'pnr_t_s'     : s['pnr_t'],
            'bat_pnr_pct' : s['bat_pnr'],
            'e_kalan_wh'  : s['e_kalan'],
            'e_pnr_wh'    : s['e_pnr'],
            'pnr_basari'  : s['pnr_ok'],
            'gecikme_ms' : s.get('gecikme_ms', None),
        })

# ── CSV kaydet ────────────────────────────────────────────────
df_ozet = pd.DataFrame(ozet_satirlar)
ozet_csv = f'logs/senaryo_ozet_{timestamp}.csv'
df_ozet.to_csv(ozet_csv, index=False)
print(f"\nÖzet CSV: {ozet_csv}")

df_detay = pd.concat(tum_df, ignore_index=True)
detay_csv = f'logs/senaryo_detay_{timestamp}.csv'
df_detay.to_csv(detay_csv, index=False)
print(f"Detay CSV: {detay_csv}")

# ══════════════════════════════════════════════════════════════
# BAŞARI KRİTERİ RAPORU
# ══════════════════════════════════════════════════════════════

print("\n" + "=" * 65)
print("BASARI KRITERI RAPORU (E_kalan >= E_min_donus)")
print("=" * 65)

e_satirlar = df_ozet[df_ozet['senaryo_key'].str.startswith('E_pnr')]
e_toplam = len(e_satirlar)
e_gecen  = e_satirlar['pnr_basari'].sum()
print(f"\nSenaryo E: {e_gecen}/{e_toplam} koşulda kriter sağlandı")

if e_gecen == e_toplam:
    print("  -> [OK] TUM DENEMELER BASARILI")
else:
    print("  -> [!!] BAZI DENEMELER BASARISIZ -- E_marj kalibrasyonu gerekiyor")

# ══════════════════════════════════════════════════════════════
# GRAFİKLER
# ══════════════════════════════════════════════════════════════

# ── Grafik 1: A vs B — Kütle etkisi ──────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle('Senaryo A ve B: Dinamik Kütlenin Enerji Bütçesine Etkisi',
             fontsize=12, fontweight='bold', color='#1F4E79')

for ax, key, renk, isim in zip(
    axes,
    ['A_baseline', 'B_dynamic_mass'],
    ['#185FA5', '#D85A30'],
    ['A — Sabit Kütle', 'B — Dinamik Kütle']
):
    df_s = df_detay[df_detay['senaryo'] == senaryolar[key]['label']].copy()
    if df_s.empty:
        continue

    ax2 = ax.twinx()
    ax.plot(df_s['t'], df_s['e_kalan'], color=renk, lw=2.5, label='Kalan enerji (Wh)')
    ax.plot(df_s['t'], df_s['e_pnr'],   color='#A32D2D', lw=2, ls='--', label='E_pnr eşiği')
    ax2.plot(df_s['t'], df_s['mass_g'], color='#534AB7', lw=1.5, ls=':', label='Kütle (g)')

    pnr_rows = df_s[df_s['pnr_flag'] == 1]
    if not pnr_rows.empty:
        px = pnr_rows.iloc[0]['t']
        ax.axvline(px, color='#A32D2D', lw=2, ls=':', label=f'PNR@{px:.0f}s')

    ax.set_title(isim, fontweight='bold')
    ax.set_xlabel('Zaman (s)')
    ax.set_ylabel('Enerji (Wh)', color=renk)
    ax2.set_ylabel('Kütle (g)', color='#534AB7')
    ax.grid(True, alpha=0.3)
    lines1, lbl1 = ax.get_legend_handles_labels()
    lines2, lbl2 = ax2.get_legend_handles_labels()
    ax.legend(lines1+lines2, lbl1+lbl2, fontsize=8)

plt.tight_layout()
plt.savefig('plots/A_vs_B.png', dpi=150, bbox_inches='tight')
print("\nGrafik: plots/A_vs_B.png")

# ── Grafik 2: C senaryoları — Rüzgar etkisi ──────────────────
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle('Senaryo C: Rüzgar Etkisi (Sabit Kütle)',
             fontsize=12, fontweight='bold', color='#1F4E79')

for ax, key, renk, vw in zip(
    axes,
    ['C_wind_3', 'C_wind_7', 'C_wind_12'],
    ['#1D9E75', '#D85A30', '#A32D2D'],
    [3, 7, 12]
):
    df_s = df_detay[df_detay['senaryo'] == senaryolar[key]['label']].copy()
    if df_s.empty:
        continue

    ax.plot(df_s['t'], df_s['e_kalan'], color=renk, lw=2.5, label='Kalan enerji')
    ax.plot(df_s['t'], df_s['e_pnr'],   color='#333', lw=1.5, ls='--', label='E_pnr eşiği')

    pnr_rows = df_s[df_s['pnr_flag'] == 1]
    if not pnr_rows.empty:
        px = pnr_rows.iloc[0]['t']
        ax.axvline(px, color='#A32D2D', lw=2, ls=':', label=f'PNR@{px:.0f}s')

    ax.set_title(f'C — Rüzgar {vw} m/s', fontweight='bold')
    ax.set_xlabel('Zaman (s)')
    ax.set_ylabel('Enerji (Wh)')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)

plt.tight_layout()
plt.savefig('plots/C_wind.png', dpi=150, bbox_inches='tight')
print("Grafik: plots/C_wind.png")

# ── Grafik 3: D senaryoları — Gerçekçi koşullar ──────────────
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle('Senaryo D: Gerçekçi Koşullar (Dinamik Kütle + Rüzgar)',
             fontsize=12, fontweight='bold', color='#1F4E79')

for ax, key, renk, vw in zip(
    axes,
    ['D_real_3', 'D_real_7', 'D_real_12'],
    ['#1D9E75', '#D85A30', '#A32D2D'],
    [3, 7, 12]
):
    df_s = df_detay[df_detay['senaryo'] == senaryolar[key]['label']].copy()
    if df_s.empty:
        continue

    ax2 = ax.twinx()
    ax.plot(df_s['t'], df_s['e_kalan'], color=renk, lw=2.5, label='Kalan enerji')
    ax.plot(df_s['t'], df_s['e_pnr'],   color='#333', lw=1.5, ls='--', label='E_pnr eşiği')
    ax2.plot(df_s['t'], df_s['mass_g'], color='#534AB7', lw=1, ls=':', alpha=0.6, label='Kütle')

    pnr_rows = df_s[df_s['pnr_flag'] == 1]
    if not pnr_rows.empty:
        px = pnr_rows.iloc[0]['t']
        ax.axvline(px, color='#A32D2D', lw=2, ls=':', label=f'PNR@{px:.0f}s')

    ax.set_title(f'D — Dinamik + {vw} m/s', fontweight='bold')
    ax.set_xlabel('Zaman (s)')
    ax.set_ylabel('Enerji (Wh)', color=renk)
    ax2.set_ylabel('Kütle (g)', color='#534AB7')
    ax.grid(True, alpha=0.3)
    lines1, lbl1 = ax.get_legend_handles_labels()
    lines2, lbl2 = ax2.get_legend_handles_labels()
    ax.legend(lines1+lines2, lbl1+lbl2, fontsize=8)

plt.tight_layout()
plt.savefig('plots/D_realistic.png', dpi=150, bbox_inches='tight')
print("Grafik: plots/D_realistic.png")

# ── Grafik 4: E senaryosu — PNR doğruluk testi ───────────────
e_labels = [senaryolar[k]['label'] for k in senaryolar if k.startswith('E_pnr')]
df_e = df_detay[df_detay['senaryo'].isin(e_labels)].copy()

if not df_e.empty:
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.suptitle('Senaryo E: PNR Doğruluk Testi (3 Deneme)',
                 fontsize=12, fontweight='bold', color='#1F4E79')

    renkler_e = ['#185FA5', '#1D9E75', '#D85A30']
    e_keys = [k for k in senaryolar if k.startswith('E_pnr')]
    for e_key, renk in zip(e_keys, renkler_e):
        df_run = df_e[df_e['senaryo'] == senaryolar[e_key]['label']]
        if df_run.empty:
            continue
        vw_label = e_key.split('_')[-1]
        ax.plot(df_run['t'], df_run['e_kalan'], color=renk, lw=2,
                label=f'E{vw_label} m/s — Kalan enerji')
        pnr_rows = df_run[df_run['pnr_flag'] == 1]
        if not pnr_rows.empty:
            px = pnr_rows.iloc[0]['t']
            ax.axvline(px, color=renk, lw=1.5, ls=':', alpha=0.7)
    # E_pnr sadece bir kez çiz (run=1 referans)
    df_r1 = df_e[df_e['run'] == 1]
    if not df_r1.empty:
        ax.plot(df_r1['t'], df_r1['e_pnr'], color='#A32D2D', lw=2,
                ls='--', label='E_pnr eşiği')

    ax.set_xlabel('Zaman (s)')
    ax.set_ylabel('Enerji (Wh)')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig('plots/E_pnr_accuracy.png', dpi=150, bbox_inches='tight')
    print("Grafik: plots/E_pnr_accuracy.png")

# ── Grafik 5: Özet karşılaştırma tablosu ─────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle('Senaryo Özeti',
             fontsize=12, fontweight='bold', color='#1F4E79')

_abcd_mask = df_ozet['senaryo_key'].str[0].isin(list('ABCD'))
df_abcd_avg = (df_ozet[_abcd_mask]
               .groupby('senaryo_key', sort=False)
               .agg(pnr_t_s=('pnr_t_s', 'mean'),
                    bat_pnr_pct=('bat_pnr_pct', 'mean'),
                    label=('label', 'first'))
               .reset_index())
df_ef1 = df_ozet[~_abcd_mask & (df_ozet['run'] == 1)][
    ['senaryo_key', 'pnr_t_s', 'bat_pnr_pct', 'label']]
df_tek = pd.concat([df_abcd_avg, df_ef1], ignore_index=True)
etiketler = [r['label'].split('(')[0].strip() for _, r in df_tek.iterrows()]
renkler_ozet = ['#185FA5','#1D9E75','#534AB7','#534AB7','#534AB7',
                '#D85A30','#D85A30','#D85A30','#A32D2D'][:len(df_tek)]

ax = axes[0]
bars = ax.bar(range(len(df_tek)), df_tek['pnr_t_s'].fillna(0),
              color=renkler_ozet, alpha=0.85)
ax.set_xticks(range(len(df_tek)))
ax.set_xticklabels(etiketler, rotation=35, ha='right', fontsize=7.5)
ax.set_ylabel('PNR Zamanı (s)')
ax.set_title('Senaryoya Göre PNR Tetikleme Zamanı')
ax.grid(True, alpha=0.3, axis='y')
for bar, val in zip(bars, df_tek['pnr_t_s'].fillna(0)):
    if val > 0:
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1,
                f'{val:.0f}s', ha='center', va='bottom', fontsize=7)

ax = axes[1]
bars = ax.bar(range(len(df_tek)), df_tek['bat_pnr_pct'].fillna(0),
              color=renkler_ozet, alpha=0.85)
ax.axhline(15, color='#A32D2D', lw=2, ls='--', label='Statik eşik referansı (15%)')
ax.set_xticks(range(len(df_tek)))
ax.set_xticklabels(etiketler, rotation=35, ha='right', fontsize=7.5)
ax.set_ylabel('PNR Anında Batarya (%)')
ax.set_title('PNR Kararında Batarya Seviyesi')
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3, axis='y')
for bar, val in zip(bars, df_tek['bat_pnr_pct'].fillna(0)):
    if val > 0:
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.3,
                f'{val:.1f}%', ha='center', va='bottom', fontsize=7)

plt.tight_layout()
plt.savefig('plots/ozet.png', dpi=150, bbox_inches='tight')
print("Grafik: plots/ozet.png")

# ── Son özet tablosu ──────────────────────────────────────────
print("\n" + "=" * 75)
print(f"{'Senaryo':<38} {'PNR(s)':>7} {'Bat%':>6} {'E_kal':>7} {'E_pnr':>7} {'Gecikme':>9} {'OK':>6}")
print("-" * 80)

_abcd_keys = [k for k in senaryolar if k[0] in 'ABCD']
_ef_mask   = ~df_ozet['senaryo_key'].str[0].isin(list('ABCD'))

# A/B/C/D — 3 run ortalaması tek satırda
for key in _abcd_keys:
    grp = df_ozet[df_ozet['senaryo_key'] == key]
    if grp.empty:
        continue
    n       = len(grp)
    pnr_str = f"{grp['pnr_t_s'].mean():.0f}"   if grp['pnr_t_s'].notna().any()     else "—"
    bat_str = f"{grp['bat_pnr_pct'].mean():.1f}" if grp['bat_pnr_pct'].notna().any() else "—"
    ek_str  = f"{grp['e_kalan_wh'].mean():.3f}"  if grp['e_kalan_wh'].notna().any()  else "—"
    ep_str  = f"{grp['e_pnr_wh'].mean():.3f}"    if grp['e_pnr_wh'].notna().any()    else "—"
    gc_mean = grp['gecikme_ms'].mean()
    gc_str  = f"{gc_mean:.0f}ms" if pd.notna(gc_mean) else "—"
    n_ok    = int(grp['pnr_basari'].sum())
    ok_str  = f"{n_ok}/{n}"
    label_k = (grp.iloc[0]['label'] + f' [ort {n}x]')[:37]
    print(f"  {label_k:<37} {pnr_str:>7} {bat_str:>6} {ek_str:>7} {ep_str:>7} {gc_str:>9} {ok_str:>6}")

# E/F — bireysel satırlar (değişmeden)
for _, r in df_ozet[_ef_mask].iterrows():
    pnr_str = f"{r['pnr_t_s']:.0f}" if pd.notna(r['pnr_t_s']) else "—"
    bat_str = f"{r['bat_pnr_pct']:.1f}" if pd.notna(r['bat_pnr_pct']) else "—"
    ek_str  = f"{r['e_kalan_wh']:.3f}" if pd.notna(r['e_kalan_wh']) else "—"
    ep_str  = f"{r['e_pnr_wh']:.3f}"   if pd.notna(r['e_pnr_wh'])   else "—"
    gc_str  = f"{r['gecikme_ms']:.0f}ms" if pd.notna(r.get('gecikme_ms', None)) else "—"
    ok_str  = "[OK]" if r['pnr_basari'] else ("[!!]" if r['pnr_basari'] is False else "-")
    label_k = r['label'][:37]
    print(f"  {label_k:<37} {pnr_str:>7} {bat_str:>6} {ek_str:>7} {ep_str:>7} {gc_str:>9} {ok_str:>6}")

# ── Grafik 6: SoH Degradasyon Etkisi ─────────────────────────
df_soh = df_ozet[df_ozet['senaryo_key'].str.startswith('F_soh')].copy()

if not df_soh.empty:
    fig_soh, axes_soh = plt.subplots(1, 2, figsize=(12, 5))
    fig_soh.suptitle(
        'Senaryo F — Batarya Yaşlanmasının PNR Kararına Etkisi\n'
        'Sağlık Durumu (SoH) Bozulma Analizi',
        fontsize=12, fontweight='bold', color='#1F4E79'
    )

    dongu = [0, 300, 500]
    pnr_sureler = df_soh['pnr_t_s'].values
    bat_pnr = df_soh['bat_pnr_pct'].values
    renkler_soh = ['#1D9E75', '#D85A30', '#A32D2D']
    etiketler = ['Yeni\n(0 döngü)', 'Orta\n(300 döngü)', 'Yaşlı\n(500 döngü)']

    # Panel 1: PNR süresi
    ax = axes_soh[0]
    bars = ax.bar(etiketler, pnr_sureler, color=renkler_soh, alpha=0.85, width=0.5)
    ax.set_ylabel('PNR Tetikleme Zamanı (s)')
    ax.set_title('Batarya Yaşına Göre Görev Süresi')
    ax.grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars, pnr_sureler):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+2,
                f'{val:.0f}s', ha='center', fontsize=11, fontweight='bold')

    # Kayıp oranı
    kayip = (pnr_sureler[0] - pnr_sureler) / pnr_sureler[0] * 100
    for i, (bar, k) in enumerate(zip(bars, kayip)):
        if k > 0:
            ax.text(bar.get_x()+bar.get_width()/2,
                    bar.get_height()/2,
                    f'-{k:.0f}%', ha='center', fontsize=10,
                    color='white', fontweight='bold')

    # Panel 2: SoH eğrisi
    ax2 = axes_soh[1]
    n_range = range(0, 501, 10)
    from modules.battery_model import soh_faktoru, efektif_kapasite
    soh_vals = [soh_faktoru(n) * 100 for n in n_range]
    cap_vals = [efektif_kapasite(n) for n in n_range]

    ax2b = ax2.twinx()
    ax2.plot(list(n_range), soh_vals, color='#185FA5', lw=2.5,
             label='SoH (%)')
    ax2b.plot(list(n_range), cap_vals, color='#D85A30', lw=2,
              ls='--', label='Kapasite (Wh)')

    # İşaret noktaları
    for n, renk, etiket in zip([0, 300, 500], renkler_soh, ['F1', 'F2', 'F3']):
        soh = soh_faktoru(n) * 100
        cap = efektif_kapasite(n)
        ax2.plot(n, soh, 'o', color=renk, markersize=10, zorder=5)
        ax2b.plot(n, cap, 's', color=renk, markersize=8, zorder=5)
        ax2.text(n+8, soh+0.5, f'{etiket}\n{soh:.1f}%',
                 fontsize=8, color=renk)

    ax2.axhline(80, color='#A32D2D', lw=1.5, ls=':',
                label='%80 eşiği (Ömür Sonu)')
    ax2.set_xlabel('Şarj Döngüsü')
    ax2.set_ylabel('Sağlık Durumu (%)', color='#185FA5')
    ax2b.set_ylabel('Efektif Kapasite (Wh)', color='#D85A30')
    ax2.set_title('SoH Bozulma Eğrisi\n(Tattu 3S LiPo Modeli)')
    ax2.set_ylim(75, 102)
    ax2.grid(True, alpha=0.3)

    lines1, lbl1 = ax2.get_legend_handles_labels()
    lines2, lbl2 = ax2b.get_legend_handles_labels()
    ax2.legend(lines1+lines2, lbl1+lbl2, fontsize=9, loc='lower left')

    plt.tight_layout()
    plt.savefig('plots/F_soh.png', dpi=150, bbox_inches='tight')
    print("Grafik: plots/F_soh.png")