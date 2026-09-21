"""
Painel de Segurança Viária. Rodovias do Estado de São Paulo
Dashboard BI/GIS baseado em dados abertos da ARTESP.

Executar: streamlit run Home.py
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from utils.data_loader import load_acidentes
from utils.metrics import compute_kpis
from utils.plot_style import (
    ACCENT,
    BLUE_VIOLET,
    FONT_FAMILY,
    GRADIENT_UV,
    TURNO_COLORS,
    apply_hover,
)

#  Configuração da página 
st.set_page_config(
    page_title="Segurança Viária SP | ARTESP",
    layout="wide",
    initial_sidebar_state="expanded",
)

#  Estilos CSS 
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter+Tight:wght@300;400;500;600;700;800&display=swap');

    :root {
        --bg: #0e1117;
        --bg-card: #161b22;
        --bg-card-hover: #1c2333;
        --border: #30363d;
        --text: #e6edf3;
        --text-muted: #8b949e;
        --accent: #58a6ff;
        --accent-2: #8957e5;
        --accent-3: #6f7cf6;
        --danger: #a855f7;
        --radius: 12px;
    }

    .stApp {
        background-color: var(--bg);
        font-family: 'Inter Tight', sans-serif;
        color: var(--text);
    }

    h1, h2, h3 {
        font-family: 'Inter Tight', sans-serif !important;
        font-weight: 700;
        color: var(--text) !important;
        letter-spacing: -0.02em;
    }

    .kpi-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 20px;
        height: 100%;
        transition: all .2s ease;
    }
    .kpi-card:hover {
        border-color: var(--accent);
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(88,166,255,.08);
    }
    .kpi-label {
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: .08em;
        color: var(--text-muted);
        margin-bottom: 8px;
    }
    .kpi-value {
        font-size: 32px;
        font-weight: 700;
        color: var(--text);
        line-height: 1.1;
    }
    .kpi-subtitle {
        font-size: 12px;
        color: var(--text-muted);
        margin-top: 6px;
    }
    .kpi-value.danger { color: var(--danger); }
    .kpi-value.accent { color: var(--accent-2); }
    .kpi-value.warn { color: var(--accent-3); }

    .section-title {
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        font-size: 1.25rem;
    }

    .info-banner {
        background: linear-gradient(135deg, rgba(88,166,255,.08), rgba(238,130,238,.05));
        border: 1px solid rgba(88,166,255,.3);
        border-radius: var(--radius);
        padding: 22px 26px 20px;
        margin: 16px 0 8px;
    }

    .stButton > button {
        background: var(--accent);
        color: #fff;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: .5rem 1.2rem;
        transition: all .2s;
    }
    .stButton > button:hover {
        background: #79c0ff;
        transform: translateY(-1px);
    }

    [data-testid="stSidebar"] {
        background: var(--bg-card);
        border-right: 1px solid var(--border);
    }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stMultiSelect label {
        color: var(--text-muted);
    }

    /* Streamlit widgets */
    .stMultiSelect [data-baseweb="tag"] {
        background-color: rgba(88,166,255,.15);
        border-radius: 6px;
    }
    [data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: 700;
    }

    footer {visibility: hidden;}
    header[data-testid="stHeader"] {background: transparent;}

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid var(--border);
        border-radius: var(--radius);
        overflow: hidden;
    }
</style>
""",
    unsafe_allow_html=True,
)

