# Painel de Segurança Viária — Rodovias do Estado de São Paulo (ARTESP)

Dashboard BI/GIS de acidentes, ocorrências e gestão da malha rodoviária
concessionada do estado de São Paulo, construído com **Streamlit**, **Pandas**,
**Plotly** e **Folium**, utilizando os dados abertos da
[ARTESP](https://dadosabertos.artesp.sp.gov.br/).

> ⚠️ **Demo ao vivo:** [inserir URL do Streamlit Cloud após o deploy]

---

## Funcionalidades

- **Visão geral** — KPIs (acidentes, óbitos, feridos, taxa de fatalidade) e gráficos
  de evolução mensal, tipos de ocorrência, concessionárias e turnos do dia.
- **Indicadores** — análises detalhadas com filtros por ano, concessionária e tipo.
- **Mapa GIS** — visualização geoespacial em Folium/Leaflet com camada de calor por
  severidade e geometricização da malha rodoviária.
- **Análise temporal** — séries históricas 2001–2026.
- **Dados brutos** — exploração tabular dos registros filtrados.

Os dados são baixados automaticamente da API CKAN do portal de dados abertos
da ARTESP na primeira execução (nenhum dado bruto é versionado no repositório).

## Como rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

Abra o endereço indicado no terminal (padrão `http://localhost:8501`).

## Estrutura do projeto

```
├── app.py                 # Página principal (visão geral + filtros globais)
├── pages/
│   ├── 1_Indicadores.py
│   ├── 2_Mapa.py
│   ├── 3_Analise_Temporal.py
│   └── 4_Dados_Brutos.py
├── utils/
│   ├── data_loader.py     # Download e parsing dos CSVs da ARTESP
│   ├── metrics.py         # Cálculo de KPIs e séries
│   ├── geo_utils.py       # Conversão KMZ → GeoJSON e operações espaciais
│   └── plot_style.py      # Padronização visual dos gráficos
└── requirements.txt
```

## Fontes de dados

- Portal de Dados Abertos da ARTESP — acidentes em rodovias concedidas (2001–2026)
- Malha rodoviária concessionada (KMZ → GeoJSON)

Projeto demonstrativo de Análise de Dados BI/GIS.