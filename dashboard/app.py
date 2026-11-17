"""Dashboard en Streamlit — Lichess Analytics.

Responsable: Integrante 4.

Ejecutar desde la raíz del repositorio:
    streamlit run dashboard/app.py
"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Lichess Analytics", layout="wide")
st.title("Lichess Analytics")

# ─── helpers de conexión (cacheados, tolerantes a fallo) ─────────────────────

@st.cache_resource
def _cassandra():
    from comun.conexiones import obtener_cassandra
    return obtener_cassandra()

@st.cache_resource
def _mongo():
    from comun.conexiones import obtener_mongo
    return obtener_mongo()

@st.cache_resource
def _neo4j():
    from comun.conexiones import obtener_neo4j
    return obtener_neo4j()

# ─── Sección 1: KPIs y tendencia (Cassandra) ─────────────────────────────────

st.header("KPIs del día")

fecha_elegida: date = st.date_input("Fecha", value=date.today() - timedelta(days=1))
anio_mes = str(fecha_elegida)[:7]

try:
    sesion = _cassandra()

    filas_kpi = sesion.execute(
        "SELECT kpi, valor, detalle FROM kpis_por_fecha WHERE fecha = %s",
        (fecha_elegida,),
    )
    kpis = {f.kpi: (f.valor, f.detalle or "") for f in filas_kpi}

    KPI_LABELS = {
        "partidas_dia":                "Partidas del dia",
        "crecimiento_diario_pct":      "Crecimiento diario (%)",
        "tasa_victoria_blancas_pct":   "Tasa victoria blancas (%)",
        "apertura_top":                "Apertura top — rendimiento (%)",
        "jugador_mas_rivales":         "Jugador con mas rivales (N)",
        "promedio_partidas_por_jugador": "Promedio partidas/jugador",
    }

    if kpis:
        cols = st.columns(3)
        for i, (nombre, label) in enumerate(KPI_LABELS.items()):
            if nombre in kpis:
                valor, detalle = kpis[nombre]
                cols[i % 3].metric(label, f"{valor:.2f}", help=detalle if detalle else None)
    else:
        st.info(
            f"No hay KPIs calculados para {fecha_elegida}. "
            "Corre `calcular_kpis` primero (etapa 6 del DAG)."
        )

    # Tendencia del mes
    st.subheader("Tendencia mensual")
    filas_resumen = sesion.execute(
        "SELECT fecha, total_partidas, victorias_blancas, victorias_negras, tablas, jugadores_activos "
        "FROM resumen_diario WHERE anio_mes = %s",
        (anio_mes,),
    )
    datos = sorted(
        [
            {
                "fecha": str(f.fecha),
                "partidas": f.total_partidas or 0,
                "v_blancas": f.victorias_blancas or 0,
                "v_negras": f.victorias_negras or 0,
                "tablas": f.tablas or 0,
                "jugadores": f.jugadores_activos or 0,
            }
            for f in filas_resumen
        ],
        key=lambda x: x["fecha"],
    )
    if datos:
        df = pd.DataFrame(datos).set_index("fecha")
        st.line_chart(df[["partidas", "jugadores"]])
        with st.expander("Ver tabla completa"):
            st.dataframe(df)
    else:
        st.info(f"Sin datos de resumen para {anio_mes}.")

except Exception as e:
    st.error(f"Cassandra no disponible: {e}")

st.divider()

# ─── Sección 2: Buscador de partidas (MongoDB) ───────────────────────────────

st.header("Buscador de partidas")
busqueda = st.text_input("Buscar por jugador (id de Lichess) o por id de partida")

if busqueda:
    try:
        db = _mongo()
        from comun.contrato import COLECCION_PARTIDAS

        # El id de partida distingue mayúsculas (ej. "8Y0wdeIi"); el id de jugador va en minúsculas.
        termino = busqueda.strip()
        jugador = termino.lower()
        resultados = list(
            db[COLECCION_PARTIDAS].find(
                {
                    "$or": [
                        {"_id": termino},
                        {"players.white.user.id": jugador},
                        {"players.black.user.id": jugador},
                    ]
                },
                limit=20,
            )
        )
        if resultados:
            st.success(f"{len(resultados)} partida(s) encontrada(s).")
            # _id es str (id de partida), _cargado_en es datetime — los convertimos para JSON
            limpios = []
            for p in resultados:
                p["_id"] = str(p["_id"])
                if "_cargado_en" in p:
                    p["_cargado_en"] = str(p["_cargado_en"])
                limpios.append(p)
            st.json(limpios[:5])
            if len(limpios) > 5:
                st.caption(f"Mostrando 5 de {len(limpios)}.")
        else:
            st.warning("Sin resultados.")
    except Exception as e:
        st.error(f"MongoDB no disponible: {e}")

st.divider()

# ─── Sección 3: Grafo de enfrentamientos (Neo4j + pyvis) ─────────────────────

st.header("Grafo de enfrentamientos")
jugador_id = st.text_input("Id del jugador (ej. dr_tiger)", key="jugador_grafo").strip().lower()

if jugador_id:
    try:
        driver = _neo4j()
        with driver.session() as neo_sesion:
            aristas = neo_sesion.run(
                "MATCH (j:Jugador {id: $id})-[e:ENFRENTO]-(r:Jugador) "
                "RETURN j.id AS origen, r.id AS rival, e.veces AS veces "
                "LIMIT 60",
                id=jugador_id,
            ).data()

        if aristas:
            from pyvis.network import Network

            net = Network(height="520px", width="100%", bgcolor="#0e1117", font_color="white")
            net.add_node(jugador_id, label=jugador_id, color="#f7c948", size=22)
            for a in aristas:
                rival = a["rival"]
                veces = int(a["veces"] or 1)
                net.add_node(rival, label=rival, color="#4a9eff", size=10 + min(veces, 18))
                net.add_edge(
                    jugador_id, rival,
                    title=f"{veces} partida(s)",
                    width=max(1, min(veces / 5, 6)),
                )
            html_grafo = net.generate_html()
            components.html(html_grafo, height=540)
            st.caption(f"{len(aristas)} rival(es) de {jugador_id}.")
        else:
            st.warning(f"No se encontro '{jugador_id}' o no tiene enfrentamientos registrados.")
    except Exception as e:
        st.error(f"Neo4j no disponible o pyvis no instalado: {e}")
