"""
Hata Toleransli Haberlesme - Dead Reckoning Modulu.
MAVLink verisi 2 saniye gelmezse kinematik konum tahmini yapar.
CPS guvenirligi icin kritik fallback mekanizmasi (Steindl vd. 2024).
"""

import time
import math

TIMEOUT = 2.0   # Saniye - veri kesintisi esigi

class DeadReckoning:
    def __init__(self):
        self.last_lat     = None
        self.last_lon     = None
        self.last_gs      = 0.0
        self.last_heading = 0.0
        self.last_alt     = 584.0
        self.last_seen    = time.time()
        self.active       = False
        self.dr_count     = 0

    def update(self, lat, lon, gs, heading, alt):
        """Gercek veri gelince kaydet, DR'yi durdur."""
        self.last_lat     = lat
        self.last_lon     = lon
        self.last_gs      = gs
        self.last_heading = heading
        self.last_alt     = alt
        self.last_seen    = time.time()
        self.active       = False

    def estimate(self):
        """
        Son bilinen hiz ve yon ile konum tahmin et.
        ds = v * dt  (Newton birinci hareket denklemi)
        Donus: (lat, lon, alt, dr_aktif_mi)
        """
        elapsed = time.time() - self.last_seen

        if elapsed < TIMEOUT or self.last_lat is None:
            return self.last_lat, self.last_lon, self.last_alt, False

        self.active    = True
        self.dr_count += 1
        ds   = self.last_gs * elapsed
        head = math.radians(self.last_heading)
        dlat = (ds * math.cos(head)) / 111320.0
        dlon = (ds * math.sin(head)) / (
            111320.0 * math.cos(math.radians(self.last_lat)))

        return (
            self.last_lat + dlat,
            self.last_lon + dlon,
            self.last_alt,
            True
        )
