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


CONSULTA_MAS_RIVALES = (
    "MATCH (j:Jugador)-[:ENFRENTO]-(r:Jugador) "
    "WITH j, count(DISTINCT r) AS rivales "
    "ORDER BY rivales DESC, j.id LIMIT 1 "
    "RETURN j.id AS jugador, rivales"
)


def jugador_mas_rivales() -> list:
    """KPI 5 desde Neo4j. Es acumulado (no depende de la fecha), así que un rango lo consulta una vez."""
    with obtener_neo4j() as driver:
        return driver.execute_query(CONSULTA_MAS_RIVALES).records


def calcular_kpis(fecha: str, sesion=None, rivales=None) -> dict:
    """FUNCIÓN DEL CONTRATO. `fecha` es "YYYY-MM-DD" (la fecha lógica del DAG).

    `sesion` (Cassandra) y `rivales` (resultado de jugador_mas_rivales) son opcionales: al calcular
    un rango de días se pasan ya abiertos/calculados para no crear una conexión nueva por día
    (cada conexión crea hilos, y con ~100 días Windows se queda sin hilos: "can't start new thread").
    El DAG llama solo con `fecha`, y entonces la función abre y cierra sus propias conexiones.
    """
    sesion_propia = sesion is None
    if sesion_propia:
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

    # Si un KPI no se puede calcular (división entre 0), se guarda None (null en Cassandra) con el
    # motivo en `detalle`. Guardar 0.0 sería engañoso: "0 % de crecimiento" no es lo mismo que
    # "no hubo partidas el día anterior".

    # KPI 1: partidas_dia
    kpis["partidas_dia"] = float(p_d)
    detalles["partidas_dia"] = ""

    # KPI 2: crecimiento_diario_pct
    kpis["crecimiento_diario_pct"] = ((p_d - p_ayer) / p_ayer * 100) if p_ayer else None
    detalles["crecimiento_diario_pct"] = f"{p_ayer} partidas el día anterior" if p_ayer else "sin partidas el día anterior"

    # KPI 3: tasa_victoria_blancas_pct
    kpis["tasa_victoria_blancas_pct"] = (victorias_blancas_d / p_d * 100) if p_d else None
    detalles["tasa_victoria_blancas_pct"] = "" if p_d else "sin partidas ese día"

    # KPI 6: promedio_partidas_por_jugador
    kpis["promedio_partidas_por_jugador"] = (2 * p_d / jugadores_activos) if jugadores_activos else None
    detalles["promedio_partidas_por_jugador"] = "" if jugadores_activos else "sin partidas ese día"

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
        # Más partidas primero; si empatan, el código ECO menor, para que el resultado no cambie entre ejecuciones
        top_eco = min(conteo, key=lambda e: (-conteo[e]["total"], e))
        d = conteo[top_eco]
        rendimiento = (d["vb"] + 0.5 * d["tablas"]) / d["total"] * 100 if d["total"] else 0.0
        kpis["apertura_top"] = rendimiento
        detalles["apertura_top"] = f"{top_eco} - {d['nombre']}"
    else:
        kpis["apertura_top"] = None
        detalles["apertura_top"] = "sin partidas ese día"

    # KPI 5: jugador_mas_rivales (Neo4j, acumulado — no depende de la fecha)
    records = rivales if rivales is not None else jugador_mas_rivales()

    if records:
        kpis["jugador_mas_rivales"] = float(records[0]["rivales"])
        detalles["jugador_mas_rivales"] = str(records[0]["jugador"])
    else:
        kpis["jugador_mas_rivales"] = None
        detalles["jugador_mas_rivales"] = "grafo vacío"

    # --- Guardar en kpis_por_fecha (INSERT en Cassandra = sobrescribe, idempotente) ---
    stmt = sesion.prepare(
        f"INSERT INTO {TABLA_KPIS_POR_FECHA} (fecha, kpi, valor, detalle, calculado_en) "
        f"VALUES (?, ?, ?, ?, ?)"
    )
    for nombre_kpi, valor in kpis.items():
        sesion.execute(stmt, (fecha_dt, nombre_kpi, valor, detalles.get(nombre_kpi, ""), ahora))
        print(f"[KPI] {nombre_kpi} ({fecha}): {valor}  detalle={detalles.get(nombre_kpi, '')!r}")

    if sesion_propia:
        sesion.cluster.shutdown()
    return kpis


if __name__ == "__main__":
    # Calcular los KPIs de un día o de un rango de días (por ejemplo, después de la carga inicial,
    # para que el dashboard tenga KPIs en todas las fechas y no solo en las que procesó el DAG):
    #   python -m kpis.calcular --fecha 2026-11-14
    #   python -m kpis.calcular --desde 2026-08-01 --hasta 2026-11-16
    import argparse

    parser = argparse.ArgumentParser(description="Calcula los KPIs y los guarda en kpis_por_fecha")
    parser.add_argument("--fecha", help="un día, YYYY-MM-DD")
    parser.add_argument("--desde", help="inicio del rango, YYYY-MM-DD")
    parser.add_argument("--hasta", help="fin del rango, YYYY-MM-DD (por defecto, hoy en UTC)")
    args = parser.parse_args()

    if args.desde:
        dia = date.fromisoformat(args.desde)
        fin = date.fromisoformat(args.hasta) if args.hasta else datetime.now(timezone.utc).date()
        # Una sola conexión a Cassandra y una sola consulta a Neo4j para todo el rango
        sesion = obtener_cassandra()
        rivales = jugador_mas_rivales()
        try:
            while dia <= fin:
                calcular_kpis(dia.isoformat(), sesion=sesion, rivales=rivales)
                dia += timedelta(days=1)
        finally:
            sesion.cluster.shutdown()
    elif args.fecha:
        calcular_kpis(args.fecha)
    else:
        parser.error("indica --fecha o --desde")
