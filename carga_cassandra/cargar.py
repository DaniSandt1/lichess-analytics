"""Transformación y carga en Cassandra.

Responsable: Integrante 2.
Estado: PLANTILLA.

Qué tiene que hacer (CONTRATO.md, sección 3):
- carga_cassandra/esquema.cql: CREATE KEYSPACE y las 6 tablas del contrato.
- carga_cassandra/crear_esquema.py: ejecuta esquema.cql (lo puede llamar cargar_en_cassandra
  al inicio, con IF NOT EXISTS, para que el DAG funcione aunque nadie lo haya corrido antes).
- cargar_en_cassandra:
    1. Insertar cada registro limpio en partidas_por_fecha (INSERT es upsert: reejecutar no duplica).
    2. Para cada fecha presente en el lote, LEER toda la partición de partidas_por_fecha de esa
       fecha y RECALCULAR las filas de partidas_por_dia, resumen_diario, resultados_por_apertura
       y actividad_por_jugador de esa fecha. Así los agregados siempre cuadran y son idempotentes.
       No usen columnas counter: si el DAG se reintenta, contarían dos veces.
- kpis_por_fecha la crea Integrante 2 pero la llena Integrante 4.
"""

from comun.contrato import TABLA_PARTIDAS_POR_FECHA


def cargar_en_cassandra(ruta_limpia: str) -> int:
    """FUNCIÓN DEL CONTRATO. Devuelve cuántas partidas se escribieron en partidas_por_fecha."""
    print(f"[PENDIENTE - Integrante 2] cargar_en_cassandra({ruta_limpia}) -> {TABLA_PARTIDAS_POR_FECHA} y agregados")
    return 0
