"""
Sloshing + Dikey Ruzgar Enerji Analizi - Gorsel
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from energy_model import pnr_energy_required, sloshing_katsayisi
import os
os.makedirs('plots', exist_ok=True)

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle('Sloshing & Vertical Wind — Energy Impact Analysis',
             fontsize=13, fontweight='bold', color='#1F4E79')

doluluklar = np.linspace(0, 1, 50)

# Panel 1: Sloshing katsayisi
ax = axes[0]
k_perdesiz = [sloshing_katsayisi(d, perdeli_tank=False) for d in doluluklar]
k_perdeli  = [sloshing_katsayisi(d, perdeli_tank=True)  for d in doluluklar]
ax.plot(doluluklar*100, k_perdesiz, color='#D85A30', lw=2.5,
        label='Unbaffled tank (k_max=0.08)')
ax.plot(doluluklar*100, k_perdeli,  color='#1D9E75', lw=2.5,
        label='Baffled tank (k_max=0.02)')
ax.fill_between(doluluklar*100, k_perdeli, k_perdesiz,
                alpha=0.15, color='#D85A30')
ax.set_xlabel('Tank Fill Level (%)')
ax.set_ylabel('Sloshing Coefficient k')
ax.set_title('Sloshing Coefficient vs Fill Level')
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)
ax.annotate('Max sloshing\nat 50% fill', xy=(50, max(k_perdesiz)),
            xytext=(65, max(k_perdesiz)*0.9),
            arrowprops=dict(arrowstyle='->', color='#D85A30'),
            fontsize=8, color='#D85A30')

# Panel 2: Sloshing'in PNR enerjisine etkisi
ax = axes[1]
e_perdesiz = [pnr_energy_required(500, 2000, 5.0, perdeli_tank=False,
               payload_g=d*1000, max_payload_g=1000) for d in doluluklar]
e_perdeli  = [pnr_energy_required(500, 2000, 5.0, perdeli_tank=True,
               payload_g=d*1000, max_payload_g=1000) for d in doluluklar]
e_baseline = [pnr_energy_required(500, 2000-(d*1000), 5.0) for d in doluluklar]

ax.plot(doluluklar*100, e_perdesiz, color='#D85A30', lw=2.5, label='Unbaffled')
ax.plot(doluluklar*100, e_perdeli,  color='#1D9E75', lw=2.5, label='Baffled')
ax.plot(doluluklar*100, e_baseline, color='#999',    lw=1.5,
        linestyle='--', label='No sloshing (baseline)')
ax.set_xlabel('Tank Fill Level (%)')
ax.set_ylabel('E_pnr (Wh)')
ax.set_title('PNR Energy vs Tank Fill Level')
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)

# Panel 3: Dikey ruzgar etkisi
ax = axes[2]
v_dikeyler = np.linspace(-5, 5, 50)
e_dikey = [pnr_energy_required(500, 2000, 5.0, v_dikey_ms=vd) for vd in v_dikeyler]
ax.plot(v_dikeyler, e_dikey, color='#534AB7', lw=2.5)
ax.axvline(0, color='#999', lw=1, linestyle='--')
ax.axhline(e_dikey[25], color='#999', lw=1, linestyle='--', alpha=0.5)
ax.fill_betweenx(e_dikey, v_dikeyler, 0,
                 where=[v > 0 for v in v_dikeyler],
                 alpha=0.15, color='#D85A30', label='Updraft zone')
ax.fill_betweenx(e_dikey, v_dikeyler, 0,
                 where=[v < 0 for v in v_dikeyler],
                 alpha=0.15, color='#185FA5', label='Downdraft zone')
ax.set_xlabel('Vertical Wind Speed (m/s)')
ax.set_ylabel('E_pnr (Wh)')
ax.set_title('PNR Energy vs Vertical Wind\n(+updraft / -downdraft)')
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('plots/sloshing_dikey_ruzgar.png', dpi=150, bbox_inches='tight')
print("Grafik: plots/sloshing_dikey_ruzgar.png")
