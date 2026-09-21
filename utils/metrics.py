"""
Módulo de cálculos de indicadores e métricas.
KPIs para o painel de segurança viária.
"""
import pandas as pd
import numpy as np


def compute_kpis(df: pd.DataFrame) -> dict:
    """
    Calcula os principais KPIs do dataset de acidentes.
    
    Retorna
    -------
    dict com chaves:
        total_acidentes, total_obitos, total_feridos, total_ilesos,
        taxa_fatalidade, acidentes_por_concessionaria,
        acidentes_por_mes, top_municipios, acidentes_por_tipo
    """
    if df.empty:
        return _empty_kpis()
    
    total_acidentes = len(df)
    total_obitos = int(df["OBITOS"].sum()) if "OBITOS" in df.columns else 0
    total_feridos = int(df["FERIDOS"].sum()) if "FERIDOS" in df.columns else 0
    total_ilesos = int(df["ILESOS"].sum()) if "ILESOS" in df.columns else 0
    
    total_vitimas = total_obitos + total_feridos + total_ilesos
    taxa_fatalidade = (
        (total_obitos / total_vitimas * 100) if total_vitimas > 0 else 0
    )
    
    # Acidentes por concessionária
    acidentes_por_conc = (
        df["CONCESSIONARIA"].value_counts().head(10)
        if "CONCESSIONARIA" in df.columns
        else pd.Series(dtype=int)
    )
    
    # Acidentes por mês (série temporal)
    acidentes_por_mes = pd.Series(dtype=int)
    if "DATA" in df.columns:
        acidentes_por_mes = (
            df.set_index("DATA").resample("ME").size()
        )
    
    # Top municípios
    top_municipios = (
        df["MUNICIPIO"].value_counts().head(15)
        if "MUNICIPIO" in df.columns
        else pd.Series(dtype=int)
    )
    
    # Acidentes por tipo de ocorrência
    acidentes_por_tipo = (
        df["CLASSE"].value_counts().head(10)
        if "CLASSE" in df.columns
        else pd.Series(dtype=int)
    )
    
    # Acidentes por turno
    acidentes_por_turno = (
        df["TURNO_DO_DIA"].value_counts()
        if "TURNO_DO_DIA" in df.columns
        else pd.Series(dtype=int)
    )
    
    # Acidentes por dia da semana
    acidentes_por_dia = (
        df["DIA_SEMANA"].value_counts()
        if "DIA_SEMANA" in df.columns
        else pd.Series(dtype=int)
    )
    
    # Rodovias mais perigosas
    rodovias_perigosas = pd.Series(dtype=float)
    if all(c in df.columns for c in ["RODOVIA", "OBITOS", "FERIDOS"]):
        rodovias_perigosas = (
            df.groupby("RODOVIA")
            .agg(total_acidentes=("OBITOS", "size"), total_obitos=("OBITOS", "sum"), total_feridos=("FERIDOS", "sum"))
            .assign(severidade=lambda x: x["total_obitos"] * 13 + x["total_feridos"] * 5)
            .sort_values("severidade", ascending=False)
            .head(10)
        )
    
    return {
        "total_acidentes": total_acidentes,
        "total_obitos": total_obitos,
        "total_feridos": total_feridos,
        "total_ilesos": total_ilesos,
        "taxa_fatalidade": round(taxa_fatalidade, 2),
        "acidentes_por_concessionaria": acidentes_por_conc,
        "acidentes_por_mes": acidentes_por_mes,
        "top_municipios": top_municipios,
        "acidentes_por_tipo": acidentes_por_tipo,
        "acidentes_por_turno": acidentes_por_turno,
        "acidentes_por_dia": acidentes_por_dia,
        "rodovias_perigosas": rodovias_perigosas,
    }


