"""Página de Análise Temporal — séries e padrões sazonais."""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="Análise Temporal", layout="wide")

if "df_acidentes" not in st.session_state:
    st.warning("Carregue os dados na página inicial primeiro.")
    st.stop()

df = st.session_state["df_acidentes"]

st.markdown(
    """
    <div style="margin-bottom:1.5rem;">
        <h2>Análise Temporal e Sazonalidade</h2>
        <p style="color:var(--text-muted);">
            Tendências, padrões sazonais e correlações dos acidentes na malha concedida.
        </p>
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
        HEAT_GRADIENT,
        PURPLE,
        PURPLE_DEEP,
        TURNO_COLORS,
        apply_hover,
    )
except ImportError:
    st.error("Instale plotly: `pip install plotly`")
    st.stop()

theme = "plotly_dark"

# ─── Séries temporais ──────────────────────────────────────────────
st.markdown('<div class="section-title">Série Temporal Completa</div>', unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    granularidade = st.selectbox("Granularidade", ["Mensal", "Trimestral", "Anual"])
with c2:
    metric = st.selectbox("Métrica", ["Acidentes", "Óbitos", "Feridos", "Severidade"])

if "DATA" in df.columns:
    freq_map = {"Mensal": "M", "Trimestral": "Q", "Anual": "Y"}
    freq = freq_map.get(granularidade, "M")
    periodo = df["DATA"].dt.to_period(freq)

    if metric == "Óbitos":
        serie = df.groupby(periodo)["OBITOS"].sum()
    elif metric == "Feridos":
        serie = df.groupby(periodo)["FERIDOS"].sum()
    elif metric == "Severidade":
        severidade = df["OBITOS"] * 13 + df["FERIDOS"] * 5 + df["ILESOS"]
        serie = df.assign(SEV=severidade).groupby(periodo)["SEV"].sum()
    else:
        serie = df.groupby(periodo).size()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[str(p) for p in serie.index],
        y=serie.values,
        mode="lines+markers",
        line=dict(color=ACCENT, width=3),
        marker=dict(size=6),
        name=metric,
        hovertemplate="%{x}<br>%{y:,.0f}<extra></extra>",
    ))

    # Média móvel de 12 meses
    if len(serie) >= 12 and granularidade == "Mensal":
        ma = serie.rolling(12).mean()
        fig.add_trace(go.Scatter(
            x=[str(p) for p in ma.index],
            y=ma.values,
            mode="lines",
            name="Média móvel 12m",
            line=dict(color=BLUE_VIOLET, width=2, dash="dash"),
        ))

    fig.update_layout(
        template=theme,
        height=450,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="Período",
        yaxis_title=metric,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    apply_hover(fig, hovermode="x unified", spike_axis="x")
    st.plotly_chart(fig, use_container_width=True)

# ─── Heatmap calendar: dia da semana × hora ────────────────────────
st.markdown('<div class="section-title">Matriz de Acidentes: Dia da Semana × Hora</div>',
                unsafe_allow_html=True)

if "DIA_SEMANA" in df.columns and "HORA_DIA" in df.columns:
    ordem = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    trad = {"Monday": "Segunda", "Tuesday": "Terça", "Wednesday": "Quarta",
            "Thursday": "Quinta", "Friday": "Sexta", "Saturday": "Sábado", "Sunday": "Domingo"}

    matrix = pd.crosstab(df["DIA_SEMANA"], df["HORA_DIA"])
    for d in ordem:
        if d not in matrix.index:
            matrix.loc[d] = 0
    matrix = matrix.reindex([d for d in ordem if d in matrix.index])
    matrix.index = [trad.get(d, d) for d in matrix.index]

    fig = go.Figure(go.Heatmap(
        z=matrix.values,
        x=[str(h) for h in matrix.columns],
        y=list(matrix.index),
        colorscale=HEAT_GRADIENT,
        hovertemplate="Dia: %{y}<br>Hora: %{x}h<br>Acidentes: %{z:,.0f}<extra></extra>",
        colorbar=dict(title="Acidentes"),
    ))
    fig.update_layout(
        template=theme,
        height=420,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_title="Hora do dia",
        yaxis_title="Dia da semana",
    )
    apply_hover(fig, hovermode="closest")
    st.plotly_chart(fig, use_container_width=True)

# ─── Comparativo por dia/hora ──────────────────────────────────────
c1, c2 = st.columns(2)

with c1:
    st.markdown('<div class="section-title">Acidentes por Hora do Dia</div>', unsafe_allow_html=True)
    horas = df["HORA_DIA"].value_counts().sort_index()
    fig = px.bar(
        horas,
        labels={"value": "Acidentes", "index": "Hora"},
    )
    fig.update_layout(
        template=theme, height=300, margin=dict(l=20, r=20, t=20, b=20),
        showlegend=False,
    )
    fig.update_traces(
        marker_color=[PURPLE_DEEP if h in [6, 7, 8, 17, 18, 19] else ACCENT for h in horas.index]
    )
    apply_hover(fig, hovermode="closest", spike_axis="x")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.markdown('<div class="section-title">Evolução por Dia da Semana (média)</div>',
                unsafe_allow_html=True)
    dias_media = df.groupby(df["DATA"].dt.dayofweek).size()
    nomes = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    
    # Converter para média por dia (para comparar semanas com meses incompletos)
    dias_counts = df["DIA_SEMANA"].apply(lambda d: trad.get(d, d))
    dias_media = dias_counts.value_counts().reindex([trad[d] for d in ordem])
    dias_media = dias_media.fillna(0)

    fig = px.bar(
        dias_media,
        labels={"value": "Acidentes", "index": "Dia"},
    )
    fig.update_layout(
        template=theme, height=300, margin=dict(l=20, r=20, t=20, b=20),
        showlegend=False,
    )
    fig.update_traces(
        marker_color=[PURPLE if i >= 5 else ACCENT for i in range(7)]
    )
    apply_hover(fig, hovermode="closest", spike_axis="x")
    st.plotly_chart(fig, use_container_width=True)

# ─── Análise de turnos ─────────────────────────────────────────────
st.markdown('<div class="section-title">Análise por Turno</div>', unsafe_allow_html=True)

if "TURNO_DO_DIA" in df.columns:
    c1, c2 = st.columns(2)
    with c1:
        turno = df["TURNO_DO_DIA"].value_counts()
        fig = px.pie(
            turno, names=turno.index, values=turno.values,
            hole=0.4, title="Distribuição por Turno",
            color_discrete_sequence=GRADIENT_UV,
        )
        fig.update_layout(template=theme, height=320, margin=dict(l=20, r=20, t=50, b=20))
        fig.update_traces(
            marker=dict(colors=[TURNO_COLORS.get(t, ACCENT) for t in turno.index]),
            textposition="inside",
            texttemplate="<b>%{percent:.0%}</b>",
            textfont=dict(family=FONT_FAMILY, size=15),
        )
        apply_hover(fig, hovermode="closest")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("**Acidentes por turno e ano:**")
        try:
            if "ANO" in df.columns:
                tab = pd.crosstab(df["TURNO_DO_DIA"], df["ANO"])
                fig = go.Figure(data=[
                    go.Bar(name=str(ano), x=tab.index, y=tab[ano])
                    for ano in sorted(tab.columns)
                ])
                fig.update_layout(
                    template=theme,
                    height=320,
                    margin=dict(l=20, r=20, t=20, b=20),
                    barmode="stack",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.info("Dados insuficientes.")

# ─── Contagem mensal média histórica ───────────────────────────────
st.markdown('<div class="section-title">Sazonalidade Anual (média por mês)</div>',
                unsafe_allow_html=True)

if "MES" in df.columns:
    meses_padrao = [f"{m:02d}" for m in range(1, 13)]
    mes_counts = df["MES"].astype(int).value_counts().sort_index()
    nomes_meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

    fig = go.Figure(go.Bar(
        x=nomes_meses,
        y=mes_counts.reindex(range(1, 13)).fillna(0).values,
        marker=dict(
            color=mes_counts.reindex(range(1, 13)).fillna(0).values,
            colorscale="Blues_r",
        ),
        hovertemplate="%{x}: %{y:,.0f} acidentes<extra></extra>",
    ))
    fig.update_layout(
        template=theme,
        height=380,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_title="Mês",
        yaxis_title="Acidentes",
    )
    apply_hover(fig, hovermode="closest", spike_axis="x")
    st.plotly_chart(fig, use_container_width=True)