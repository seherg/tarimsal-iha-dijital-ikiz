"""
Dinamik Yuk Azalma Modulu
Ilac tukendikce drone hafifler, motor akimi duser.
Tum parametreler config.yaml -> iha blogundan okunur.
"""

import yaml
import os

def _load_cfg():
    cfg_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    if not os.path.exists(cfg_path):
        cfg_path = 'config.yaml'
    with open(cfg_path) as f:
        return yaml.safe_load(f)

_cfg         = _load_cfg()
FLOW_RATE    = _cfg['iha']['flow_rate_gs']    # gram/saniye ilac tuketimi
M_FRAME      = _cfg['iha']['m_frame_g']       # govde kutle (gram)
M_PAYLOAD0   = _cfg['iha']['m_payload_g']     # baslangic ilac yuku (gram)
CRUISE_SPEED = _cfg['iha']['cruise_speed_ms'] # m/s

def payload_mass(t):
    """Kalan ilac kitlesi (gram)."""
    return max(0.0, M_PAYLOAD0 - FLOW_RATE * t)

def total_mass(t):
    """Toplam anlik kutle = govde + kalan ilac (gram)."""
    return M_FRAME + payload_mass(t)

def estimated_current(mass_g, v_wind, voltage=12.6, eta=0.85):
    """
    Kutle ve ruzgara gore tahmini motor akimi (Amper).
    Drone hafifledikce bu deger duser.
    """
    from energy_model import hover_gucu, ileri_guc
    P_total = hover_gucu(mass_g / 1000.0) + ileri_guc(v_wind)
    return P_total / voltage
