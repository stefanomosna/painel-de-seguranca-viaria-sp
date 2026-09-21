"""
Módulo de utilidades geoespaciais.
Conversão KMZ → GeoJSON e operações espaciais.
"""
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import shape

DATA_DIR = Path(__file__).parent.parent / "data"


def kmz_to_geodataframe(kmz_path: str | Path) -> gpd.GeoDataFrame:
    """
    Converte um arquivo KMZ para GeoDataFrame.
    
    Parâmetros
    ----------
    kmz_path : str ou Path
        Caminho para o arquivo .kmz
    
    Retorna
    -------
    gpd.GeoDataFrame
    """
    kmz_path = Path(kmz_path)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(kmz_path, "r") as z:
            z.extractall(tmpdir)
        
        kml_files = list(Path(tmpdir).rglob("*.kml"))
        if not kml_files:
            raise ValueError(f"Nenhum arquivo KML encontrado em {kmz_path}")
        
        gdf = gpd.read_file(str(kml_files[0]))
    
    # Garantir CRS WGS84
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")
    
    return gdf


def download_and_convert_kmz(url: str, output_name: str) -> gpd.GeoDataFrame:
    """
    Baixa um KMZ de uma URL e converte para GeoDataFrame.
    Salva GeoJSON processado em data/processed/.
    
    Parâmetros
    ----------
    url : str
        URL do arquivo KMZ
    output_name : str
        Nome base para o arquivo de saída (sem extensão)
    
    Retorna
    -------
    gpd.GeoDataFrame
    """
    processed_dir = DATA_DIR / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    geojson_path = processed_dir / f"{output_name}.geojson"
    
    # Verificar cache
    if geojson_path.exists():
        return gpd.read_file(geojson_path)
    
    # Baixar KMZ
    resp = requests.get(url, timeout=60, stream=True)
    resp.raise_for_status()
    
    kmz_path = DATA_DIR / "raw" / f"{output_name}.kmz"
    kmz_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(kmz_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    
    # Converter
    gdf = kmz_to_geodataframe(kmz_path)
    
    # Salvar GeoJSON
    gdf.to_file(geojson_path, driver="GeoJSON")
    
    return gdf


def load_processed_geojson(name: str) -> gpd.GeoDataFrame | None:
    """Carrega um GeoJSON já processado do cache."""
    geojson_path = DATA_DIR / "processed" / f"{name}.geojson"
    if geojson_path.exists():
        return gpd.read_file(geojson_path)
    return None


def create_rodovia_segments(
    gdf_rodovias: gpd.GeoDataFrame,
    gdf_acidentes: pd.DataFrame,
) -> gpd.GeoDataFrame:
    """
    Cruza acidentes com geometria das rodovias para atribuir
    coordenadas geográficas aos registros de acidentes.
    
    Parâmetros
    ----------
    gdf_rodovias : GeoDataFrame com geometria das rodovias
    gdf_acidentes : DataFrame com coluna RODOVIA e KM
    
    Retorna
    -------
    GeoDataFrame com acidentes georreferenciados
    """
    if gdf_rodovias.empty or gdf_acidentes.empty:
        return gpd.GeoDataFrame()
    
    # Merge por nome da rodovia
    merged = gdf_acidentes.copy()
    
    # Tentar fazer correspondência entre nomes
    rodovia_map = {}
    for _, row in gdf_rodovias.iterrows():
        nome = str(row.get("Name", row.get("name", ""))).strip()
        rodovia_map[nome] = row.geometry
    
    # Atribuir geometria baseado na rodovia mais provável
    geometrias = []
    for _, acidente in merged.iterrows():
        rodo = str(acidente.get("RODOVIA", "")).strip()
        geom = None
        
        # Busca exata
        if rodo in rodovia_map:
            geom = rodovia_map[rodo]
        else:
            # Busca parcial
            for nome, g in rodovia_map.items():
                if rodo.lower() in nome.lower() or nome.lower() in rodo.lower():
                    geom = g
                    break
        
        geometrias.append(geom)
    
    merged["geometry"] = geometrias
    
    return gpd.GeoDataFrame(merged, geometry="geometry", crs="EPSG:4326")


def generate_heatmap_data(
    gdf: gpd.GeoDataFrame,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
) -> list[list[float, float, float]]:
    """
    Gera dados formatados para heatmap do Folium.
    
    Retorna lista de [lat, lon, weight]
    """
    if gdf.empty:
        return []
    
    heat_data = []
    for _, row in gdf.iterrows():
        try:
            if row.geometry is not None and not row.geometry.is_empty:
                coords = row.geometry.centroid.coords[0]
                lat, lon = coords[1], coords[0]
                weight = float(row.get("OBITOS", 0) * 13 + row.get("FERIDOS", 0) * 5 + row.get("ILESOS", 0))
                heat_data.append([lat, lon, max(weight, 1)])
        except Exception:
            continue
    
    return heat_data
