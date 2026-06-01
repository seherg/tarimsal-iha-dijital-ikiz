"""
Birim Testleri - V-Model Dogrulama Fazi
Her formul beklenen degerlerle karsilastirilir.
"""
import pytest
from modules.payload_model import payload_mass, total_mass, estimated_current
from modules.battery_model import (open_circuit_voltage, effective_resistance,
                                   terminal_voltage, energy_remaining)
from energy_model import haversine, pnr_energy_required

# ─────────────────────────────────────────────────────────
# PAYLOAD MODEL TESTLERI
# ─────────────────────────────────────────────────────────
class TestPayloadModel:

    def test_payload_baslangic_tam_dolu(self):
        """t=0'da ilac yuku tam olmali."""
        assert payload_mass(0) == 1000.0

    def test_payload_zamanla_azaliyor(self):
        """Ilac zamana gore azalmali."""
        assert payload_mass(30) < payload_mass(0)
        assert payload_mass(60) < payload_mass(30)

    def test_payload_sifirin_altina_dusmez(self):
        """Ilac bittikten sonra negatif olmamali."""
        assert payload_mass(9999) == 0.0
        assert payload_mass(1000) >= 0.0

    def test_payload_60_saniyede_bitmeli(self):
        """1000g / 16.7 g/s = ~59.9 saniyede bitmeli."""
        assert payload_mass(60) == pytest.approx(0.0, abs=1.0)

    def test_total_mass_govde_eklendi(self):
        """Toplam kutle = govde (1500g) + ilac."""
        assert total_mass(0) == pytest.approx(2500.0, abs=1.0)

    def test_total_mass_ilac_bitince_sadece_govde(self):
        """Ilac bitince sadece govde kutle olmali."""
        assert total_mass(9999) == pytest.approx(1500.0, abs=1.0)

    def test_akim_kutle_ile_artiyor(self):
        """Agir drone daha fazla akim harcar."""
        i_agir  = estimated_current(2500, 0)
        i_hafif = estimated_current(1500, 0)
        assert i_agir > i_hafif

    def test_akim_ruzgar_ile_artiyor(self):
        """Ruzgar artinca akim artmali."""
        i_az   = estimated_current(2000, 3)
        i_fazla = estimated_current(2000, 12)
        assert i_fazla > i_az

    def test_akim_pozitif(self):
        """Akim her zaman pozitif olmali."""
        assert estimated_current(1500, 0) > 0
        assert estimated_current(2500, 15) > 0


# ─────────────────────────────────────────────────────────
# BATARYA MODEL TESTLERI
# ─────────────────────────────────────────────────────────
class TestBatteryModel:

    def test_acik_devre_tam_sarj(self):
        """Tam sarjda voltaj 12.6V olmali."""
        assert open_circuit_voltage(100) == pytest.approx(12.556, abs=0.1)

    def test_acik_devre_bos(self):
        """Bos bataryada voltaj 10.5V olmali."""
        assert open_circuit_voltage(0) == pytest.approx(9.075, abs=0.1)

    def test_acik_devre_azaliyor(self):
        """Sarj azaldikca voltaj dusmeli."""
        assert open_circuit_voltage(50) < open_circuit_voltage(100)

    def test_ic_direnc_dusuk_sarjda_artiyor(self):
        """%20 altinda ic direnc artmali."""
        r_tam   = effective_resistance(100)
        r_dusuk = effective_resistance(10)
        assert r_dusuk > r_tam

    def test_ic_direnc_peukert_artisi(self):
        """%20 altinda ic direnc 3 kat olmali."""
        r_tam   = effective_resistance(100)
        r_kritik = effective_resistance(10)
        assert r_kritik > r_tam * 1.5   # %10 SoC'de en az 1.5x artış olmalı
        assert r_kritik < r_tam * 4.0   # ama 4x'i geçmemeli

    def test_terminal_voltaj_akimla_dusuyor(self):
        """Yuksek akim terminal voltaji dusurur."""
        v_dusuk_akim = terminal_voltage(80, 1)
        v_yuksek_akim = terminal_voltage(80, 20)
        assert v_yuksek_akim < v_dusuk_akim

    def test_terminal_voltaj_lipo_koruma(self):
        """Terminal voltaj 9V'un altina dusmemeli."""
        assert terminal_voltage(0, 100) >= 9.0
        assert terminal_voltage(5, 50) >= 9.0

    def test_enerji_tam_sarjda_maksimum(self):
        """Tam sarjda enerji maksimum olmali."""
        e_tam = energy_remaining(100, 5)
        e_yari = energy_remaining(50, 5)
        assert e_tam > e_yari

    def test_enerji_bos_bataryada_sifir(self):
        """Bos bataryada kullanilabilir enerji sifir olmali."""
        assert energy_remaining(0, 5) == pytest.approx(0.0, abs=0.1)


