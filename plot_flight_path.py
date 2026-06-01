"""
2B Uçuş Yörüngesi Görselleştirmesi
====================================
İP-6 gereksinimi:
  "RTH komutunun tetiklendiği konum tarla haritası üzerinde işaretlenir"

Simülasyon matematiksel model üzerinde çalıştığından GPS verisi yok.
Drone'un 500m hedef noktasına doğru düz ilerlediği varsayılır.
Her senaryo için PNR anındaki konum hesaplanır ve harita üzerinde gösterilir.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import glob
import os

os.makedirs('plots', exist_ok=True)

csv_list = sorted(glob.glob('logs/senaryo_ozet_*.csv'))
if not csv_list:
    print("HATA: logs/ozet_*.csv bulunamadı.")
    print("Önce python run_scenarios.py çalıştırın.")
    exit(1)

csv_path = csv_list[-1]
print(f"CSV: {csv_path}")
df = pd.read_csv(csv_path)

# ── Sabitler ──────────────────────────────────────────────────
TARLA_X      = 200    # m — tarla genişliği
TARLA_Y      = 200    # m — tarla uzunluğu
HEDEF_MESAFE = 500    # m — drone'un hedef noktası (tarla dışı)
CRUISE_SPEED = 5.0    # m/s

# ── Senaryo renkleri ──────────────────────────────────────────
RENKLER = {
    'A_baseline'        : '#999999',
    'B_dynamic_mass'    : '#185FA5',
    'C_wind_3'          : '#1D9E75',
    'C_wind_7'          : '#D85A30',
    'C_wind_12'         : '#A32D2D',
    'D_real_3'          : '#534AB7',
    'D_real_7'          : '#B7534A',
    'D_real_12'         : '#4AB753',
    'E_pnr_accuracy_3'  : '#185FA5',
    'E_pnr_accuracy_7'  : '#D85A30',
    'E_pnr_accuracy_12' : '#A32D2D',
}

# ── Konum hesapla ─────────────────────────────────────────────
# Drone ev noktasından (0,0) doğrusal olarak (500, 0)'a gidiyor
# PNR anındaki x konumu = cruise_speed * pnr_t
def pnr_konum(pnr_t):
    x = min(CRUISE_SPEED * pnr_t, HEDEF_MESAFE)
    y = 0.0
    return x, y

# ══════════════════════════════════════════════════════════════
# GRAFİK 1: C vs D — Karşılaştırmalı 2 satır harita
# ══════════════════════════════════════════════════════════════
df_tek = df[df['run'] == 1].copy()

fig, axes = plt.subplots(2, 3, figsize=(15, 8))
fig.suptitle(
    'Statik Kütle (C) ve Dinamik Kütle (D): Görev Sonucu Karşılaştırması\n'
    'Drone nerede geri dönmek zorunda kalıyor?',
    fontsize=13, fontweight='bold', color='#1F4E79'
)

c_d_pairs = [
    ('C_wind_3',  'D_real_3',  '3 m/s',  '#1D9E75'),
    ('C_wind_7',  'D_real_7',  '7 m/s',  '#D85A30'),
    ('C_wind_12', 'D_real_12', '12 m/s', '#A32D2D'),
]

for col, (c_key, d_key, vw_label, renk) in enumerate(c_d_pairs):
    for row_idx, (key, satir_baslik) in enumerate([
        (c_key, 'C: Statik Kütle (Literatür)'),
        (d_key, 'D: Dinamik Kütle (DT v2.0)'),
    ]):
        ax = axes[row_idx][col]
        row_data = df[(df['senaryo_key'] == key) & (df['run'] == 1)]
        if row_data.empty:
            continue

        pnr_t   = row_data['pnr_t_s'].values[0]
        bat_pnr = row_data['bat_pnr_pct'].values[0]
        x, _    = pnr_konum(pnr_t)
        gorev_tamamlandi = x >= HEDEF_MESAFE

        # Arka plan rengi
        bg_renk = '#E8F5E9' if gorev_tamamlandi else '#FFEBEE'
        ax.set_facecolor(bg_renk)

        # Tarla
        tarla_r = plt.Rectangle((0, -15), TARLA_X, 30,
                                  linewidth=1.5, edgecolor='#2E7D32',
                                  facecolor='#C8E6C9', alpha=0.4)
        ax.add_patch(tarla_r)

        # Uçuş rotası
        ax.plot([0, HEDEF_MESAFE], [0, 0], '--',
                color='#BDBDBD', lw=1.5, alpha=0.7, zorder=1)

        # Ev
        ax.plot(0, 0, 'k^', markersize=11, zorder=5)

        # Hedef
        ax.plot(HEDEF_MESAFE, 0, '^', markersize=11, color='#2E7D32')

        if gorev_tamamlandi:
            # Tüm rota yeşil — görev tamamlandı
            ax.plot([0, HEDEF_MESAFE], [0, 0],
                    color='#2E7D32', lw=3, zorder=2)
            ax.plot(HEDEF_MESAFE, 0, '*', color='#2E7D32',
                    markersize=18, zorder=6)
            ax.text(HEDEF_MESAFE/2, 8,
                    '✓ Görev Tamamlandı',
                    ha='center', fontsize=9, color='#2E7D32',
                    fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.3',
                              facecolor='white', edgecolor='#2E7D32'))
        else:
            # Gidilen kısım renkli, kalan gri
            ax.plot([0, x], [0, 0], color=renk, lw=3, zorder=2)
            ax.plot([x, HEDEF_MESAFE], [0, 0],
                    color='#BDBDBD', lw=2, ls=':', zorder=2, alpha=0.5)
            # RTH noktası
            ax.plot(x, 0, 'o', color=renk, markersize=13,
                    markeredgecolor='white', markeredgewidth=2, zorder=6)
            # RTH oku (geri dönüş)
            ax.annotate('', xy=(0, 0), xytext=(x, 0),
                        arrowprops=dict(arrowstyle='->',
                                        color=renk, lw=2, alpha=0.7))
            ax.text(x/2, -10,
                    f'✗ RTH@{x:.0f}m',
                    ha='center', fontsize=9, color=renk,
                    fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.3',
                              facecolor='white', edgecolor=renk))

        # Bilgi
        durum = "✓ Tamamlandı" if gorev_tamamlandi else f"✗ İptal@{x:.0f}m"
        ax.text(5, 18, f'Rüzgar: {vw_label} | PNR: {pnr_t:.0f}s | '
                       f'Bat: {bat_pnr:.1f}% | {durum}',
                fontsize=8, va='top', color='#333',
                bbox=dict(boxstyle='round,pad=0.3',
                          facecolor='white', alpha=0.85))

        # Başlık
        satir_renk = '#555555' if row_idx == 0 else '#185FA5'
        ax.set_title(f'{satir_baslik} {vw_label}',
                     fontsize=9, fontweight='bold', color=satir_renk)

        ax.set_xlim(-20, HEDEF_MESAFE + 30)
        ax.set_ylim(-25, 30)
        ax.set_xlabel('Evden Uzaklık (m)', fontsize=8)
        if col == 0:
            ax.set_ylabel('Lateral (m)', fontsize=8)
        ax.grid(True, alpha=0.2)
        ax.tick_params(labelsize=8)

        # HOME / TARGET etiketleri
        ax.text(2, -18, 'HOME', fontsize=7, fontweight='bold', color='black')
        ax.text(HEDEF_MESAFE-2, -18, 'HEDEF',
                fontsize=7, fontweight='bold', ha='right', color='#2E7D32')

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig('plots/flight_path_2d.png', dpi=150, bbox_inches='tight')
print("Grafik 1: plots/flight_path_2d.png")

# ══════════════════════════════════════════════════════════════
# GRAFİK 2: D senaryoları karşılaştırması — büyütülmüş
# ══════════════════════════════════════════════════════════════
fig2, axes2 = plt.subplots(1, 3, figsize=(15, 5))
fig2.suptitle(
    'Senaryo D: Farklı Rüzgar Hızlarında RTH Tetiklenme Konumu\n'
    'Dinamik Kütle + Rüzgar: Gerçekçi Tarımsal Koşullar',
    fontsize=12, fontweight='bold', color='#1F4E79'
)

d_senaryolar = [
    ('D_real_3',  '3 m/s',  '#1D9E75'),
    ('D_real_7',  '7 m/s',  '#D85A30'),
    ('D_real_12', '12 m/s', '#A32D2D'),
]

for ax, (key, vw_label, renk) in zip(axes2, d_senaryolar):
    row = df[(df['senaryo_key'] == key) & (df['run'] == 1)]
    if row.empty:
        continue

    pnr_t   = row['pnr_t_s'].values[0]
    bat_pnr = row['bat_pnr_pct'].values[0]
    x, y    = pnr_konum(pnr_t)

    # Tarla
    tarla2 = plt.Rectangle((0, -50), TARLA_X, TARLA_Y,
                             linewidth=2, edgecolor='#2E7D32',
                             facecolor='#E8F5E9', alpha=0.5)
    ax.add_patch(tarla2)

    # Uçuş rotası
    ax.plot([0, HEDEF_MESAFE], [0, 0], '--', color='#999', lw=1.5, alpha=0.6)

    # Ev ve hedef
    ax.plot(0, 0, 'k^', markersize=12, zorder=5)
    ax.plot(HEDEF_MESAFE, 0, 'gs', markersize=10, zorder=5)

    gorev_tamamlandi = x >= HEDEF_MESAFE

    if gorev_tamamlandi:
        # Görev tamamlandı — yeşil yıldız
        ax.plot(HEDEF_MESAFE, 0, '*', color='#2E7D32',
                markersize=22, zorder=6)
        ax.text(HEDEF_MESAFE, 22, '✓ GÖREV\nTAMAMLANDI',
                ha='center', fontsize=9, color='#2E7D32',
                fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.4',
                          facecolor='#E8F5E9', edgecolor='#2E7D32',
                          linewidth=2))
        # Mesafe çizgisi
        ax.annotate('', xy=(HEDEF_MESAFE, -30), xytext=(0, -30),
                    arrowprops=dict(arrowstyle='<->', color='#2E7D32', lw=1.5))
        ax.text(HEDEF_MESAFE/2, -42, f'{HEDEF_MESAFE:.0f}m ✓',
                ha='center', fontsize=10, fontweight='bold', color='#2E7D32')
    else:
        # Görev yarıda — RTH noktası
        ax.plot(x, 0, 'o', color=renk, markersize=15,
                markeredgecolor='white', markeredgewidth=2, zorder=6)
        ax.annotate('', xy=(0, 0), xytext=(x, 0),
                    arrowprops=dict(arrowstyle='->', color=renk,
                                   lw=2.5, alpha=0.8))
        ax.annotate('', xy=(x, -30), xytext=(0, -30),
                    arrowprops=dict(arrowstyle='<->', color='#333', lw=1.5))
        ax.text(x/2, -42, f'{x:.0f}m — RTH',
                ha='center', fontsize=10, fontweight='bold', color=renk)
        ax.text(x, 20, f'RTH\n@{pnr_t:.0f}s',
                ha='center', fontsize=9, color=renk, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='white',
                          edgecolor=renk, alpha=0.9))

    # Bilgi kutusu
    durum = "✓ Tamamlandı" if gorev_tamamlandi else "✗ İptal"
    info = (f'Rüzgar: {vw_label}\n'
            f'PNR: {pnr_t:.0f}s\n'
            f'Durum: {durum}\n'
            f'Batarya@PNR: {bat_pnr:.1f}%')
    ax.text(10, 85, info, fontsize=9, ha='left', va='top',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white',
                      edgecolor=renk, linewidth=2))

    # Etiketler
    ax.text(3, 8, 'HOME', fontsize=8, fontweight='bold')
    ax.text(HEDEF_MESAFE-3, 8, 'HEDEF', fontsize=8,
            fontweight='bold', ha='right', color='#2E7D32')

    ax.set_xlim(-20, HEDEF_MESAFE + 20)
    ax.set_ylim(-60, 100)
    ax.set_title(f'D: Dinamik Kütle + {vw_label}',
                 fontweight='bold', color=renk)
    ax.set_xlabel('Evden Uzaklık (m)')
    if ax == axes2[0]:
        ax.set_ylabel('Lateral Position (m)')
    ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('plots/flight_path_D_scenarios.png', dpi=150, bbox_inches='tight')
print("Grafik 2: plots/flight_path_D_scenarios.png")

# ── Sayısal özet ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("RTH Tetiklenme Konumları")
print("=" * 60)
print(f"{'Senaryo':<35} {'PNR_t':>7} {'Konum':>8} {'Kalan%':>8}")
print("-" * 60)
for _, row in df_tek.iterrows():
    pnr_t = row['pnr_t_s']
    if pd.isna(pnr_t):
        continue
    x, _ = pnr_konum(pnr_t)
    kalan_pct = (1 - x / HEDEF_MESAFE) * 100
    kisa = row['label'].split('(')[0].strip()[:34]
    print(f"  {kisa:<33} {pnr_t:>6.0f}s {x:>7.0f}m {kalan_pct:>7.1f}%")
print("=" * 60)
print("\n% Kalan: Hedefe ulaşmadan dönen mesafe oranı")