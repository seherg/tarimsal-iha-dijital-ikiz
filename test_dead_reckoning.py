"""
Dead Reckoning Test Modülü
MAVLink kesintisi simüle edilerek DR'nin doğruluğu ölçülür.
Sloshing etkisi altında pozisyon sapması da test edilir.
"""
import time
import math
import pytest
from modules.dead_reckoning import DeadReckoning
from energy_model import sloshing_katsayisi

class TestDeadReckoning:

    def test_dr_hareketsiz(self):
        """Hareketsiz drone'da 2s sonra DR aktif, sapma olmamalı"""
        dr = DeadReckoning()
        dr.update(39.0, 35.0, 0.0, 0.0, 600.0)
        time.sleep(2.1)  # DR esigini gec
        lat, lon, alt, aktif = dr.estimate()
        # Hareketsiz: konum degismemeli
        assert abs(lat - 39.0) < 1e-5
        assert abs(lon - 35.0) < 1e-5
        # 2s sonra DR aktif olmali
        assert aktif == True

    def test_dr_kuzey_yonunde(self):
        """Kuzey yönünde uçan drone doğru konuma yaklaşmalı"""
        dr = DeadReckoning()
        # 5 m/s, kuzey (heading=0)
        dr.update(39.0, 35.0, 5.0, 0.0, 600.0)
        time.sleep(2.1)  # DR eşiğini geç
        lat, lon, alt, aktif = dr.estimate()
        # Kuzey = lat artmalı
        assert lat > 39.0, "DR kuzey yönünde çalışmıyor"
        assert aktif == True
        print(f"\n  DR Kuzey testi: Δlat = {(lat-39.0)*111320:.2f}m")

    def test_dr_dogu_yonunde(self):
        """Doğu yönünde uçan drone doğru konuma yaklaşmalı"""
        dr = DeadReckoning()
        # 5 m/s, doğu (heading=90)
        dr.update(39.0, 35.0, 5.0, 90.0, 600.0)
        time.sleep(2.1)
        lat, lon, alt, aktif = dr.estimate()
        assert lon > 35.0, "DR doğu yönünde çalışmıyor"
        assert aktif == True
        print(f"\n  DR Doğu testi: Δlon = {(lon-35.0)*111320*math.cos(math.radians(39)):.2f}m")

    def test_dr_2_saniye_dogruluk(self):
        """2 saniye kesintide pozisyon hatası 15m'den az olmalı"""
        dr = DeadReckoning()
        v_gs = 5.0  # m/s
        heading = 45.0  # kuzeydoğu
        dr.update(39.0, 35.0, v_gs, heading, 600.0)
        time.sleep(2.1)
        lat, lon, alt, aktif = dr.estimate()

        # Beklenen pozisyon
        ds = v_gs * 2.0
        beklenen_dlat = (ds * math.cos(math.radians(heading))) / 111320
        beklenen_dlon = (ds * math.sin(math.radians(heading))) / (111320 * math.cos(math.radians(39.0)))

        hata_m = math.sqrt(
            ((lat - (39.0 + beklenen_dlat)) * 111320)**2 +
            ((lon - (35.0 + beklenen_dlon)) * 111320)**2
        )
        assert hata_m < 15.0, f"DR pozisyon hatası çok büyük: {hata_m:.2f}m"
        print(f"\n  DR 2s doğruluk: Pozisyon hatası = {hata_m:.3f}m")

    def test_dr_aktif_olmadan_tahmin(self):
        """2 saniye geçmeden DR aktif olmamalı"""
        dr = DeadReckoning()
        dr.update(39.0, 35.0, 5.0, 0.0, 600.0)
        time.sleep(0.5)  # 0.5s bekle - eşik aşılmadı
        lat, lon, alt, aktif = dr.estimate()
        # DR eşiği (2s) geçilmediği için aktif=False olmalı
        # Ama bazı implementasyonlarda hep True döner - test uyarı verir
        assert aktif == False, "2 saniye geçmeden DR aktif olmamalı"
        print(f"\n  DR 0.5s sonrası aktif: {aktif}")


class TestSloshing:

    def test_tam_dolu_sloshing_dusuk(self):
        """Tam dolu tankta sloshing minimum olmalı"""
        k = sloshing_katsayisi(1.0, perdeli_tank=False)
        assert k < 0.01, f"Tam dolu tankta sloshing yüksek: {k}"

    def test_tam_bos_sloshing_sifir(self):
        """Boş tankta sloshing sıfır olmalı"""
        k = sloshing_katsayisi(0.0, perdeli_tank=False)
        assert k < 0.001, f"Boş tankta sloshing sıfır olmalı: {k}"

    def test_yari_dolu_maksimum(self):
        """Yarı dolu tankta sloshing maksimum olmalı"""
        k_yari = sloshing_katsayisi(0.5, perdeli_tank=False)
        k_dolu = sloshing_katsayisi(1.0, perdeli_tank=False)
        k_bos  = sloshing_katsayisi(0.0, perdeli_tank=False)
        assert k_yari > k_dolu
        assert k_yari > k_bos
        print(f"\n  Sloshing k değerleri: boş={k_bos:.4f}, yarı={k_yari:.4f}, dolu={k_dolu:.4f}")

    def test_perdeli_tank_daha_az_sloshing(self):
        """Perdeli tank sloshingı azaltmalı"""
        k_perdesiz = sloshing_katsayisi(0.5, perdeli_tank=False)
        k_perdeli  = sloshing_katsayisi(0.5, perdeli_tank=True)
        assert k_perdeli < k_perdesiz
        oran = k_perdesiz / k_perdeli
        print(f"\n  Perdeli tank sloshing azalma oranı: {oran:.1f}x")
        assert oran > 3.0, "Perdeli tank en az 3x daha az sloshing üretmeli"

    def test_sloshing_enerji_etkisi(self):
        """Sloshing PNR enerjisini artırmalı"""
        from energy_model import pnr_energy_required
        e_normal   = pnr_energy_required(500, 2000, 5.0,
                                          perdeli_tank=True,
                                          payload_g=500, max_payload_g=1000)
        e_sloshing = pnr_energy_required(500, 2000, 5.0,
                                          perdeli_tank=False,
                                          payload_g=500, max_payload_g=1000)
        assert e_sloshing > e_normal
        fark_pct = (e_sloshing - e_normal) / e_normal * 100
        print(f"\n  Sloshing enerji etkisi: %{fark_pct:.2f} artış")


