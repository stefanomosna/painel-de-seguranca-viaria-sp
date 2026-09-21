# Painel de Segurança Viária — Rodovias do Estado de São Paulo

Dashboard BI/GIS de acidentes, ocorrências e gestão da malha rodoviária
concessionada do estado de São Paulo, construído com **Streamlit**, **Pandas**,
**Plotly** e **Folium** a partir dos dados abertos da
[ARTESP](https://dadosabertos.artesp.sp.gov.br/).

**Demo ao vivo:** `https://artesp-seguranca-viaria.streamlit.app` *(link a definir após o deploy)*

---

## Destaques

- **5 telas integradas:** visão geral, indicadores, mapa GIS, análise temporal e dados brutos,
  com filtros compartilhados por ano, período e concessionária.
- **~945 mil acidentes (2001–2026)** processados automaticamente: download, limpeza,
  correção de encoding (mojibake), padronização de schema e tratamento de geocoordenadas.
- **Pipeline geoespacial** KMZ → GeoJSON (EPSG:4326) via GeoPandas, com georreferenciamento
  da malha rodoviária no mapa.
- **KPIs e risco:** taxa de fatalidade, feridos/ilesos, score de severidade por rodovia
  (Óbitos×13 + Feridos×5 + Ilesos×1) e métricas por turno, dia da semana e região.
- **Identidade visual própria:** fonte Inter Tight e paleta em gradiente azul→roxo.

## Funcionalidades por tela

| Tela | O que entrega |
|---|---|
| **Visão geral** | KPIs (acidentes, óbitos, feridos, taxa de fatalidade), evolução mensal, top ocorrências, acidentes por concessionária e por turno |
| **Indicadores** | Filtro de período (2001–2026), rodovias mais perigosas por score de severidade, top municípios, tendência mensal, dia da semana e região administrativa |
| **Mapa** | Camada de calor por severidade e marcadores coloridos em Leaflet, sobre a malha rodoviária concessionada |
| **Análise temporal** | Séries mensais/trimestrais/anuais, matriz dia-da-semana × hora, horários de pico e distribuição por turno |
| **Dados brutos** | Exploração tabular dos registros filtrados |

## Tecnologias

| Camada | Ferramenta |
|---|---|
| App | Streamlit (multipágina) |
| Dados | Pandas, NumPy |
| Visualização | Plotly, Folium / Leaflet |
| Geoespacial | GeoPandas, Shapely, kml2geojson |
| Fonte de dados | API CKAN — Portal de Dados Abertos da ARTESP |

## Estrutura do projeto

```
├── app.py                 # Página principal (visão geral + filtros globais)
├── pages/
│   ├── 1_Indicadores.py
│   ├── 2_Mapa.py
│   ├── 3_Analise_Temporal.py
│   └── 4_Dados_Brutos.py
├── utils/
│   ├── data_loader.py     # Download/parsing dos CSVs (mojibake, duplo-quote)
│   ├── metrics.py         # KPIs, séries e score de severidade
│   ├── geo_utils.py       # KMZ → GeoJSON e operações espaciais
│   └── plot_style.py      # Fonte e paleta (padrões visuais compartilhados)
├── requirements.txt
└── README.md
```

## Como rodar localmente

```bash
git clone https://github.com/stefanomosna/painel-de-seguranca-viaria-sp.git
cd painel-de-seguranca-viaria-sp
pip install -r requirements.txt
streamlit run app.py
```

Os dados são baixados automaticamente da API da ARTESP na primeira execução —
nenhum dado bruto é versionado no repositório.

## Dados

- Acidentes em rodovias concessionadas de SP (2001–2026) — Portal de Dados Abertos da ARTESP
- Malha rodoviária concessionada (KMZ → GeoJSON)

Projeto demonstrativo de Análise de Dados BI/GIS.