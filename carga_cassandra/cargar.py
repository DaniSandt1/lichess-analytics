"""Transformación y carga en Cassandra.

Responsable: Integrante 2.

Cómo funciona (CONTRATO.md, sección 3):
1. Crea el esquema si no existe (esquema.cql, todo con IF NOT EXISTS).
2. Inserta cada registro limpio en partidas_por_fecha. En Cassandra un INSERT con la misma
   clave primaria sobrescribe la fila, así que reejecutar el lote no duplica nada.
3. Para cada fecha presente en el lote, LEE toda la partición de partidas_por_fecha de esa
   fecha (incluidas partidas de otros lotes del mismo día) y RECALCULA desde cero las filas
   de partidas_por_dia, resumen_diario, resultados_por_apertura y actividad_por_jugador.
   No se usan columnas counter: si Airflow reintenta la tarea, contarían doble.

Probar con la muestra, sin Airflow:
    python -m carga_cassandra.cargar
"""

import json
from collections import defaultdict
from datetime import date, datetime, timezone

from cassandra.concurrent import execute_concurrent_with_args
from cassandra.query import dict_factory

from carga_cassandra.crear_esquema import crear_esquema
from comun import configuracion as cfg
from comun.conexiones import obtener_cassandra
from comun.contrato import (
    TABLA_ACTIVIDAD_POR_JUGADOR,
    TABLA_PARTIDAS_POR_DIA,
    TABLA_PARTIDAS_POR_FECHA,
    TABLA_RESULTADOS_POR_APERTURA,
    TABLA_RESUMEN_DIARIO,
    validar_registro,
)

CONCURRENCIA = 64  # escrituras en vuelo a la vez (suficiente para 60,000 partidas en segundos)

CQL_INSERTAR_PARTIDA = f"""
INSERT INTO {TABLA_PARTIDAS_POR_FECHA} (
  fecha, ritmo, id_partida, fecha_hora, jugador_blancas, jugador_negras,
  rating_blancas, rating_negras, ganador, codigo_eco, nombre_apertura, cantidad_movimientos
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

CQL_LEER_DIA = f"""
SELECT ritmo, id_partida, fecha_hora, jugador_blancas, jugador_negras,
       rating_blancas, rating_negras, ganador, codigo_eco, nombre_apertura, cantidad_movimientos
