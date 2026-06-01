"""
C vs D Karşılaştırma Grafiği
"Dinamik kütle modeli olmadan PNR ne kadar sapıyor?"

C: Sabit kütle + rüzgar  → mevcut literatür yaklaşımı
D: Dinamik kütle + rüzgar → DT v2.0 yaklaşımı

Her rüzgar hızı için (3, 7, 12 m/s):
  - PNR zamanı farkı (saniye)
  - Batarya seviyesi farkı (%)
  - Enerji dengesi karşılaştırması
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'DejaVu Sans'
import glob
import os

os.makedirs('plots', exist_ok=True)

csv_list = sorted(glob.glob('logs/senaryo_ozet_*.csv'))
if not csv_list:
    print("HATA: logs/ozet_*.csv bulunamadı.")
    print("Önce python scenario_runner.py çalıştırın.")
    exit(1)

csv_path = csv_list[-1]
print(f"CSV: {csv_path}")
df = pd.read_csv(csv_path)

# ── C ve D verilerini çek ─────────────────────────────────────
c_keys = ['C_wind_3', 'C_wind_7', 'C_wind_12']
d_keys = ['D_real_3', 'D_real_7', 'D_real_12']
vw_labels = ['3 m/s', '7 m/s', '12 m/s']

c_data = (df[df['senaryo_key'].isin(c_keys)]
          .groupby('senaryo_key', sort=False).mean(numeric_only=True)
          .reindex(c_keys).reset_index())
d_data = (df[df['senaryo_key'].isin(d_keys)]
          .groupby('senaryo_key', sort=False).mean(numeric_only=True)
          .reindex(d_keys).reset_index())

pnr_c   = c_data['pnr_t_s'].values
pnr_d   = d_data['pnr_t_s'].values
bat_c   = c_data['bat_pnr_pct'].values
bat_d   = d_data['bat_pnr_pct'].values
ekal_c  = c_data['e_kalan_wh'].values
ekal_d  = d_data['e_kalan_wh'].values
epnr_c  = c_data['e_pnr_wh'].values
epnr_d  = d_data['e_pnr_wh'].values

pnr_fark  = pnr_d  - pnr_c    # pozitif = D daha geç tetiklendi
bat_fark  = bat_d  - bat_c    # negatif = D'de daha az batarya kaldı

# ── Renkler ───────────────────────────────────────────────────
RENK_C   = '#999999'   # gri — statik/literatür
RENK_D   = '#185FA5'   # mavi — DT v2.0
RENK_FARK = '#D85A30'  # turuncu — fark

x = np.arange(len(vw_labels))
w = 0.35

# ══════════════════════════════════════════════════════════════
# GRAFİK 1: PNR Zamanı Karşılaştırması (ana figür)
# ══════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 3, figsize=(16, 7))
fig.suptitle(
    'Dinamik Kütle Modelinin PNR Kararına Etkisi\n'
    'Senaryo C (Sabit Kütle) ile Senaryo D (Dinamik Kütle) Karşılaştırması',
    fontsize=13, fontweight='bold', color='#1F4E79'
)

def _bar_label_inside(ax, bar, txt, fontsize=9):
    """Değeri çubuğun içine (üstten %15 aşağı) yazar — dış etiketle çakışmaz."""
    h = bar.get_height()
    ax.text(bar.get_x() + bar.get_width() / 2,
            h * 0.85,
            txt, ha='center', va='top',
            fontsize=fontsize, color='white', fontweight='bold')

# Panel 1: PNR zamanı
ax = axes[0]
bars_c = ax.bar(x - w/2, pnr_c, w,
                label='C — Sabit Kütle\n(Literatür yaklaşımı)',
                color=RENK_C, alpha=0.85)
bars_d = ax.bar(x + w/2, pnr_d, w,
                label='D — Dinamik Kütle\n(DT v2.0)',
                color=RENK_D, alpha=0.85)

for bar in bars_c:
    _bar_label_inside(ax, bar, f'{bar.get_height():.0f}s')
for bar in bars_d:
    _bar_label_inside(ax, bar, f'{bar.get_height():.0f}s')

ax.set_ylim(0, max(pnr_d) * 1.22)
for i in range(len(x)):
    y_max = max(pnr_c[i], pnr_d[i])
    ax.annotate(
        f'D={pnr_fark[i]:.0f}s',
        xy=(x[i], y_max + max(pnr_d) * 0.05),
        ha='center', fontsize=9, color=RENK_FARK, fontweight='bold'
    )

ax.set_xticks(x)
ax.set_xticklabels(vw_labels)
ax.set_xlabel('Rüzgar Hızı', fontsize=10)
ax.set_ylabel('PNR Tetikleme Zamanı (s)', fontsize=10)
ax.set_title('PNR Tetikleme Zamanı\n(Daha erken = Daha muhafazakâr)', fontweight='bold')
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3, axis='y')

# Panel 2: Batarya seviyesi @ PNR
ax = axes[1]
bars_c2 = ax.bar(x - w/2, bat_c, w, label='C — Sabit Kütle', color=RENK_C, alpha=0.85)
bars_d2 = ax.bar(x + w/2, bat_d, w, label='D — Dinamik Kütle', color=RENK_D, alpha=0.85)
ax.axhline(15, color='#A32D2D', lw=2, ls='--',
           label='Sabit eşik ref. (Yang [28],\nLei [29]: %15)')

for bar in bars_c2:
    _bar_label_inside(ax, bar, f'{bar.get_height():.1f}%')
for bar in bars_d2:
    _bar_label_inside(ax, bar, f'{bar.get_height():.1f}%')

ax.set_ylim(0, max(bat_c) * 1.28)
for i in range(len(x)):
    y_max = max(bat_c[i], bat_d[i])
    ax.annotate(
        f'D={bat_fark[i]:.1f}%',
        xy=(x[i], y_max + max(bat_c) * 0.06),
        ha='center', fontsize=9, color=RENK_FARK, fontweight='bold'
    )

ax.set_xticks(x)
ax.set_xticklabels(vw_labels)
ax.set_xlabel('Rüzgar Hızı', fontsize=10)
ax.set_ylabel('PNR Kararında Batarya Doluluğu (%)', fontsize=10)
ax.set_title('PNR Anında Batarya Seviyesi\n(Daha yüksek = Daha erken/muhafazakâr)', fontweight='bold')
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3, axis='y')

# Panel 3: Enerji farkı (E_kalan @ PNR)
ax = axes[2]
bars_c3 = ax.bar(x - w/2, ekal_c, w, label='C — Kalan enerji', color=RENK_C, alpha=0.85)
bars_d3 = ax.bar(x + w/2, ekal_d, w, label='D — Kalan enerji', color=RENK_D, alpha=0.85)

for i, (ec, ed) in enumerate(zip(epnr_c, epnr_d)):
    ax.plot([x[i]-w, x[i]], [ec, ec], color=RENK_C, lw=2, ls=':', alpha=0.7)
    ax.plot([x[i], x[i]+w], [ed, ed], color=RENK_D, lw=2, ls=':', alpha=0.7)

for bar in bars_c3:
    _bar_label_inside(ax, bar, f'{bar.get_height():.2f}')
for bar in bars_d3:
    _bar_label_inside(ax, bar, f'{bar.get_height():.2f}')

ax.set_xticks(x)
ax.set_xticklabels(vw_labels)
ax.set_xlabel('Rüzgar Hızı', fontsize=10)
ax.set_ylabel('PNR Anında Kalan Enerji (Wh)', fontsize=10)
ax.set_title('PNR Anında Enerji Dengesi\n(Kesikli = E_pnr eşiği)', fontweight='bold')
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('plots/C_vs_D_comparison.png', dpi=300, bbox_inches='tight')
print("Grafik 1: plots/C_vs_D_comparison.png")

# ══════════════════════════════════════════════════════════════
# GRAFİK 2: PNR Sapma Özeti (tez için özlü figür)
# ══════════════════════════════════════════════════════════════
fig2, ax2 = plt.subplots(figsize=(8, 5))
fig2.suptitle(
    'Dinamik Kütle Modeli Olmadan PNR Karar Hatası\n'
    '(C - D: Kaç saniye erken tetikleniyor?)',
    fontsize=12, fontweight='bold', color='#1F4E79'
)

renkler_fark = ['#1D9E75', '#D85A30', '#A32D2D']
bars_f = ax2.bar(vw_labels, pnr_fark, color=renkler_fark, alpha=0.85, width=0.5)
ax2.axhline(0, color='#333', lw=1)

for bar, val in zip(bars_f, pnr_fark):
    ax2.text(bar.get_x()+bar.get_width()/2,
             bar.get_height() + (2 if val >= 0 else -8),
             f'{val:+.0f}s', ha='center', fontsize=11, fontweight='bold',
             color='#1F4E79')

ax2.set_xlabel('Rüzgar Hızı', fontsize=10)
ax2.set_ylabel('PNR Zaman Farkı: D - C (saniye)', fontsize=10)
ax2.set_title(
    'Pozitif değer = Sabit kütleli model RTH kararını erken veriyor\n'
    'Dinamik kütle modeli görevi bu kadar saniye uzatıyor',
    fontsize=9, color='#555'
)
ax2.grid(True, alpha=0.3, axis='y')
ax2.set_ylim(0, max(pnr_fark) * 1.3)

plt.tight_layout()
plt.savefig('plots/C_vs_D_pnr_delta.png', dpi=300, bbox_inches='tight')
print("Grafik 2: plots/C_vs_D_pnr_delta.png")

# ── Sayısal özet ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("C vs D Sayısal Karşılaştırma")
print("=" * 60)
print(f"{'Ruzgar':>8} | {'PNR_C':>7} | {'PNR_D':>7} | {'dPNR':>7} | "
      f"{'Bat_C':>6} | {'Bat_D':>6} | {'dBat':>6}")
print("-" * 60)
for i, vw in enumerate(vw_labels):
    print(f"{vw:>8} | {pnr_c[i]:>7.0f}s | {pnr_d[i]:>7.0f}s | "
          f"{pnr_fark[i]:>+7.0f}s | {bat_c[i]:>5.1f}% | "
          f"{bat_d[i]:>5.1f}% | {bat_fark[i]:>+5.1f}%")
print("=" * 60)
print(f"\nOrtalama PNR sapması: {np.mean(pnr_fark):.0f} saniye")
print(f"  → Statik kütle modeli RTH kararını ortalama "
      f"{np.mean(pnr_fark):.0f}s erken tetikliyor")
print(f"  → Bu, görev süresinin %{np.mean(pnr_fark)/np.mean(pnr_d)*100:.1f}'i kadar kayıp demek")

# ══════════════════════════════════════════════════════════════
# D vs (B+C) — Doğrusal Olmayan Bileşen Analizi
# ══════════════════════════════════════════════════════════════
pnr_a = df[df['senaryo_key'] == 'A_baseline']['pnr_t_s'].mean()
pnr_b = df[df['senaryo_key'] == 'B_dynamic_mass']['pnr_t_s'].mean()

b_etkisi = pnr_b - pnr_a   # dinamik kütlenin katkısı
c_etkisi = pnr_d - pnr_c   # rüzgarın katkısı (her hız için)
bc_toplam = pnr_a + b_etkisi + c_etkisi  # lineer tahmin
d_gercek  = pnr_d           # gerçek birleşik etki
dogrusal_olmayan = d_gercek - bc_toplam  # sapma

print("\n" + "=" * 65)
print("D vs (B+C) — Doğrusal Olmayan Bileşen Analizi")
print("=" * 65)
print(f"Baseline (A)          : {pnr_a:.0f}s")
print(f"Kütle etkisi (B-A)    : +{b_etkisi:.0f}s")
print()
print(f"{'Rüzgar':>8} | {'C etkisi':>10} | {'B+C tahmini':>12} | {'D gerçek':>10} | {'Fark':>8}")
print("-" * 58)
for i, vw in enumerate(vw_labels):
    print(f"{vw:>8} | {c_etkisi[i]:>+10.0f}s | {bc_toplam[i]:>11.0f}s | "
          f"{d_gercek[i]:>9.0f}s | {dogrusal_olmayan[i]:>+8.0f}s")
print("=" * 65)
print("\nFark > 0: Kütle+rüzgar birlikte daha fazla süre kazandırıyor")
print("Fark < 0: Birleşik etki lineer toplamdan daha az")