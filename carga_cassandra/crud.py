"""CRUD de Cassandra para la demostración en el video.

Responsable: Integrante 2.

Ejecutar desde la raíz del repositorio (con Cassandra levantada):
    python -m carga_cassandra.crud

Trabaja sobre actividad_por_jugador, cuya clave es ((jugador), fecha): todas las operaciones
van a una sola partición (la del jugador) y a una fila concreta (la fecha).
"""

from datetime import date

from cassandra.query import dict_factory

from carga_cassandra.crear_esquema import crear_esquema
from comun.conexiones import obtener_cassandra
from comun.contrato import TABLA_ACTIVIDAD_POR_JUGADOR as TABLA

# Columnas que se pueden escribir (además de la clave). Los nombres de columna no se pueden
# pasar como parámetros en CQL, así que se validan contra esta lista antes de armar la sentencia.
COLUMNAS = ("partidas", "victorias", "derrotas", "tablas", "rating_ultimo")

_sesion = None


def _obtener_sesion():
    """Una sola sesión para toda la demo, con el esquema creado y filas como dict."""
    global _sesion
    if _sesion is None:
        _sesion = obtener_cassandra(usar_keyspace=False)
        crear_esquema(_sesion)
        _sesion.row_factory = dict_factory
    return _sesion


def _validar_columnas(datos: dict) -> list[str]:
    desconocidas = set(datos) - set(COLUMNAS)
    if desconocidas:
        raise ValueError(f"Columnas no válidas: {sorted(desconocidas)}. Permitidas: {COLUMNAS}")
    return list(datos)


def insertar_actividad(jugador: str, fecha: str, datos: dict) -> None:
    """Inserción: una fila (jugador, fecha). Si ya existía, la sobrescribe (upsert)."""
    columnas = _validar_columnas(datos)
    cql = (
        f"INSERT INTO {TABLA} (jugador, fecha, {', '.join(columnas)}) "
        f"VALUES (%s, %s{', %s' * len(columnas)})"
    )
    _obtener_sesion().execute(cql, (jugador, date.fromisoformat(fecha), *datos.values()))


def consultar_actividad(jugador: str) -> list[dict]:
    """Consulta: todas las fechas de un jugador (una sola partición), de la más reciente a la más antigua."""
    filas = _obtener_sesion().execute(f"SELECT * FROM {TABLA} WHERE jugador = %s", (jugador,))
    # fecha llega como cassandra.util.Date; se pasa a texto para que se lea bien en la demo
    return [{**fila, "fecha": str(fila["fecha"])} for fila in filas]


def actualizar_actividad(jugador: str, fecha: str, cambios: dict) -> None:
    """Actualización (UPDATE ... WHERE jugador = ? AND fecha = ?)."""
    columnas = _validar_columnas(cambios)
    if not columnas:
        return
    asignaciones = ", ".join(f"{c} = %s" for c in columnas)
    cql = f"UPDATE {TABLA} SET {asignaciones} WHERE jugador = %s AND fecha = %s"
    _obtener_sesion().execute(cql, (*cambios.values(), jugador, date.fromisoformat(fecha)))


def eliminar_actividad(jugador: str, fecha: str) -> None:
    """Eliminación de una fila concreta (DELETE ... WHERE jugador = ? AND fecha = ?)."""
    cql = f"DELETE FROM {TABLA} WHERE jugador = %s AND fecha = %s"
    _obtener_sesion().execute(cql, (jugador, date.fromisoformat(fecha)))


def _mostrar(titulo: str, filas: list[dict]) -> None:
    print(f"\n--- {titulo} ---")
    if not filas:
        print("  (sin filas)")
    for fila in filas:
        print(f"  {fila}")


if __name__ == "__main__":
    jugador, fecha = "jugador_demo", "2026-11-16"

    print(f"Demo CRUD sobre {TABLA} (clave ((jugador), fecha))")

    insertar_actividad(jugador, fecha, {"partidas": 5, "victorias": 3, "derrotas": 1, "tablas": 1, "rating_ultimo": 2500})
    insertar_actividad(jugador, "2026-11-15", {"partidas": 2, "victorias": 0, "derrotas": 2, "tablas": 0, "rating_ultimo": 2490})
    _mostrar("1. INSERT: dos fechas del jugador", consultar_actividad(jugador))

    actualizar_actividad(jugador, fecha, {"partidas": 6, "victorias": 4, "rating_ultimo": 2508})
    _mostrar(f"2. UPDATE: {fecha} gana una partida más", consultar_actividad(jugador))

    eliminar_actividad(jugador, "2026-11-15")
    _mostrar("3. DELETE: se elimina la fila del 2026-11-15", consultar_actividad(jugador))

    eliminar_actividad(jugador, fecha)
    _mostrar("4. DELETE: se elimina la última fila (la partición queda vacía)", consultar_actividad(jugador))

    _mostrar("Consulta de un jugador real cargado desde la muestra (realdavidnavara)", consultar_actividad("realdavidnavara")[:5])

    _sesion.cluster.shutdown()
