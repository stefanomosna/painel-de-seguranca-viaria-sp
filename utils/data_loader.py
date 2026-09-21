"""
Módulo de carregamento de dados da ARTESP via API CKAN.
Portal: https://dadosabertos.artesp.sp.gov.br/

Nota sobre o formato dos arquivos CSV:
- Texto duplamente codificado em UTF-8 (mojibake) – corrigido em `_fix_mojibake`
- Cada linha inteira envolta em aspas duplas – tratado em `_read_artesp_csv`
- Campos com vírgulas internas usam aspas duplas internas – tratado pelo csv
"""
import csv
import io
from pathlib import Path

import numpy as np
import pandas as pd
import requests

BASE_URL = "https://dadosabertos.artesp.sp.gov.br/api/3/action"
DATA_DIR = Path(__file__).parent.parent / "data"

# Colunas do schema principal (2001–2026)
SCHEMA_PRINCIPAL = {
    "DATA", "HORA", "CONCESSIONARIA", "RODOVIA", "KM", "SENTIDO",
    "LATITUDE", "LONGITUDE", "CLASSE", "SUBCLASSE", "CAUSA_PROVAVEL",
    "VITIMA_ILESA", "VITIMA_LEVE", "VITIMA_MODERADA", "VITIMA_GRAVE",
    "VITIMA_FATAL", "VITIMAS_SEM_INFO", "VEICULOS_ENVOLVIDOS",
    "VISIBILIDADE", "CONDICAO_METERIOLOGICA", "MUNICIPIO",
    "REGIAO_ADMINISTRATIVA", "REGIONAL_DER", "JURISDICAO",
}


def _get_resources(dataset_id: str) -> list[dict]:
    """Retorna lista de recursos de um dataset CKAN."""
    resp = requests.get(f"{BASE_URL}/package_show?id={dataset_id}", timeout=30)
    resp.raise_for_status()
    return resp.json()["result"]["resources"]


def _fix_mojibake(raw: bytes) -> str:
    """
    Corrige texto duplamente codificado em UTF-8.
    
    O portal gera arquivos onde o texto UTF-8 original foi tratado como
    Latin-1 e re-encodado em UTF-8. Ex: 'JUNDIAÍ' vira 'JUNDIAÃ\x8d'.
    
    Correção reversa: decode utf-8 -> encode latin-1 -> decode utf-8.
    """
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        # Fallback: arquivo em utf-8 simples
        return raw.decode("utf-8", errors="replace")
    
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def _read_artesp_csv(path: Path | str) -> pd.DataFrame:
    """
    Lê um CSV da ARTESP suportando os dois formatos publicados pelo portal:

    1. Formato legado: cada linha inteira envolta em aspas duplas e texto
       duplamente codificado em UTF-8 (mojibake).
    2. Formato atual: CSV padrão em UTF-8 (sem envelope e sem mojibake).

    A detecção é automática, linha a linha: se a interpretação simples do CSV
    devolver um único campo que contém vírgulas, é o formato legado (re-parse).
    """
    path = Path(path)
    with open(path, "rb") as fh:
        raw = fh.read()

    if not raw.strip():
        return pd.DataFrame()

    text = _fix_mojibake(raw)

    def _parse_line(line: str) -> list:
        # Passada 1: CSV simples
        outer = next(csv.reader([line], delimiter=",", quotechar='"', doublequote=True))
        # Formato legado: a linha inteira era 1 campo quotado contendo o CSV interno
        if len(outer) == 1 and "," in outer[0]:
            return next(csv.reader([outer[0]], delimiter=",", quotechar='"', doublequote=True))
        return outer

    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(_parse_line(line))

    if not rows:
        return pd.DataFrame()

    header = rows[0]
    data = rows[1:]

    # Garantir alinhamento: linhas com número errado de campos são completadas
    n_cols = len(header)
    for i, row in enumerate(data):
        if len(row) != n_cols:
            data[i] = row[:n_cols] + [None] * max(0, n_cols - len(row))

    return pd.DataFrame(data, columns=header)


