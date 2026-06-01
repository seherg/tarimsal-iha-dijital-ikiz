"""
Dinamik Ruzgar Senaryolari - Genisletilmis v2
4 profil + istatistiksel ozet + tez grafikleri
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import math, random, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import yaml
import re

with open('config.yaml') as f:
    cfg = yaml.safe_load(f)

from modules.payload_model import total_mass, estimated_current
from modules.battery_model  import energy_remaining, terminal_voltage
from energy_model           import pnr_energy_required
from modules.wind_model     import PROFILLER as WIND_PROFILLER

os.makedirs('plots', exist_ok=True)
os.makedirs('logs',  exist_ok=True)

BAT_KAP = 9.5
V_NOM   = 12.6
DT      = 1.0
MAX_T   = 800
MESAFE  = 500.0

random.seed(42)
np.random.seed(42)

# ── 4 RÜZGAR PROFİLİ ──────────────────────────────────────────
PROFILLER = {
    'Sabit\n(3 m/s)':            lambda t: 3.0,
    'Sinüsoidal\n(ort. 5 m/s)':  WIND_PROFILLER['sinusoidal'],
    'Basamaklı\n(3→12→7)':       WIND_PROFILLER['basamakli'],
    'Türbülanslı\n(ort. 5 m/s)': WIND_PROFILLER['turbulansli'],
}

# ── SİMÜLASYON ────────────────────────────────────────────────
print("=" * 65)
print("Dinamik Ruzgar Senaryolari — Genisletilmis v2")
print("=" * 65)

sonuclar = {}
for profil_adi, wind_fn in PROFILLER.items():
    random.seed(42); np.random.seed(42)
    bat_wh = BAT_KAP
    t      = 0.0
    pnr_t  = None
    recs   = []

    while t < MAX_T:
        mass   = total_mass(t)
        vw     = wind_fn(t)
        i_est  = estimated_current(mass, vw)
        bat_wh = max(0.0, bat_wh - (i_est * V_NOM) * DT / 3600.0)
        bat_pct= (bat_wh / BAT_KAP) * 100.0
        dist   = min(t * cfg['iha']['cruise_speed_ms'], MESAFE)
        e_pnr  = pnr_energy_required(max(dist, 10), mass, vw)
        v_term = terminal_voltage(bat_pct, i_est)

        recs.append({
            't': t, 'v_wind': round(vw, 2),
            'bat_pct': round(bat_pct, 2),
            'e_kalan': round(bat_wh, 4),
            'e_pnr':   round(e_pnr,  4),
            'mass':    round(mass,    1),
            'i_est':   round(i_est,   3),
            'v_term':  round(v_term,  3),
            'pnr':     0
        })

        if bat_wh <= e_pnr and pnr_t is None:
            pnr_t = t
            recs[-1]['pnr'] = 1
            break

        bat_wh = max(0.0, bat_wh)
        if bat_wh <= 0:
            break
        t += DT

    df = pd.DataFrame(recs)
    import re; etiket = re.sub(r'[^a-zA-Z0-9_]', '', profil_adi.replace('\n', '_').replace(' ', '_'))
    df.to_csv(f'logs/wind_{etiket}.csv', index=False)
    sonuclar[profil_adi] = {'df': df, 'pnr_t': pnr_t}

    vw_ort = df['v_wind'].mean()
    vw_max = df['v_wind'].max()
    vw_std = df['v_wind'].std()
    print(f"\nProfil : {profil_adi.replace(chr(10),' ')}")
    print(f"  PNR  : {pnr_t:.0f}s" if pnr_t else "  PNR  : Tetiklenmedi")
    print(f"  Rüzgar ort/max/std: {vw_ort:.2f} / {vw_max:.2f} / {vw_std:.2f} m/s")
    print(f"  Batarya@PNR: %{df.iloc[-1]['bat_pct']:.1f}")

# ── GRAFİK 1: 4 Profil Detay (2x2) ───────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(14, 9))
fig.suptitle('Dinamik Rüzgar Profili Analizi: PNR Karar Davranışı',
             fontsize=13, fontweight='bold', color='#1F4E79')

renkler = ['#185FA5','#1D9E75','#D85A30','#534AB7']

for ax, (padi, veri), renk in zip(axes.flat, sonuclar.items(), renkler):
    df   = veri['df']
    pnr  = veri['pnr_t']

    ax2 = ax.twinx()

    # Rüzgar profili (sol eksen)
    ax.fill_between(df['t'], df['v_wind'], alpha=0.2, color=renk)
    ax.plot(df['t'], df['v_wind'], color=renk, lw=1.5, alpha=0.8, label='Rüzgar (m/s)')

    # Enerji dengesi (sağ eksen)
    ax2.plot(df['t'], df['e_kalan'], color='#1D9E75', lw=2.5, label='E_remaining (Wh)')
    ax2.plot(df['t'], df['e_pnr'],   color='#A32D2D', lw=2,
             linestyle='--', label='E_pnr (Wh)')

    # PNR çizgisi
    if pnr:
        ax.axvline(pnr, color='#A32D2D', lw=2.5, linestyle=':', label=f'PNR@{pnr:.0f}s')
        ax2.axvline(pnr, color='#A32D2D', lw=2.5, linestyle=':', alpha=0.5)

    ax.set_title(padi.replace('\n', ' — '), fontsize=11, fontweight='bold')
    ax.set_xlabel('Süre (s)')
    ax.set_ylabel('Rüzgar (m/s)', color=renk)
    ax2.set_ylabel('Enerji (Wh)', color='#1D9E75')
    ax.tick_params(axis='y', labelcolor=renk)
    ax2.tick_params(axis='y', labelcolor='#1D9E75')
    ax.grid(True, alpha=0.3)

    lines1, lbl1 = ax.get_legend_handles_labels()
    lines2, lbl2 = ax2.get_legend_handles_labels()
    ax.legend(lines1+lines2, lbl1+lbl2, fontsize=8, loc='upper right')

    # İstatistik kutusu
    vw_ort = df['v_wind'].mean()
    vw_std = df['v_wind'].std()
    info   = f'μ={vw_ort:.1f} σ={vw_std:.1f} m/s'
    ax.text(0.02, 0.08, info, transform=ax.transAxes,
            fontsize=8, color='#444',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

plt.tight_layout()
plt.savefig('plots/dinamik_ruzgar_detay.png', dpi=150, bbox_inches='tight')
print("\nGrafik 1: plots/dinamik_ruzgar_detay.png")

# ── GRAFİK 2: Karşılaştırma Özet ─────────────────────────────
fig2, axes2 = plt.subplots(1, 3, figsize=(14, 5))
fig2.suptitle('Rüzgar Senaryoları Karşılaştırma Özeti',
              fontsize=13, fontweight='bold', color='#1F4E79')

etiketler = [k.replace('\n', '\n') for k in sonuclar.keys()]
pnr_sureler = [v['pnr_t'] or 0 for v in sonuclar.values()]
vw_ortalar  = [v['df']['v_wind'].mean()   for v in sonuclar.values()]
vw_stdlar   = [v['df']['v_wind'].std()    for v in sonuclar.values()]
bat_pnrler  = [v['df'].iloc[-1]['bat_pct'] for v in sonuclar.values()]

x = np.arange(len(etiketler))

# Panel 1: PNR zamanı
ax = axes2[0]
bars = ax.bar(x, pnr_sureler, color=renkler, alpha=0.85, width=0.55)
ax.set_xticks(x); ax.set_xticklabels(etiketler, fontsize=8.5)
ax.set_ylabel('PNR Zamanı (s)'); ax.set_title('PNR Tetiklenme Zamanı')
ax.grid(True, alpha=0.3, axis='y')
for bar, val in zip(bars, pnr_sureler):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+2,
            f'{val:.0f}s', ha='center', va='bottom', fontsize=9, fontweight='bold')

# Panel 2: Rüzgar ort ± std
ax = axes2[1]
ax.bar(x, vw_ortalar, color=renkler, alpha=0.75, width=0.55, label='Mean')
ax.errorbar(x, vw_ortalar, yerr=vw_stdlar, fmt='none',
            color='#333', capsize=6, lw=2, label='±Std')
ax.set_xticks(x); ax.set_xticklabels(etiketler, fontsize=8.5)
ax.set_ylabel('Rüzgar Hızı (m/s)'); ax.set_title('Rüzgar İstatistikleri (Ort. ± Std)')
ax.legend(fontsize=9); ax.grid(True, alpha=0.3, axis='y')

# Panel 3: Batarya @ PNR
ax = axes2[2]
bars = ax.bar(x, bat_pnrler, color=renkler, alpha=0.85, width=0.55)
ax.axhline(15, color='#A32D2D', lw=2, linestyle='--', label='Statik eşik referansı (15%)')
ax.set_xticks(x); ax.set_xticklabels(etiketler, fontsize=8.5)
ax.set_ylabel('Batarya (%)'); ax.set_title('PNR Anında Batarya Seviyesi')
ax.legend(fontsize=9); ax.grid(True, alpha=0.3, axis='y')
for bar, val in zip(bars, bat_pnrler):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.3,
            f'{val:.1f}%', ha='center', va='bottom', fontsize=9)

plt.tight_layout()
plt.savefig('plots/dinamik_ruzgar_ozet.png', dpi=150, bbox_inches='tight')
print("Grafik 2: plots/dinamik_ruzgar_ozet.png")

# ── İSTATİSTİKSEL ÖZET TABLOSU ────────────────────────────────
print("\n" + "=" * 70)
print(f"{'Profil':<22} {'PNR(s)':>7} {'Rz.Ort':>7} {'Rz.Std':>7} "
      f"{'Rz.Max':>7} {'Bat@PNR':>8}")
print("-" * 70)
for padi, veri in sonuclar.items():
    df  = veri['df']
    pnr = veri['pnr_t']
    print(f"{padi.replace(chr(10),' '):<22} "
          f"{pnr:>7.0f} {df['v_wind'].mean():>7.2f} "
          f"{df['v_wind'].std():>7.2f} {df['v_wind'].max():>7.2f} "
          f"{df.iloc[-1]['bat_pct']:>7.1f}%")
print("=" * 70)
