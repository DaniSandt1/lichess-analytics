"""CRUD de Cassandra para la demostración en el video.

Responsable: Integrante 2.
Estado: PLANTILLA.

Ejecutar:  python -m carga_cassandra.crud
Sugerencia: hacer la demo sobre actividad_por_jugador (clave ((jugador), fecha)).
"""

from comun.conexiones import obtener_cassandra  # noqa: F401


def insertar_actividad(jugador: str, fecha: str, datos: dict) -> None:
    """Inserción."""
    raise NotImplementedError("Integrante 2")


def consultar_actividad(jugador: str) -> list[dict]:
    """Consulta: todas las fechas de un jugador (una sola partición)."""
    raise NotImplementedError("Integrante 2")


def actualizar_actividad(jugador: str, fecha: str, cambios: dict) -> None:
    """Actualización (UPDATE ... WHERE jugador = ? AND fecha = ?)."""
    raise NotImplementedError("Integrante 2")


def eliminar_actividad(jugador: str, fecha: str) -> None:
    """Eliminación."""
    raise NotImplementedError("Integrante 2")


if __name__ == "__main__":
    print("PENDIENTE (Integrante 2)")