def _clean_acidentes(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza nomes de colunas, tipos e deriva variáveis temporais."""
    df = df.copy()

    # Normalizar nomes de colunas (remove acentos para robustez a variações do portal)
    import unicodedata

    def _deaccent(s: str) -> str:
        return "".join(
            ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn"
        )

    col_map = {c: _deaccent(c.strip().upper().replace(" ", "_")) for c in df.columns}
    df = df.rename(columns=col_map)

    # Eliminar coluna sem nome (artefatos de parsing)
    df = df.loc[:, ~df.columns.str.contains("Unnamed", case=False)]

    # Converter DATA
    if "DATA" in df.columns:
        try:
            df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce", dayfirst=False)
        except Exception:
            df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce", dayfirst=True)
        df["ANO"] = df["DATA"].dt.year
        df["MES"] = df["DATA"].dt.month
        df["DIA_SEMANA"] = df["DATA"].dt.day_name()

    # 'HORA' vem separada: converter para novo campo datetime completo
    if "HORA" in df.columns and "DATA" in df.columns:
        horas = (
            df["HORA"]
            .astype(str)
            .str.replace(".", ":")
            .str.extract(r"(\d{1,2}):(\d{2}):?(\d{2})?")
        )
        hora_num = pd.to_numeric(horas[0], errors="coerce").fillna(0).astype(int)
        df["HORA_DIA"] = hora_num

        # Turno do dia
        def _turno(h):
            if pd.isna(h):
                return None
            h = int(h)
            if h < 6:
                return "Madrugada"
            if h < 12:
                return "Manhã"
            if h < 18:
                return "Tarde"
            return "Noite"

        df["TURNO_DO_DIA"] = df["HORA_DIA"].apply(_turno)

        # Combinar DATA + HORA
        try:
            df["DATETIME"] = pd.to_datetime(
                df["DATA"].astype(str).str[:10] + " " + df["HORA"].astype(str).str[:5],
                errors="coerce",
            )
        except Exception:
            pass
    else:
        df["HORA_DIA"] = None
        df["TURNO_DO_DIA"] = None

    # Nomear colunas de vítimas de forma consistente
    renomear_vitimas = {
        "VITIMA_ILESA": "ILESOS",
        "VITIMA_LEVE": "FERIDO_LEVE",
        "VITIMA_MODERADA": "FERIDO_MODERADO",
        "VITIMA_GRAVE": "FERIDO_GRAVE",
        "VITIMA_FATAL": "OBITOS",
    }
    df = df.rename(columns={k: v for k, v in renomear_vitimas.items() if k in df.columns})

    if "ILESOS" not in df.columns:
        df["ILESOS"] = 0
    if "OBITOS" not in df.columns:
        df["OBITOS"] = 0

    # Converter numéricos de vítimas ANTES de somar (evita concatenação de strings)
    for col in ["OBITOS", "ILESOS", "FERIDO_LEVE", "FERIDO_MODERADO", "FERIDO_GRAVE"]:
        if col in df.columns:
            _coerce_numeric(df, col)

    # FERIDOS = leves + moderados + graves
    if all(c in df.columns for c in ["FERIDO_LEVE", "FERIDO_MODERADO", "FERIDO_GRAVE"]):
        df["FERIDOS"] = (
            df["FERIDO_LEVE"] + df["FERIDO_MODERADO"] + df["FERIDO_GRAVE"]
        )
    elif "FERIDOS" not in df.columns:
        df["FERIDOS"] = 0
    if "FERIDOS" in df.columns:
        _coerce_numeric(df, "FERIDOS")

    # KM
    if "KM" in df.columns:
        df["KM"] = pd.to_numeric(
            df["KM"].astype(str).str.replace(",", "."), errors="coerce"
        )

    # Lat/Long
    for col in ["LATITUDE", "LONGITUDE"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def load_acidentes(ano: int | None = None, cache: bool = True) -> pd.DataFrame:
    """
    Carrega dados de acidentes da malha rodoviária estadual (schema principal).

    Parâmetros
    ----------
    ano : int, opcional
        Ano específico para filtrar. None retorna todos os anos disponíveis.
    cache : bool
        Se True, baixa e salva CSVs locais para reuso.

    Retorna
    -------
    pd.DataFrame com colunas padronizadas (data, vítimas, geolocalização).
    """
    cache_dir = DATA_DIR / "raw"
    cache_dir.mkdir(parents=True, exist_ok=True)

    resources = _get_resources("acidentes")
    frames = []

    import re

    for res in resources:
        if res["format"] not in ("CSV", "csv"):
            continue

        name = res.get("name", "")

        # Manter apenas arquivos anuais (2001-2026) do schema principal com coords.
        # Arquivos auxiliares (INFOSIGA, Fumaça/Neblina) são ignorados.
        m_ano = re.search(r"(\d{4})", name)
        if not m_ano:
            continue
        year = int(m_ano.group(1))
        if ano and year != ano:
            continue

        url = res.get("url") or res.get("download_url")
        if not url:
            continue

        fname = f"acidentes_{year}.csv"
        fpath = cache_dir / fname

        try:
            if cache and fpath.exists():
                df = _read_artesp_csv(fpath)
            else:
                resp = requests.get(url, timeout=120)
                resp.raise_for_status()
                fpath.write_bytes(resp.content)
                df = _read_artesp_csv(fpath)
        except Exception:
            # Um arquivo com falha de download não pode derrubar o app todo
            continue

        if not df.empty:
            frames.append(df)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    # Eliminar colunas duplicadas (arquivos com headers ligeiramente distintos)
    combined = combined.loc[:, ~combined.columns.duplicated()]
    return _clean_acidentes(combined)


def _coerce_numeric(df: pd.DataFrame, col: str) -> None:
    """Coage uma coluna a numérica de forma segura (lida com valores estranhos)."""
    serie = df[col]
    if not isinstance(serie, pd.Series):
        serie = pd.Series(np.ravel(serie), index=df.index, name=col)
    df[col] = pd.to_numeric(serie, errors="coerce").fillna(0).astype(int)


def load_ocorrencias(cache: bool = True) -> pd.DataFrame:
    """Carrega dados de ocorrências gerais (panes, alagamentos, etc.)."""
    cache_dir = DATA_DIR / "raw"
    cache_dir.mkdir(parents=True, exist_ok=True)

    try:
        resources = _get_resources("ocorrenciass")
    except Exception:
        return pd.DataFrame()

    frames = []
    for res in resources:
        if res["format"] not in ("CSV", "csv"):
            continue

        url = res.get("url") or res.get("download_url")
        if not url:
            continue

        fname = f"ocorrencias_{res['id'][:8]}.csv"
        fpath = cache_dir / fname

        try:
            if cache and fpath.exists():
                df = _read_artesp_csv(fpath)
            else:
                resp = requests.get(url, timeout=120)
                resp.raise_for_status()
                fpath.write_bytes(resp.content)
                df = _read_artesp_csv(fpath)
            frames.append(df)
        except Exception:
            continue

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def get_rodovias_info() -> dict:
    """
    Retorna metadados das rodovias concessionadas (KMZ disponíveis).
    """
    try:
        resources = _get_resources("malha-rodoviaria")
        kmz_resources = [r for r in resources if r["format"].upper() == "KMZ"]
        return {
            "total_kmz": len(kmz_resources),
            "resources": [
                {"name": r.get("name", r["id"]), "url": r.get("url")}
                for r in kmz_resources
            ],
        }
    except Exception:
        return {"total_kmz": 0, "resources": []}