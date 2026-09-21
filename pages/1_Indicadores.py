"""Página de Indicadores BI — análise detalhada por filtros."""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.metrics import compute_kpis, compute_risk_score, compute_monthly_trend

st.set_page_config(page_title="Indicadores", layout="wide")

if "df_acidentes" not in st.session_state:
    st.warning("Carregue os dados na página inicial primeiro.")
    st.stop()

# Usa o dataset completo para que o filtro temporal desta página seja
# independente do filtro da página inicial (que congela no ano mais recente).
df = (
    st.session_state["df_completo"]
    if "df_completo" in st.session_state
    else st.session_state["df_acidentes"]
)

st.markdown(
    """
    <div style="margin-bottom:1.5rem;">
        <h2>Indicadores de Segurança Viária</h2>
        <p style="color:var(--text-muted);">Análise detalhada de acidentes, severidade e risco por rodovia.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    from utils.plot_style import (
        ACCENT,
        BLUE_VIOLET,
        FONT_FAMILY,
        GRADIENT_UV,
        PURPLE,
        PURPLE_DEEP,
        apply_hover,
    )
except ImportError:
    st.error("Instale plotly: `pip install plotly`")
    st.stop()

theme = "plotly_dark"

#  Filtro temporal (período de análise em anos)
anos_disponiveis = sorted(df["ANO"].dropna().astype(int).unique().tolist())
periodo = st.slider(
    "Período de análise (anos)",
    min_value=min(anos_disponiveis),
    max_value=max(anos_disponiveis),
    value=(min(anos_disponiveis), max(anos_disponiveis)),
)

#  Filtros avançados 
with st.expander("Filtros avançados", expanded=False):
    fcol1, fcol2, fcol3, fcol4 = st.columns(4)
    with fcol1:
        rodovias = ["Todas"] + sorted(df["RODOVIA"].dropna().unique().tolist())
        rodovia = st.selectbox("Rodovia", rodovias)
    with fcol2:
        classes = ["Todas"] + sorted(df["CLASSE"].dropna().unique().tolist())
        classe = st.selectbox("Classe de Acidente", classes)
    with fcol3:
        turnos = ["Todos"] + sorted(df["TURNO_DO_DIA"].dropna().unique().tolist())
        turno = st.selectbox("Turno", turnos)
    with fcol4:
        tipos = ["Todos"] + sorted(df["SUBCLASSE"].dropna().unique().tolist())
        tipo = st.selectbox("Subclasse", tipos)

df_view = df[df["ANO"].between(periodo[0], periodo[1])].copy()
if rodovia != "Todas":
    df_view = df_view[df_view["RODOVIA"] == rodovia]
if classe != "Todas":
    df_view = df_view[df_view["CLASSE"] == classe]
if turno != "Todos":
    df_view = df_view[df_view["TURNO_DO_DIA"] == turno]
if tipo != "Todos":
    df_view = df_view[df_view["SUBCLASSE"] == tipo]

if df_view.empty:
    st.warning("Sem registros no período e filtros selecionados.")
    st.stop()

# KPIs resumidos (consistentes com os filtros aplicados)
kpis = compute_kpis(df_view)

kc1, kc2, kc3, kc4, kc5 = st.columns(5)
with kc1:
    st.metric("Total Acidentes", f"{kpis['total_acidentes']:,.0f}")
with kc2:
    st.metric("Óbitos", f"{kpis['total_obitos']:,.0f}")
with kc3:
    st.metric("Feridos", f"{kpis['total_feridos']:,.0f}")
with kc4:
    st.metric("Ilesos", f"{kpis['total_ilesos']:,.0f}")
with kc5:
    st.metric("Taxa Fatalidade", f"{kpis['taxa_fatalidade']:.2f}%")

#  Ranking de rodovias por severidade 
st.markdown('<div class="section-title">Rodovias mais Perigosas (score de severidade)</div>',
                unsafe_allow_html=True)

risk = compute_risk_score(df_view)
if not risk.empty:
    grafico = risk.head(10).reset_index().sort_values("score_severidade", ascending=True)
    fig = go.Figure(go.Bar(
        x=grafico["score_severidade"],
        y=grafico["RODOVIA"],
        orientation="h",
        marker=dict(
            color=grafico["score_severidade"],
            colorscale=[[0, ACCENT], [1, PURPLE_DEEP]],
            line=dict(color="rgba(255,255,255,.2)", width=1),
        ),
        text=grafico["score_severidade"].round(0),
        textposition="auto",
        customdata=grafico[["total_acidentes", "obitos", "feridos"]],
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Acidentes: %{customdata[0]:,}<br>"
            "Óbitos: %{customdata[1]:,}<br>"
            "Feridos: %{customdata[2]:,}<br>"
            "Score: %{x:,.0f}<extra></extra>"
        ),
    ))
    fig.update_layout(
        template=theme,
        height=500,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_title="Score de Severidade (Óbitos×13 + Feridos×5 + Ilesos×1)",
    )
    apply_hover(fig, hovermode="closest", spike_axis="y")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sem dados suficientes.")

#  Top municípios e evolução 
c1, c2 = st.columns(2)

with c1:
    st.markdown('<div class="section-title">Top Municípios</div>', unsafe_allow_html=True)
    top_cidades = kpis["top_municipios"]
    if not top_cidades.empty:
        fig = px.bar(
            top_cidades,
            orientation="h",
            labels={"value": "Acidentes", "index": "Município"},
        )
        fig.update_layout(
            template=theme,
            height=420,
            margin=dict(l=20, r=20, t=20, b=20),
            yaxis={"categoryorder": "total ascending"},
            showlegend=False,
        )
        fig.update_traces(marker_color=ACCENT)
        apply_hover(fig, hovermode="closest", spike_axis="y")
        st.plotly_chart(fig, use_container_width=True)

with c2:
    st.markdown('<div class="section-title">Tendência Mensal</div>', unsafe_allow_html=True)
    monthly = compute_monthly_trend(df_view)
    if not monthly.empty:
        fig = make_subplots()
        fig.add_trace(go.Bar(
            x=monthly["mes_ano"], y=monthly["total_acidentes"],
            name="Acidentes", marker_color=ACCENT, opacity=.8,
        ))
        fig.add_trace(go.Scatter(
            x=monthly["mes_ano"], y=monthly["total_obitos"],
            name="Óbitos", mode="lines+markers",
            line=dict(color=PURPLE_DEEP, width=2.5),
        ))
        fig.update_layout(
            template=theme,
            height=420,
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis_title="Mês/Ano",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        apply_hover(fig, hovermode="x unified", spike_axis="x")
        st.plotly_chart(fig, use_container_width=True)

#  Concentração por dia da semana e região 
c1, c2 = st.columns(2)

with c1:
    st.markdown('<div class="section-title">Acidentes por Dia da Semana</div>', unsafe_allow_html=True)
    dias = kpis["acidentes_por_dia"]
    if not dias.empty:
        ordem = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        trad = {"Monday": "Seg", "Tuesday": "Ter", "Wednesday": "Qua",
                "Thursday": "Qui", "Friday": "Sex", "Saturday": "Sáb", "Sunday": "Dom"}
        dias = dias.reindex([d for d in ordem if d in dias.index])
        dias.index = [trad.get(d, d) for d in dias.index]
        fig = px.bar(dias, labels={"value": "Acidentes", "index": "Dia"})
        fig.update_layout(
            template=theme, height=300, margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False,
        )
        fig.update_traces(marker_color=[PURPLE if i >= 5 else ACCENT for i in range(len(dias))])
        apply_hover(fig, hovermode="closest", spike_axis="x")
        st.plotly_chart(fig, use_container_width=True)

with c2:
    st.markdown('<div class="section-title">Acidentes por Região Administrativa</div>',
                unsafe_allow_html=True)
    regioes = df_view["REGIAO_ADMINISTRATIVA"].value_counts()
    if not regioes.empty:
        fig = px.bar(
            regioes,
            orientation="h",
            labels={"value": "Acidentes", "index": "Região"},
            color_discrete_sequence=[PURPLE],
        )
        fig.update_layout(
            template=theme, height=300, margin=dict(l=20, r=20, t=20, b=20),
            yaxis={"categoryorder": "total ascending"}, showlegend=False,
        )
        apply_hover(fig, hovermode="closest", spike_axis="y")
        st.plotly_chart(fig, use_container_width=True)