FROM {TABLA_PARTIDAS_POR_FECHA} WHERE fecha = ?
"""

CQL_PARTIDAS_POR_DIA = f"""
INSERT INTO {TABLA_PARTIDAS_POR_DIA} (fecha, ritmo, total, victorias_blancas, victorias_negras, tablas)
VALUES (?, ?, ?, ?, ?, ?)
"""

CQL_RESUMEN_DIARIO = f"""
INSERT INTO {TABLA_RESUMEN_DIARIO} (
  anio_mes, fecha, total_partidas, jugadores_activos,
  victorias_blancas, victorias_negras, tablas, promedio_movimientos
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

CQL_RESULTADOS_POR_APERTURA = f"""
INSERT INTO {TABLA_RESULTADOS_POR_APERTURA} (
  codigo_eco, fecha, nombre_apertura, total, victorias_blancas, victorias_negras, tablas
) VALUES (?, ?, ?, ?, ?, ?, ?)
"""

CQL_ACTIVIDAD_POR_JUGADOR = f"""
INSERT INTO {TABLA_ACTIVIDAD_POR_JUGADOR} (
  jugador, fecha, partidas, victorias, derrotas, tablas, rating_ultimo
) VALUES (?, ?, ?, ?, ?, ?, ?)
"""


# ---------------------------------------------------------------------------
# Lectura del lote
# ---------------------------------------------------------------------------

def leer_registros(ruta_limpia: str) -> list[dict]:
    """Lee el JSONL limpio y valida cada registro contra el contrato."""
    registros = []
    with open(ruta_limpia, encoding="utf-8") as archivo:
        for linea in archivo:
            if linea.strip():
                registro = json.loads(linea)
                validar_registro(registro)
                registros.append(registro)
    return registros


def _a_fila_partida(r: dict) -> tuple:
    """Registro limpio -> valores de partidas_por_fecha (en el orden de CQL_INSERTAR_PARTIDA)."""
    fecha_hora = datetime.strptime(r["fecha_hora"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (
        date.fromisoformat(r["fecha"]), r["ritmo"], r["id_partida"], fecha_hora,
        r["jugador_blancas"], r["jugador_negras"], r["rating_blancas"], r["rating_negras"],
        r["ganador"], r["codigo_eco"], r["nombre_apertura"], r["cantidad_movimientos"],
    )


# ---------------------------------------------------------------------------
# Agregados de un día (función pura: se puede probar sin Cassandra)
# ---------------------------------------------------------------------------

def _resultados(partidas: list[dict]) -> tuple[int, int, int, int]:
    """(total, victorias_blancas, victorias_negras, tablas)."""
    blancas = sum(1 for p in partidas if p["ganador"] == "blancas")
    negras = sum(1 for p in partidas if p["ganador"] == "negras")
    tablas = sum(1 for p in partidas if p["ganador"] == "tablas")
    return len(partidas), blancas, negras, tablas


def calcular_agregados(fecha: date, partidas: list[dict]) -> dict[str, list[tuple]]:
    """Calcula las filas de las tablas 2 a 5 para `fecha` a partir de TODAS sus partidas.

    `partidas` son filas de partidas_por_fecha (dicts). Devuelve {tabla: [valores de cada fila]}.
    """
    if not partidas:
        return {}

    # Orden cronológico: así "el último rating" y "el último nombre de apertura" son los
    # de la partida más reciente del día (el id desempata para que sea determinista).
    partidas = sorted(partidas, key=lambda p: (p["fecha_hora"], p["id_partida"]))

    # 2) partidas_por_dia: una fila por ritmo
    por_ritmo = defaultdict(list)
    for p in partidas:
        por_ritmo[p["ritmo"]].append(p)
    filas_por_dia = [(fecha, ritmo, *_resultados(grupo)) for ritmo, grupo in sorted(por_ritmo.items())]

    # 3) resumen_diario: una fila para el día
    jugadores = {p["jugador_blancas"] for p in partidas} | {p["jugador_negras"] for p in partidas}
    total, blancas, negras, tablas = _resultados(partidas)
    promedio_movimientos = round(sum(p["cantidad_movimientos"] for p in partidas) / total, 2)
    filas_resumen = [(
        fecha.strftime("%Y-%m"), fecha, total, len(jugadores),
        blancas, negras, tablas, promedio_movimientos,
    )]

    # 4) resultados_por_apertura: una fila por código ECO
    por_eco = defaultdict(list)
    for p in partidas:
        por_eco[p["codigo_eco"]].append(p)
    filas_apertura = [
        (eco, fecha, grupo[-1]["nombre_apertura"], *_resultados(grupo))
        for eco, grupo in sorted(por_eco.items())
    ]

    # 5) actividad_por_jugador: una fila por jugador (cada partida cuenta para los dos)
    actividad = defaultdict(lambda: {"partidas": 0, "victorias": 0, "derrotas": 0, "tablas": 0, "rating": None})
    for p in partidas:
        for color, jugador, rating in (
            ("blancas", p["jugador_blancas"], p["rating_blancas"]),
            ("negras", p["jugador_negras"], p["rating_negras"]),
        ):
            a = actividad[jugador]
            a["partidas"] += 1
            if p["ganador"] == "tablas":
                a["tablas"] += 1
            elif p["ganador"] == color:
                a["victorias"] += 1
            else:
                a["derrotas"] += 1
            a["rating"] = rating  # en orden cronológico, queda el de la última partida
    filas_actividad = [
        (jugador, fecha, a["partidas"], a["victorias"], a["derrotas"], a["tablas"], a["rating"])
        for jugador, a in sorted(actividad.items())
    ]

    return {
        TABLA_PARTIDAS_POR_DIA: filas_por_dia,
        TABLA_RESUMEN_DIARIO: filas_resumen,
        TABLA_RESULTADOS_POR_APERTURA: filas_apertura,
        TABLA_ACTIVIDAD_POR_JUGADOR: filas_actividad,
    }


# ---------------------------------------------------------------------------
# Escritura
# ---------------------------------------------------------------------------

def _escribir(sesion, sentencia, filas: list[tuple]) -> None:
    """Ejecuta `sentencia` para cada fila en paralelo; falla si alguna escritura falla."""
    if filas:
        execute_concurrent_with_args(sesion, sentencia, filas, concurrency=CONCURRENCIA, raise_on_first_error=True)


def recalcular_dia(sesion, fecha: date, sentencias: dict) -> None:
    """Lee la partición `fecha` de partidas_por_fecha y reescribe sus agregados."""
    partidas = list(sesion.execute(sentencias["leer_dia"], (fecha,)))
    for tabla, filas in calcular_agregados(fecha, partidas).items():
        _escribir(sesion, sentencias[tabla], filas)


def cargar_en_cassandra(ruta_limpia: str) -> int:
    """FUNCIÓN DEL CONTRATO. Devuelve cuántas partidas se escribieron en partidas_por_fecha."""
    registros = leer_registros(ruta_limpia)

    sesion = obtener_cassandra(usar_keyspace=False)
    try:
        crear_esquema(sesion)  # deja la sesión en el keyspace
        sesion.row_factory = dict_factory

        sentencias = {
            "insertar": sesion.prepare(CQL_INSERTAR_PARTIDA),
            "leer_dia": sesion.prepare(CQL_LEER_DIA),
            TABLA_PARTIDAS_POR_DIA: sesion.prepare(CQL_PARTIDAS_POR_DIA),
            TABLA_RESUMEN_DIARIO: sesion.prepare(CQL_RESUMEN_DIARIO),
            TABLA_RESULTADOS_POR_APERTURA: sesion.prepare(CQL_RESULTADOS_POR_APERTURA),
            TABLA_ACTIVIDAD_POR_JUGADOR: sesion.prepare(CQL_ACTIVIDAD_POR_JUGADOR),
        }

        # 1) Partidas (upsert por clave primaria)
        _escribir(sesion, sentencias["insertar"], [_a_fila_partida(r) for r in registros])

        # 2) Agregados de cada fecha del lote, recalculados sobre la partición completa
        fechas = sorted({date.fromisoformat(r["fecha"]) for r in registros})
        for fecha in fechas:
            recalcular_dia(sesion, fecha, sentencias)
    finally:
        sesion.cluster.shutdown()

    print(
        f"Cassandra: {len(registros)} partidas en {TABLA_PARTIDAS_POR_FECHA}; "
        f"agregados recalculados para {len(fechas)} fechas"
    )
    return len(registros)


if __name__ == "__main__":
    cargar_en_cassandra(str(cfg.DIR_MUESTRA / "partidas_limpias.jsonl"))