class TestDiKeyRuzgar:

    def test_updraft_enerji_arttirir(self):
        """Updraft (yukarı rüzgar) enerji gereksinimini artırmalı"""
        from energy_model import pnr_energy_required
        e_sakin   = pnr_energy_required(500, 2000, 5.0, v_dikey_ms=0.0)
        e_updraft = pnr_energy_required(500, 2000, 5.0, v_dikey_ms=3.0)
        assert e_updraft > e_sakin
        print(f"\n  Updraft 3 m/s enerji artışı: {e_updraft - e_sakin:.4f} Wh")

    def test_downdraft_de_enerji_arttirir(self):
        """Downdraft de enerji artırmalı (abs değer alınıyor)"""
        from energy_model import pnr_energy_required
        e_sakin     = pnr_energy_required(500, 2000, 5.0, v_dikey_ms=0.0)
        e_downdraft = pnr_energy_required(500, 2000, 5.0, v_dikey_ms=-3.0)
        assert e_downdraft > e_sakin

    def test_dikey_ruzgar_sifirda_etki_yok(self):
        """Dikey rüzgar 0'da temel formülle aynı olmalı"""
        from energy_model import pnr_energy_required
        e_base  = pnr_energy_required(500, 2000, 5.0)
        e_dikey = pnr_energy_required(500, 2000, 5.0, v_dikey_ms=0.0)
        assert abs(e_base - e_dikey) < 1e-6


class TestReSimulation:

    def test_resim_yuksek_ruzgarda_tehlike(self):
        """Yüksek rüzgarda düşük bataryada re-sim tehlike vermeli."""
        from modules.re_simulation import re_simulate_pnr
        state = {'lat': 39.005, 'lon': 35.005, 'bat_pct': 15}
        home  = (39.0, 35.0)
        ok, margin, report = re_simulate_pnr(state, 15.0, home, 200)
        assert ok == False, "Yüksek rüzgar + düşük batarya tehlikeli olmalı"
        assert margin < 0

    def test_resim_iyi_kosullarda_guvenli(self):
        """İyi koşullarda (yakın mesafe, tam batarya) re-sim güvenli vermeli."""
        from modules.re_simulation import re_simulate_pnr
        state = {'lat': 39.001, 'lon': 35.001, 'bat_pct': 80}
        home  = (39.0, 35.0)
        ok, margin, report = re_simulate_pnr(state, 3.0, home, 10)
        assert ok == True, "Yakın mesafe + tam batarya güvenli olmalı"
        assert margin > 0

    def test_resim_rapor_formati(self):
        """Re-sim raporu liste döndürmeli ve boş olmamalı."""
        from modules.re_simulation import re_simulate_pnr
        state = {'lat': 39.002, 'lon': 35.002, 'bat_pct': 50}
        home  = (39.0, 35.0)
        ok, margin, report = re_simulate_pnr(state, 5.0, home, 60)
        assert isinstance(report, list)
        assert len(report) > 0


class TestWindModel:

    def test_sabit_profil_degerismez(self):
        """Sabit profil her zaman aynı değer döndürmeli."""
        from modules.wind_model import get_wind_speed
        assert get_wind_speed('sabit', 0)   == get_wind_speed('sabit', 100)
        assert get_wind_speed('sabit', 500) == get_wind_speed('sabit', 999)

    def test_basamakli_profil_dogru_zamanda_degisiyor(self):
        """Basamaklı profil t=100'de 12 m/s'ye çıkmalı."""
        from modules.wind_model import get_wind_speed
        v_once = get_wind_speed('basamakli', 50)
        v_sonra = get_wind_speed('basamakli', 150)
        assert v_once < v_sonra, "t=150'de rüzgar t=50'den fazla olmalı"

    def test_profil_negatif_olmaz(self):
        """Hiçbir profil negatif rüzgar hızı döndürmemeli."""
        from modules.wind_model import get_wind_speed
        for profil in ['sabit', 'sinusoidal', 'basamakli', 'turbulansli']:
            for t in range(0, 500, 50):
                assert get_wind_speed(profil, t) >= 0.0, \
                    f"{profil} profili t={t}'de negatif rüzgar döndürdü"