def compute_monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula tendência mensal com estatísticas de vítimas.
    
    Retorna DataFrame com colunas:
        mes_ano, total_acidentes, total_obitos, total_feridos,
        media_acidentes_dia
    """
    if df.empty or "DATA" not in df.columns:
        return pd.DataFrame()
    
    monthly = (
        df.set_index("DATA")
        .resample("ME")
        .agg(
            total_acidentes=("OBITOS", "size") if "OBITOS" in df.columns else ("DATA", "size"),
            total_obitos=("OBITOS", "sum") if "OBITOS" in df.columns else ("DATA", "count"),
            total_feridos=("FERIDOS", "sum") if "FERIDOS" in df.columns else ("DATA", "count"),
        )
    )
    
    monthly["dias_no_mes"] = monthly.index.days_in_month
    monthly["media_acidentes_dia"] = (
        monthly["total_acidentes"] / monthly["dias_no_mes"]
    ).round(2)
    
    monthly = monthly.reset_index()
    monthly.columns = [
        "mes_ano", "total_acidentes", "total_obitos", "total_feridos",
        "dias_no_mes", "media_acidentes_dia"
    ]
    
    return monthly


def compute_hourly_heatmap(df: pd.DataFrame) -> pd.DataFrame:
    """
    Gera matriz de acidentes por dia da semana x hora do dia.
    """
    if df.empty or "DIA_SEMANA" not in df.columns or "HORA_DIA" not in df.columns:
        return pd.DataFrame()
    
    dias_ordem = [
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday"
    ]
    
    matrix = pd.crosstab(df["DIA_SEMANA"], df["HORA_DIA"])
    
    # Reordenar dias e garantir colunas 0..23
    for d in dias_ordem:
        if d not in matrix.index:
            matrix.loc[d] = 0
    for h in range(24):
        if h not in matrix.columns:
            matrix[h] = 0
    matrix = matrix.reindex(dias_ordem)
    matrix = matrix.reindex(columns=range(24))
    
    # Traduzir nomes dos dias
    traducao = {
        "Monday": "Segunda", "Tuesday": "Terça", "Wednesday": "Quarta",
        "Thursday": "Quinta", "Friday": "Sexta", "Saturday": "Sábado",
        "Sunday": "Domingo",
    }
    matrix.index = [traducao.get(d, d) for d in matrix.index]
    
    return matrix


def compute_risk_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula score de risco por rodovia (Índice Crítico simplificado).
    
    Fórmula: IC = (ILE*1 + FER*5 + FAT*13) / (extensao_km * VDM * dias / 1_000_000)
    Sem VDM, usamos apenas o peso das vítimas como proxy.
    """
    if df.empty or "RODOVIA" not in df.columns:
        return pd.DataFrame()
    
    risk = (
        df.groupby("RODOVIA")
        .agg(
            total_acidentes=("OBITOS", "size") if "OBITOS" in df.columns else ("DATA", "size"),
            obitos=("OBITOS", "sum") if "OBITOS" in df.columns else ("DATA", "count"),
            feridos=("FERIDOS", "sum") if "FERIDOS" in df.columns else ("DATA", "count"),
            ilesos=("ILESOS", "sum") if "ILESOS" in df.columns else ("DATA", "count"),
        )
    )
    
    risk["score_severidade"] = (
        risk["obitos"] * 13 + risk["feridos"] * 5 + risk["ilesos"] * 1
    )
    
    risk["indice_fatalidade"] = (
        risk["obitos"] / risk["total_acidentes"] * 100
    ).round(2)
    
    return risk.sort_values("score_severidade", ascending=False)


def _empty_kpis() -> dict:
    """Retorna KPIs vazios quando não há dados."""
    return {
        "total_acidentes": 0,
        "total_obitos": 0,
        "total_feridos": 0,
        "total_ilesos": 0,
        "taxa_fatalidade": 0.0,
        "acidentes_por_concessionaria": pd.Series(dtype=int),
        "acidentes_por_mes": pd.Series(dtype=int),
        "top_municipios": pd.Series(dtype=int),
        "acidentes_por_tipo": pd.Series(dtype=int),
        "acidentes_por_turno": pd.Series(dtype=int),
        "acidentes_por_dia": pd.Series(dtype=int),
        "rodovias_perigosas": pd.Series(dtype=float),
    }
