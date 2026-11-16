"""Dashboard en Streamlit.

Responsable: Integrante 4.
Estado: PLANTILLA.

Ejecutar desde la raíz del repositorio:
    streamlit run dashboard/app.py

Qué tiene que mostrar (CONTRATO.md, sección 7):
- Desde Cassandra: tarjetas con los KPIs (kpis_por_fecha) y la tendencia diaria (resumen_diario).
- Desde MongoDB: buscador de partidas por jugador o por id.
- Desde Neo4j: grafo de enfrentamientos dibujado con pyvis.
"""

import json
import sys
from pathlib import Path

# Permite "from comun..." aunque Streamlit se ejecute desde otra carpeta
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from comun import configuracion as cfg  # noqa: E402

st.set_page_config(page_title="Lichess Analytics", layout="wide")
st.title("Lichess Analytics")
st.info("Plantilla del dashboard: pendiente (Integrante 4). Mientras tanto, muestra la muestra limpia.")

ruta = cfg.DIR_MUESTRA / "partidas_limpias.jsonl"
partidas = [json.loads(linea) for linea in ruta.read_text(encoding="utf-8").splitlines() if linea]
st.metric("Partidas en la muestra", len(partidas))
st.dataframe(partidas[:50])
