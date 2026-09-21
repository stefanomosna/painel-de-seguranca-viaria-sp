"""Página de Dados Brutos — exploração, filtros e exportação."""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="Dados Brutos", layout="wide")

if "df_acidentes" not in st.session_state:
    st.warning("Carregue os dados na página inicial primeiro.")
    st.stop()

df = st.session_state["df_acidentes"]

st.markdown(
    """
    <div style="margin-bottom:1.5rem;">
        <h2>Dados Brutos e Exportação</h2>
        <p style="color:var(--text-muted);">
            Exploração tabular dos dados da ARTESP com filtros e exportação.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─── Filtros ───────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filtros de tabela")
    mostrar_colunas = st.multiselect(
        "Colunas para exibir",
        options=list(df.columns),
        default=[c for c in ["DATA", "CLASSE", "CONCESSIONARIA", "RODOVIA", "KM", "MUNICIPIO", "TURNO_DO_DIA", "OBITOS", "FERIDOS", "ILESOS"] if c in df.columns],
    )

# Registrar metadados
st.caption(f"**{len(df):,}** linhas × **{len(df.columns)}** colunas")

c1, c2, c3 = st.columns(3)
with c1:
    query_municipio = st.text_input("Filtrar por município")
with c2:
    if "MUNICIPIO" in df.columns:
        municipios = st.multiselect(
            "Selecionar municípios",
            options=sorted(df["MUNICIPIO"].dropna().unique().tolist()),
        )
with c3:
    if "CONCESSIONARIA" in df.columns:
        concessionarias = st.multiselect(
            "Concessionárias",
            options=sorted(df["CONCESSIONARIA"].dropna().unique().tolist()),
        )

df_view = df.copy()
if query_municipio:
    df_view = df_view[df_view["MUNICIPIO"].astype(str).str.contains(query_municipio, case=False, na=False)]
if "MUNICIPIO" in df.columns and municipios:
    df_view = df_view[df_view["MUNICIPIO"].isin(municipios)]
if "CONCESSIONARIA" in df.columns and concessionarias:
    df_view = df_view[df_view["CONCESSIONARIA"].isin(concessionarias)]

# ─── Exportação ────────────────────────────────────────────────────
st.markdown('<div class="section-title">Exportar Dados</div>', unsafe_allow_html=True)
ec1, ec2, ec3 = st.columns(3)
with ec1:
    if st.button("Baixar como CSV", use_container_width=True):
        csv = df_view.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button(
            label="Confirmar download CSV",
            data=csv,
            file_name="artesp_acidentes.csv",
            mime="text/csv",
        )
with ec2:
    if st.button("Baixar como Excel", use_container_width=True):
        import io
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_view.to_excel(writer, index=False, sheet_name="Acidentes")
            if "KM" in df_view.columns:
                resumo = df_view.groupby("RODOVIA").agg(
                    total_acidentes=("OBITOS", "size"),
                    obitos=("OBITOS", "sum"),
                    feridos=("FERIDOS", "sum"),
                ).reset_index()
                resumo.to_excel(writer, index=False, sheet_name="Resumo")
        st.download_button(
            label="Confirmar download Excel",
            data=buffer.getvalue(),
            file_name="artesp_acidentes.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
with ec3:
    n_rows = st.number_input("Linhas para exibir", min_value=10, max_value=200, value=50)

# ─── Tabela ────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Dados Filtrados</div>', unsafe_allow_html=True)

cols_show = [c for c in mostrar_colunas if c in df_view.columns] or list(df_view.columns)
st.dataframe(
    df_view[cols_show].head(n_rows),
    use_container_width=True,
    hide_index=True,
    height=450,
)

st.caption(f"Exibindo {min(n_rows, len(df_view))} de {len(df_view):,} registros filtrados.")

# ─── Análise descritiva ────────────────────────────────────────────
st.markdown('<div class="section-title">Estatística Descritiva</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Variáveis numéricas**")
    num_cols = df_view.select_dtypes(include="number").columns.tolist()
    if num_cols:
        st.dataframe(
            df_view[num_cols].describe().T,
            use_container_width=True,
        )
with c2:
    st.markdown("**Variáveis categóricas**")
    cat_cols = [
        c for c in df_view.columns
        if df_view[c].dtype == "object" and c not in ("MUNICIPIO", "RODOVIA")
    ][:4]
    for col in cat_cols:
        st.markdown(f"**{col}**")
        top = df_view[col].value_counts().head(5)
        st.dataframe(top, use_container_width=True)