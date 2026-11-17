"""Cálculo automático de los KPIs (última tarea del DAG).

Responsable: Integrante 4.

Qué hace (CONTRATO.md, sección 6):
- Calcula los 6 KPIs para `fecha` leyendo de Cassandra y Neo4j.
- Escribe cada uno en kpis_por_fecha de Cassandra (INSERT = upsert, idempotente).
- Devuelve un dict {nombre_kpi: valor}.
"""

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from comun.conexiones import obtener_cassandra, obtener_neo4j
from comun.contrato import (
    TABLA_KPIS_POR_FECHA,
    TABLA_PARTIDAS_POR_FECHA,
    TABLA_RESUMEN_DIARIO,
)


def calcular_kpis(fecha: str) -> dict:
    """FUNCIÓN DEL CONTRATO. `fecha` es "YYYY-MM-DD" (la fecha lógica del DAG)."""
    sesion = obtener_cassandra()
    ahora = datetime.now(timezone.utc)
    fecha_dt = date.fromisoformat(fecha)
    anio_mes = fecha[:7]

    # --- Resumen del día ---
    fila_hoy = sesion.execute(
        f"SELECT total_partidas, jugadores_activos, victorias_blancas "
        f"FROM {TABLA_RESUMEN_DIARIO} WHERE anio_mes = %s AND fecha = %s",
        (anio_mes, fecha_dt),
    ).one()

    # --- Resumen del día anterior (para crecimiento) ---
    ayer_dt = fecha_dt - timedelta(days=1)
    fila_ayer = sesion.execute(
        f"SELECT total_partidas FROM {TABLA_RESUMEN_DIARIO} WHERE anio_mes = %s AND fecha = %s",
        (str(ayer_dt)[:7], ayer_dt),
    ).one()

    p_d = int(fila_hoy.total_partidas or 0) if fila_hoy else 0
    jugadores_activos = int(fila_hoy.jugadores_activos or 0) if fila_hoy else 0
    victorias_blancas_d = int(fila_hoy.victorias_blancas or 0) if fila_hoy else 0
    p_ayer = int(fila_ayer.total_partidas or 0) if fila_ayer else 0

    kpis: dict = {}
    detalles: dict = {}

    # KPI 1: partidas_dia
    kpis["partidas_dia"] = float(p_d)
    detalles["partidas_dia"] = ""

    # KPI 2: crecimiento_diario_pct
    kpis["crecimiento_diario_pct"] = ((p_d - p_ayer) / p_ayer * 100) if p_ayer else 0.0
    detalles["crecimiento_diario_pct"] = ""

    # KPI 3: tasa_victoria_blancas_pct
    kpis["tasa_victoria_blancas_pct"] = (victorias_blancas_d / p_d * 100) if p_d else 0.0
    detalles["tasa_victoria_blancas_pct"] = ""

    # KPI 6: promedio_partidas_por_jugador
    kpis["promedio_partidas_por_jugador"] = (2 * p_d / jugadores_activos) if jugadores_activos else 0.0
    detalles["promedio_partidas_por_jugador"] = ""

    # KPI 4: apertura_top (lee toda la partición del día en partidas_por_fecha)
    conteo: dict = defaultdict(lambda: {"total": 0, "vb": 0, "tablas": 0, "nombre": ""})
    for f in sesion.execute(
        f"SELECT codigo_eco, nombre_apertura, ganador FROM {TABLA_PARTIDAS_POR_FECHA} WHERE fecha = %s",
        (fecha_dt,),
    ):
        eco = f.codigo_eco
        conteo[eco]["total"] += 1
        conteo[eco]["nombre"] = f.nombre_apertura
        if f.ganador == "blancas":
            conteo[eco]["vb"] += 1
        elif f.ganador == "tablas":
            conteo[eco]["tablas"] += 1

    if conteo:
        top_eco = max(conteo, key=lambda e: conteo[e]["total"])
        d = conteo[top_eco]
        rendimiento = (d["vb"] + 0.5 * d["tablas"]) / d["total"] * 100 if d["total"] else 0.0
        kpis["apertura_top"] = rendimiento
        detalles["apertura_top"] = f"{top_eco} - {d['nombre']}"
    else:
        kpis["apertura_top"] = 0.0
        detalles["apertura_top"] = ""

    # KPI 5: jugador_mas_rivales (Neo4j, acumulado — no depende de la fecha)
    with obtener_neo4j() as driver:
        records = driver.execute_query(
            "MATCH (j:Jugador)-[:ENFRENTO]-(r:Jugador) "
            "WITH j, count(DISTINCT r) AS rivales "
            "ORDER BY rivales DESC LIMIT 1 "
            "RETURN j.id AS jugador, rivales"
        ).records

    if records:
        kpis["jugador_mas_rivales"] = float(records[0]["rivales"])
        detalles["jugador_mas_rivales"] = str(records[0]["jugador"])
    else:
        kpis["jugador_mas_rivales"] = 0.0
        detalles["jugador_mas_rivales"] = ""

    # --- Guardar en kpis_por_fecha (INSERT en Cassandra = sobrescribe, idempotente) ---
    stmt = sesion.prepare(
        f"INSERT INTO {TABLA_KPIS_POR_FECHA} (fecha, kpi, valor, detalle, calculado_en) "
        f"VALUES (?, ?, ?, ?, ?)"
    )
    for nombre_kpi, valor in kpis.items():
        sesion.execute(stmt, (fecha_dt, nombre_kpi, valor, detalles.get(nombre_kpi, ""), ahora))
        print(f"[KPI] {nombre_kpi} ({fecha}): {valor}  detalle={detalles.get(nombre_kpi, '')!r}")

    return kpis
