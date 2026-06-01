"""
Dijital Ikiz v2.0 - Canli Dashboard
Streamlit ile gercek zamanli telemetri izleme
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import yaml, os, time
from datetime import datetime

st.set_page_config(
    page_title="Dijital Ikiz v2.0",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS
st.markdown("""
<style>
.metric-card {
    background: #1F4E79; color: white;
    padding: 16px; border-radius: 10px;
    text-align: center; margin: 4px;
}
.metric-val { font-size: 28px; font-weight: bold; }
.metric-lbl { font-size: 12px; opacity: 0.8; }
.status-ok  { color: #1D9E75; font-weight: bold; }
.status-warn{ color: #D85A30; font-weight: bold; }
.status-crit{ color: #A32D2D; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Config
with open('config.yaml') as f:
    cfg = yaml.safe_load(f)

LOG = cfg['log']['dosya']

# ── SIDEBAR ──────────────────────────────────────────────────────

st.sidebar.title("🚁 Dijital İkiz v2.0")
st.sidebar.markdown("**Fırat Üniversitesi**  \nYazılım Mühendisliği")
st.sidebar.divider()

mod = st.sidebar.radio("Mod", ["📊 Canlı İzleme", "📁 Log Analizi", "🌬️ Rüzgar Senaryoları", "📈 Model Karşılaştırma"])

yenile = st.sidebar.slider("Yenileme (sn)", 1, 10, 2)
st.sidebar.divider()
st.sidebar.markdown(f"**Config:** `config.yaml`")
st.sidebar.markdown(f"Batarya: **{cfg['batarya']['kapasite_wh']} Wh**")
st.sidebar.markdown(f"PNR Marjı: **%{cfg['guvenik']['pnr_marji_pct']}**")
st.sidebar.markdown(f"Rüzgar: **{cfg['ruzgar']['baslangic_ms']} → {cfg['ruzgar']['olay_hizi_ms']} m/s**")

# ── LOG YUKLE ────────────────────────────────────────────────────
@st.cache_data(ttl=2)
def log_yukle(path):
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    if df.empty:
        return None
    df['sure_s'] = df['timestamp'] - df['timestamp'].iloc[0]
    return df

# ══════════════════════════════════════════════════════════════════
if mod == "📊 Canlı İzleme":
    st.title("📊 Canlı Telemetri İzleme")

    ph_metric = st.empty()
    ph_chart  = st.empty()
    ph_status = st.empty()

    while True:
        df = log_yukle(LOG)

        if df is None:
            st.warning("⚠️ Log dosyası bulunamadı. SITL çalışıyor mu?")
            time.sleep(yenile)
            st.rerun()

        son = df.iloc[-1]
        pnr_satirlar = df[df['pnr_tetiklendi'] == 1]
        resim_satirlar = df[df.get('re_sim_tetiklendi', pd.Series([0]*len(df))) == 1] if 're_sim_tetiklendi' in df.columns else pd.DataFrame()

        # ─ Metrikler
        with ph_metric.container():
            c1,c2,c3,c4,c5,c6 = st.columns(6)
            c1.metric("⏱️ Süre",     f"{son['sure_s']:.0f}s")
            c2.metric("🔋 Batarya",  f"%{son['bat_pct']:.0f}",
                      delta=f"{df['bat_pct'].diff().iloc[-1]:.1f}%" if len(df)>1 else None)
            c3.metric("📡 İrtifa",   f"{son['alt']:.1f}m")
            c4.metric("📍 Mesafe",   f"{son['distance_m']:.1f}m")
            c5.metric("⚡ E_kalan",  f"{son['E_kalan_wh']:.2f}Wh")
            c6.metric("🎯 E_pnr",    f"{son['E_pnr_wh']:.2f}Wh")

        # ─ Durum
        with ph_status.container():
            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                if not pnr_satirlar.empty:
                    st.error(f"🔴 RTH AKTİF — {pnr_satirlar['sure_s'].iloc[0]:.0f}s'de tetiklendi")
                elif son['E_kalan_wh'] < son['E_pnr_wh'] * 1.2:
                    st.warning("🟡 PNR EŞİĞİNE YAKLAŞIYOR")
                else:
                    st.success("🟢 GÖREV DEVAM EDİYOR")
            with sc2:
                if not resim_satirlar.empty:
                    st.info(f"🔄 Re-Simulation: {resim_satirlar['sure_s'].iloc[0]:.0f}s'de çalıştı")
                else:
                    st.info("🔄 Re-Simulation: Bekleniyor")
            with sc3:
                dr_var = 'dead_reckoning' in df.columns and df['dead_reckoning'].sum() > 0
                if dr_var:
                    st.warning(f"🧭 Dead Reckoning: {df['dead_reckoning'].sum()*0.1:.1f}s aktif")
                else:
                    st.success("📡 MAVLink: Bağlı")

        # ─ Grafikler
        with ph_chart.container():
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=[
                    'Batarya & Enerji Dengesi',
                    'Dinamik Kütle m(t)',
                    'Motor Akımı & Terminal Voltaj',
                    'PNR Karar Dengesi'
                ]
            )

            # Sol üst: Batarya + Enerji
            fig.add_trace(go.Scatter(x=df['sure_s'], y=df['bat_pct'],
                name='Batarya %', line=dict(color='#185FA5', width=2)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df['sure_s'], y=df['E_kalan_wh'],
                name='E_kalan', line=dict(color='#1D9E75', width=2, dash='dash'),
                yaxis='y3'), row=1, col=1)

            # Sağ üst: Kütle
            if 'mass_g' in df.columns:
                fig.add_trace(go.Scatter(x=df['sure_s'], y=df['mass_g'],
                    name='Toplam Kütle (g)', line=dict(color='#534AB7', width=2)), row=1, col=2)
            if 'payload_g' in df.columns:
                fig.add_trace(go.Scatter(x=df['sure_s'], y=df['payload_g'],
                    name='İlaç Yükü (g)', line=dict(color='#AFA9EC', width=1.5, dash='dot'),
                    fill='tozeroy', fillcolor='rgba(175,169,236,0.15)'), row=1, col=2)

            # Sol alt: Akım & Voltaj
            if 'est_current_A' in df.columns:
                fig.add_trace(go.Scatter(x=df['sure_s'], y=df['est_current_A'],
                    name='Akım (A)', line=dict(color='#D85A30', width=2)), row=2, col=1)
            if 'v_terminal' in df.columns:
                fig.add_trace(go.Scatter(x=df['sure_s'], y=df['v_terminal'],
                    name='Voltaj (V)', line=dict(color='#854F0B', width=1.5, dash='dash')), row=2, col=1)

            # Sağ alt: PNR dengesi
            fig.add_trace(go.Scatter(x=df['sure_s'], y=df['E_kalan_wh'],
                name='E_kalan', line=dict(color='#1D9E75', width=2.5),
                fill='tonexty', fillcolor='rgba(29,158,117,0.1)'), row=2, col=2)
            fig.add_trace(go.Scatter(x=df['sure_s'], y=df['E_pnr_wh'],
                name='E_pnr', line=dict(color='#A32D2D', width=2, dash='dot')), row=2, col=2)

            # PNR çizgisi
            if not pnr_satirlar.empty:
                pnr_x = pnr_satirlar['sure_s'].iloc[0]
                for r in [1,2]:
                    for c in [1,2]:
                        fig.add_vline(x=pnr_x, line_dash="dash",
                            line_color="#A32D2D", line_width=2, row=r, col=c)

            fig.update_layout(
                height=550, showlegend=True,
                font=dict(size=11),
                paper_bgcolor='white', plot_bgcolor='#FAFAFA',
                legend=dict(orientation='h', y=-0.12)
            )
            st.plotly_chart(fig, width="stretch")

        time.sleep(yenile)
        st.rerun()

# ══════════════════════════════════════════════════════════════════
elif mod == "📁 Log Analizi":
    st.title("📁 Uçuş Log Analizi")

    log_dosyalar = [f for f in os.listdir('logs') if f.endswith('.csv') and 'dt_log' in f]
    if not log_dosyalar:
        st.warning("logs/ klasöründe CSV bulunamadı.")
    else:
        secilen = st.selectbox("Log dosyası seç:", sorted(log_dosyalar, reverse=True))
        df = pd.read_csv(f'logs/{secilen}')
        df['sure_s'] = df['timestamp'] - df['timestamp'].iloc[0]

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Toplam Süre",    f"{df['sure_s'].max():.0f}s")
        c2.metric("Max İrtifa",     f"{df['alt'].max():.1f}m")
        c3.metric("Min Batarya",    f"%{df['bat_pct'].min():.0f}")
        c4.metric("Kayıt Sayısı",   f"{len(df)}")

        st.dataframe(df.tail(20), width="stretch")

# ══════════════════════════════════════════════════════════════════
elif mod == "🌬️ Rüzgar Senaryoları":
    st.title("🌬️ Dinamik Rüzgar Senaryoları")

    ruzgar_dosyalar = [f for f in os.listdir('logs') if f.startswith('wind_')]
    if not ruzgar_dosyalar:
        st.warning("Önce run_wind_scenarios.py çalıştır.")
    else:
        cols = st.columns(len(ruzgar_dosyalar))
        for col, dosya in zip(cols, sorted(ruzgar_dosyalar)):
            df = pd.read_csv(f'logs/{dosya}')
            profil = dosya.replace('wind_','').replace('.csv','')
            pnr_t = df[df['pnr']==1]['t'].values
            pnr_str = f"{pnr_t[0]:.0f}s" if len(pnr_t)>0 else "—"
            col.metric(profil, f"PNR: {pnr_str}",
                       f"Rz: {df['v_wind'].mean():.1f} m/s")

        # Tüm profiller birlikte
        fig = go.Figure()
        renkler = ['#185FA5','#1D9E75','#D85A30','#534AB7']
        for dosya, renk in zip(sorted(ruzgar_dosyalar), renkler):
            df = pd.read_csv(f'logs/{dosya}')
            profil = dosya.replace('wind_','').replace('.csv','')
            fig.add_trace(go.Scatter(x=df['t'], y=df['e_kalan'],
                name=f'{profil} — E_kalan', line=dict(color=renk, width=2)))
            fig.add_trace(go.Scatter(x=df['t'], y=df['e_pnr'],
                name=f'{profil} — E_pnr', line=dict(color=renk, width=1.5, dash='dot')))

        fig.update_layout(title='Enerji Dengesi — Tüm Rüzgar Profilleri',
            xaxis_title='Süre (s)', yaxis_title='Enerji (Wh)', height=450)
        st.plotly_chart(fig, width="stretch")

# ══════════════════════════════════════════════════════════════════
elif mod == "📈 Model Karşılaştırma":
    st.title("📈 Model Karşılaştırma — DT v2.0 vs Schacht [8]")

    csv_path = 'logs/ip6_istatistik.csv'
    if not os.path.exists(csv_path):
        st.warning("Önce ip6_istatistik.py çalıştır.")
    else:
        df = pd.read_csv(csv_path)
        st.dataframe(df, width="stretch")

        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(df, x='v_wind', y='erken_uyari',
                title='Erken Uyarı Kazanımı (s)',
                labels={'v_wind':'Rüzgar (m/s)', 'erken_uyari':'Saniye'},
                color='erken_uyari', color_continuous_scale='Blues')
            st.plotly_chart(fig, width="stretch")
        with c2:
            fig = px.bar(df, x='v_wind', y=['mae_soc','rmse_soc'],
                title='MAE & RMSE (SoC Farkı)',
                labels={'v_wind':'Rüzgar (m/s)', 'value':'Hata'},
                barmode='group')
            st.plotly_chart(fig, width="stretch")

        st.success(f"✅ Ortalama erken uyarı kazanımı: **{df['erken_uyari'].mean():.0f} saniye**")
        st.info(f"📊 MAE ortalaması: {df['mae_soc'].mean():.4f} | RMSE: {df['rmse_soc'].mean():.4f}")