#  Sidebar com filtros globais
with st.sidebar:
    st.markdown(
        """
        <div style="padding: 4px 0 16px 0;">
            <div style="font-size:18px; font-weight:700;">Segurança Viária SP</div>
            <div style="font-size:12px; color:var(--text-muted);">
                Rodovias sob concessão no Estado de São Paulo
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    @st.cache_data(ttl=3600, show_spinner="Baixando dados da ARTESP...")
    def _carregar_dados():
        return load_acidentes(cache=True)

    df_acidentes = _carregar_dados()

    if df_acidentes.empty:
        st.error("Não foi possível carregar os dados. Verifique a conexão e tente novamente.")
        st.stop()

    anos_disponiveis = sorted(df_acidentes["ANO"].dropna().astype(int).unique().tolist())
    anos = st.multiselect(
        "Anos", anos_disponiveis, default=[max(anos_disponiveis)],
        help="Selecione os anos para análise",
    )

    concessionarias = ["Todas"] + sorted(df_acidentes["CONCESSIONARIA"].dropna().unique().tolist())
    conc = st.selectbox("Concessionária", concessionarias)

    if conc != "Todas":
        df_filtrado = df_acidentes[
            (df_acidentes["ANO"].isin(anos)) & (df_acidentes["CONCESSIONARIA"] == conc)
        ].copy()
    else:
        df_filtrado = df_acidentes[df_acidentes["ANO"].isin(anos)].copy()

    st.divider()
    st.caption(f"**{len(df_filtrado):,}** registros · fonte: dadosabertos.artesp.sp.gov.br")

# Gravar df filtrado no session_state para as páginas
st.session_state["df_acidentes"] = df_filtrado
st.session_state["df_completo"] = df_acidentes

# Header 
st.markdown(
    """
    <div class="info-banner">
        <div style="font-weight:700; font-size:3.3rem; line-height:1.2; letter-spacing:-.02em;">Painel de Segurança Viária.&nbsp;&nbsp;Rodovias Concedidas do Estado de São Paulo</div>
        <div style="color:var(--text-muted); font-size:.85rem; margin-top:12px;">
            Análise BI e GIS de acidentes, ocorrências e gestão da malha rodoviária.
            Dados abertos ARTESP · <code>dadosabertos.artesp.sp.gov.br</code>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

#  Página principal: visão geral
kpis = compute_kpis(df_filtrado)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Acidentes</div>
            <div class="kpi-value">{kpis['total_acidentes']:,.0f}</div>
            <div class="kpi-subtitle">no período selecionado</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Óbitos</div>
            <div class="kpi-value danger">{kpis['total_obitos']:,.0f}</div>
            <div class="kpi-subtitle">fatalidades registradas</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Feridos</div>
            <div class="kpi-value warn">{kpis['total_feridos']:,.0f}</div>
            <div class="kpi-subtitle">vítimas não fatais</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Taxa de Fatalidade</div>
            <div class="kpi-value accent">{kpis['taxa_fatalidade']:.2f}%</div>
            <div class="kpi-subtitle">óbitos / total de vítimas</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div style="margin-top:2rem;">
        <div class="section-title">Visão Operacional</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Gráficos de visão geral
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    theme = "plotly_dark"

    c1, c2 = st.columns([3, 2])

    with c1:
        # Evolução mensal
        serie_mensal = kpis["acidentes_por_mes"]
        if not serie_mensal.empty:
            fig = px.line(
                serie_mensal,
                title="Evolução Mensal de Acidentes",
                labels={"value": "Acidentes", "index": "Mês"},
            )
            fig.update_traces(
                line_color="#58a6ff",
                line_width=2.5,
                fill="tozeroy",
                fillcolor="rgba(88,166,255,.15)",
            )
            fig.update_layout(
                template=theme,
                height=360,
                margin=dict(l=20, r=20, t=60, b=20),
                xaxis_rangeslider_visible=False,
                hovermode="x unified",
            )
            apply_hover(fig, hovermode="x unified", spike_axis="x")
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        # Acidentes por tipo
        tipos = kpis["acidentes_por_tipo"]
        if not tipos.empty:
            fig = px.bar(
                tipos,
                orientation="h",
                title="Top Ocorrências",
                labels={"value": "Qtd.", "index": "Tipo de ocorrência"},
                color_discrete_sequence=["#58a6ff"],
            )
            fig.update_layout(
                template=theme,
                height=360,
                margin=dict(l=20, r=20, t=60, b=20),
                yaxis={"categoryorder": "total ascending"},
            )
            apply_hover(fig, hovermode="closest", spike_axis="y")
            st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)

    with c1:
        # Por concessionária
        conc_serie = kpis["acidentes_por_concessionaria"]
        if not conc_serie.empty:
            fig = px.pie(
                values=conc_serie.values,
                names=conc_serie.index,
                title="Acidentes por Concessionária",
                hole=0.45,
                color_discrete_sequence=GRADIENT_UV,
            )
            fig.update_layout(template=theme, height=360, margin=dict(l=20, r=20, t=60, b=20))
            fig.update_traces(
                textposition="inside",
                texttemplate="<b>%{percent:.0%}</b>",
                textfont=dict(family=FONT_FAMILY, size=15),
            )
            apply_hover(fig, hovermode="closest")
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        # Turnos
        turnos = kpis["acidentes_por_turno"]
        if not turnos.empty:
            fig = px.bar(
                turnos,
                title="Acidentes por Turno do Dia",
                labels={"value": "Acidentes", "index": "Turno"},
                color_discrete_sequence=GRADIENT_UV,
            )
            fig.update_layout(
                template=theme,
                height=360,
                margin=dict(l=20, r=20, t=60, b=20),
                showlegend=False,
            )
            fig.update_traces(
                marker_color=[
                    TURNO_COLORS.get(t, ACCENT) for t in turnos.index if isinstance(t, str)
                ] or ACCENT
            )
            apply_hover(fig, hovermode="closest", spike_axis="x")
            st.plotly_chart(fig, use_container_width=True)

except ImportError:
    st.warning("Instale `plotly` para visualizar os gráficos")

st.markdown(
    """
    <div style="display:flex; justify-content:space-between; align-items:center;
                margin-top:3rem; padding-top:1rem; border-top:1px solid var(--border);">
        <div style="color:var(--text-muted); font-size:.8rem;">
            Projeto demonstrativo · Análise de Dados BI/GIS
        </div>
        <div style="color:var(--text-muted); font-size:.8rem;">
            Dados: Portal de Dados Abertos da ARTESP
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)