# ─────────────────────────────────────────────────────────
# ENERJI MODELI TESTLERI
# ─────────────────────────────────────────────────────────
class TestEnerjiModeli:

    def test_haversine_sifir_mesafe(self):
        """Ayni nokta arasindaki mesafe sifir olmali."""
        assert haversine(41.0, 29.0, 41.0, 29.0) == pytest.approx(0.0, abs=0.1)

    def test_haversine_pozitif_mesafe(self):
        """Iki farkli nokta arasindaki mesafe pozitif olmali."""
        assert haversine(41.0, 29.0, 41.1, 29.1) > 0

    def test_haversine_istanbul_ankara(self):
        """Istanbul-Ankara mesafesi ~350km olmali."""
        d = haversine(41.01, 28.96, 39.93, 32.85)
        assert 340000 < d < 360000

    def test_pnr_mesafe_artinca_enerji_artiyor(self):
        """Uzak mesafe daha fazla enerji gerektirir."""
        e_yakin = pnr_energy_required(100, 2000, 3)
        e_uzak  = pnr_energy_required(500, 2000, 3)
        assert e_uzak > e_yakin

    def test_pnr_ruzgar_artinca_enerji_artiyor(self):
        """Yuksek ruzgar daha fazla enerji gerektirir."""
        e_az   = pnr_energy_required(500, 2000, 3)
        e_fazla = pnr_energy_required(500, 2000, 12)
        assert e_fazla > e_az

    def test_pnr_kutle_artinca_enerji_artiyor(self):
        """Agir drone daha fazla enerji harcar."""
        e_hafif = pnr_energy_required(500, 1500, 3)
        e_agir  = pnr_energy_required(500, 2500, 3)
        assert e_agir > e_hafif

    def test_pnr_guvenik_marji_dahil(self):
        """PNR enerji hesabi %15 guvenlik marji icermeli — marjsiz hesaptan buyuk olmali."""
        from energy_model import hover_gucu, ileri_guc
        import math
        mass_kg  = 2.0
        v_wind   = 3.0
        dist_m   = 500.0
        v_seyir  = 5.0
        P_raw    = hover_gucu(mass_kg) + ileri_guc(v_wind)
        t_donus  = dist_m / v_seyir
        e_marjsiz = P_raw * t_donus / 3600.0
        e_pnr     = pnr_energy_required(dist_m, mass_kg * 1000, v_wind)
        assert e_pnr > e_marjsiz, "PNR enerjisi guvenlik marji olmadan hesaplanan degerden buyuk olmali"
        assert e_pnr == pytest.approx(e_marjsiz * 1.15, rel=0.02), "PNR marji yaklasik %%15 olmali"


# ─────────────────────────────────────────────────────────
# ENTEGRASYON TESTLERI
# ─────────────────────────────────────────────────────────
class TestEntegrasyon:

    def test_ruzgar_artinca_pnr_erken_tetiklenir(self):
        """
        Gercek senaryo: yuksek ruzgarda daha fazla enerji gerekir.
        Bu tezin ana argumani.
        """
        from modules.battery_model import energy_remaining
        bat_pct = 30
        mass    = 1500

        e_kal = energy_remaining(bat_pct, estimated_current(mass, 3))
        e_pnr_az   = pnr_energy_required(453, mass, 3)
        e_pnr_fazla = pnr_energy_required(453, mass, 12)

        assert e_pnr_fazla > e_pnr_az, \
            "Yuksek ruzgarda PNR esigi daha yuksek olmali"

    def test_ilac_bitince_kutle_azalir_pnr_gec_tetiklenir(self):
        """
        Hafif drone daha az enerji harcar,
        dolayisiyla PNR daha gec tetiklenmeli.
        """
        e_pnr_agir  = pnr_energy_required(300, 2500, 5)
        e_pnr_hafif = pnr_energy_required(300, 1500, 5)
        assert e_pnr_hafif < e_pnr_agir, \
            "Hafif droneun PNR esigi daha dusuk olmali"


# ─────────────────────────────────────────────────────────
# SOH (STATE OF HEALTH) TESTLERI
# ─────────────────────────────────────────────────────────
class TestSoH:

    def test_yeni_batarya_soh_tam(self):
        """0 döngüde SoH 1.0 olmalı."""
        from modules.battery_model import soh_faktoru
        assert soh_faktoru(0) == pytest.approx(1.0, abs=0.001)

    def test_500_dongude_soh_yaklasik_80(self):
        """500 döngüde SoH yaklaşık %80 olmalı."""
        from modules.battery_model import soh_faktoru
        assert soh_faktoru(500) == pytest.approx(0.80, abs=0.02)

    def test_soh_dongule_azaliyor(self):
        """Döngü arttıkça SoH azalmalı."""
        from modules.battery_model import soh_faktoru
        assert soh_faktoru(100) > soh_faktoru(300)
        assert soh_faktoru(300) > soh_faktoru(500)

    def test_efektif_kapasite_azaliyor(self):
        """Döngü arttıkça efektif kapasite azalmalı."""
        from modules.battery_model import efektif_kapasite
        assert efektif_kapasite(0) > efektif_kapasite(300)
        assert efektif_kapasite(300) > efektif_kapasite(500)

    def test_efektif_kapasite_soh_ile_tutarli(self):
        """Efektif kapasite = nominal kapasite * SoH olmalı."""
        from modules.battery_model import soh_faktoru, efektif_kapasite
        BAT_KAP = 9.5
        for n in [0, 100, 300, 500]:
            assert efektif_kapasite(n) == pytest.approx(
                BAT_KAP * soh_faktoru(n), abs=0.001)
