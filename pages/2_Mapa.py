"""Página de Mapa — análise GIS interativa."""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="Mapa", layout="wide")

if "df_acidentes" not in st.session_state:
    st.warning("Carregue os dados na página inicial primeiro.")
    st.stop()

df = st.session_state["df_acidentes"]

from utils.plot_style import ACCENT, BLUE_VIOLET, PURPLE, PURPLE_DEEP

import folium
from streamlit_folium import st_folium

st.markdown(
    """
    <div style="margin-bottom:1.5rem;">
        <h2>Análise Geoespacial de Acidentes</h2>
        <p style="color:var(--text-muted);">
            Visualização dos registros georreferenciados na malha rodoviária.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─── Filtros 
with st.sidebar:
    st.sidebar.header("Filtros do Mapa")

    tipo_mapa = st.radio(
        "Tipo de camada de calor",
        ["Marcadores", "Heatmap de severidade"],
        help="Marcadores: pontos individuais. Heatmap: densidade ponderada por vítimas.",
    )

    categorias = ["Todos"] + sorted(df["CLASSE"].dropna().unique().tolist()) if "CLASSE" in df.columns else ["Todos"]
    tipo_ocorrencia = st.selectbox("Tipo de ocorrência", categorias)

    if "CLASSE" in df.columns and tipo_ocorrencia != "Todos":
        df_map = df[df["CLASSE"] == tipo_ocorrencia]
    else:
        df_map = df

    max_acidentes = st.slider(
        "Máximo de pontos no mapa",
        min_value=100, max_value=min(len(df_map), 5000),
        value=min(len(df_map), 2000), step=100,
        help="Limita a quantidade de pontos para performance.",
    )

# ─── Preparar dados geoespaciais 
@st.cache_data(ttl=3600)
def preparar_pontos(df_in: pd.DataFrame, limit: int) -> pd.DataFrame:
    """Prepara pontos com coordenadas válidas a partir do dataset."""
    if df_in.empty:
        return pd.DataFrame()

    resultado = df_in.copy().reset_index(drop=True)

    # Manter apenas registros com coordenadas válidas
    if "LATITUDE" in resultado.columns and "LONGITUDE" in resultado.columns:
        mask = (
            resultado["LATITUDE"].notna()
            & resultado["LONGITUDE"].notna()
            & (resultado["LATITUDE"] != 0)
            & (resultado["LONGITUDE"] != 0)
            & resultado["LATITUDE"].between(-30, -18)
            & resultado["LONGITUDE"].between(-55, -43)
        )
        resultado = resultado[mask]

    if len(resultado) > limit:
        # Amostra estratificada: preservar todos os óbitos
        has_obitos = resultado["OBITOS"] > 0
        n_fat = has_obitos.sum()
        n_restante = limit - n_fat
        if n_restante > 0:
            sample_rest = resultado[~has_obitos].sample(
                n=min(n_restante, (~has_obitos).sum()), random_state=42
            )
            resultado = pd.concat([resultado[has_obitos], sample_rest])
        else:
            resultado = resultado[has_obitos]

    return resultado.reset_index(drop=True)


df_pontos = preparar_pontos(df_map, max_acidentes)

# ─── Construir mapa 
BASE_MAP = folium.Map(
    location=[-23.0, -48.5],
    zoom_start=7,
    tiles=None,
    prefer_canvas=True,
    control_scale=True,
)

# Basemap escuro (ESRI Dark Gray Canvas)
folium.TileLayer(
    tiles="https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
    name="Dark (ESRI)",
    attr="Esri, HERE, Garmin, © OpenStreetMap contributors",
).add_to(BASE_MAP)

folium.TileLayer("OpenStreetMap", name="Light").add_to(BASE_MAP)

# Tentar carregar geometria das rodovias se disponível
try:
    from utils.geo_utils import load_processed_geojson

    gdf_rodovias = load_processed_geojson("malha_rodoviaria")
    if gdf_rodovias is not None and not gdf_rodovias.empty:
        rodovia_group = folium.FeatureGroup(name="Malha Rodoviária", show=True)
        tooltip_fields = [c for c in ["RODOVIA", "CONCESSIONARIA"] if c in gdf_rodovias.columns]
        tooltip_aliases = [
            "Rodovia" if c == "RODOVIA" else "Concessionária" for c in tooltip_fields
        ]
        folium.GeoJson(
            gdf_rodovias,
            name="Malha Rodoviária",
            style_function=lambda x: {
                "color": ACCENT,
                "weight": 2,
                "opacity": 0.7,
            },
            highlight_function=lambda x: {
                "color": "#79c0ff",
                "weight": 4,
                "opacity": 1,
                "fillOpacity": 0.15,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=tooltip_fields or ["RODOVIA"],
                aliases=tooltip_aliases or ["Rodovia"],
            ),
        ).add_to(rodovia_group)
        rodovia_group.add_to(BASE_MAP)
except Exception:
    pass

# Camada de pontos
pontos_group = folium.FeatureGroup(name="Acidentes", show=True)

if not df_pontos.empty:
    try:
        from folium.plugins import HeatMap

        if tipo_mapa == "Heatmap de severidade":
            # Heatmap usando coordenadas reais, ponderado por severidade
            flagged = df_pontos[["LATITUDE", "LONGITUDE", "OBITOS", "FERIDOS", "ILESOS"]].dropna()
            flagged = flagged[
                (flagged["LATITUDE"] != 0) & (flagged["LONGITUDE"] != 0)
            ]
            if not flagged.empty:
                n = min(len(flagged), 3000)
                amostra = flagged.sample(n, random_state=42)
                heat_data = [
                    [
                        row["LATITUDE"],
                        row["LONGITUDE"],
                        max(float(row["OBITOS"] * 13 + row["FERIDOS"] * 5 + row["ILESOS"]), 1),
                    ]
                    for _, row in amostra.iterrows()
                ]
                heat = HeatMap(
                    heat_data,
                    radius=12, blur=10, max_zoom=8, min_opacity=.3,
                    gradient={.2: ACCENT, .4: BLUE_VIOLET, .6: PURPLE, .8: PURPLE_DEEP, 1: PURPLE_DEEP},
                )
                heat.add_to(pontos_group)
            else:
                st.info("Sem coordenadas válidas para o heatmap no recorte atual.")
        else:
            # Marcadores coloridos por severidade em coordenadas reais
            n = min(len(df_pontos), 1500)
            amostra = df_pontos.head(n)
            for _, row in amostra.iterrows():
                try:
                    lat, lon = float(row["LATITUDE"]), float(row["LONGITUDE"])
                except (TypeError, ValueError):
                    continue
                peso = int(row["OBITOS"] * 13 + row["FERIDOS"] * 5 + row["ILESOS"])
                cor = ACCENT if peso <= 5 else BLUE_VIOLET if peso <= 30 else PURPLE_DEEP
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=3 if peso <= 5 else 5 if peso <= 30 else 7,
                    color=cor,
                    fill=True,
                    fill_opacity=.7,
                    tooltip=f"<b>{row.get('RODOVIA','')}</b> km {row.get('KM','')} · {row.get('MUNICIPIO','')}",
                    popup=folium.Popup(
                        f"<b>{row.get('RODOVIA','')}</b> km {row.get('KM','')} "
                        f"· {row.get('MUNICIPIO','')}<br>"
                        f"Óbitos: {row.get('OBITOS',0)} · Feridos: {row.get('FERIDOS',0)} · Ilesos: {row.get('ILESOS',0)}",
                        max_width=300,
                    ),
                ).add_to(pontos_group)
    except ImportError as e:
        st.warning(f"Instale `folium` e `streamlit-folium`: `{e}`")

pontos_group.add_to(BASE_MAP)

folium.LayerControl(collapsed=False).add_to(BASE_MAP)
folium.plugins.Fullscreen(position="topright").add_to(BASE_MAP)

# Renderizar
selected = st_folium(
    BASE_MAP,
    key="mapa_artesp",
    height=560,
    use_container_width=True,
    returned_objects=["last_object_clicked", "last_object_clicked_popup"],
)

# ─── Painel de informações 
st.markdown('<div class="section-title">Informações</div>', unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Pontos no mapa", f"{len(df_pontos):,}")
with c2:
    st.metric("Municípios abrangidos", f"{df_pontos['MUNICIPIO'].nunique() if 'MUNICIPIO' in df_pontos else 0:,}")
with c3:
    st.metric("Rodovias", f"{df_pontos['RODOVIA'].nunique() if 'RODOVIA' in df_pontos else 0:,}")

with st.expander("Sobre a metodologia GIS", expanded=False):
    st.markdown(
        """
        **Fluxo geoespacial (equivalente ao QGIS/ArcGIS):**

        1. **Download** da malha rodoviária (KMZ) do portal de dados abertos
        2. **Conversão** KMZ → GeoJSON via GeoPandas (WGS84 / EPSG:4326)
        3. **Geocodificação** dos acidentes por rodovia + KM
        4. **Análise espacial** (buffer, junction de geometrias)
        5. **Visualização** em mapa Leaflet via Folium

        **Ferramentas Google-equivalente:**
        - `geopandas` → processamento vetorial
        - `folium`/`leaflet` → visualização web
        - `shapely` → operações espaciais (buffers, interseções)
        - PostGIS → análise espacial em banco de dados
        """
    )

# ─── Tabela resumida 
st.markdown('<div class="section-title">Amostra dos pontos</div>', unsafe_allow_html=True)
cols_show = [c for c in ["DATA", "RODOVIA", "KM", "MUNICIPIO", "CLASSE", "TURNO_DO_DIA", "OBITOS", "FERIDOS", "ILESOS"] if c in df_pontos.columns]
if cols_show:
    st.dataframe(df_pontos[cols_show].head(100), use_container_width=True, hide_index=True)