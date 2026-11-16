"""CRUD de MongoDB para la demostración en el video.

Responsable: Integrante 1.
Estado: PLANTILLA.

Ejecutar:  python -m carga_mongo.crud
Debe mostrar en consola las cuatro operaciones sobre la colección `partidas`.
"""

from comun.conexiones import obtener_mongo  # noqa: F401  (úsenlo dentro de cada función)


def crear_partida(documento: dict) -> str:
    """Crear documento. Devuelve el _id insertado."""
    raise NotImplementedError("Integrante 1")


def consultar_partida(id_partida: str) -> dict | None:
    """Consultar documento por _id."""
    raise NotImplementedError("Integrante 1")


def actualizar_partida(id_partida: str, cambios: dict) -> int:
    """Actualizar documento ($set). Devuelve cuántos se modificaron."""
    raise NotImplementedError("Integrante 1")


def eliminar_partida(id_partida: str) -> int:
    """Eliminar documento. Devuelve cuántos se eliminaron."""
    raise NotImplementedError("Integrante 1")


if __name__ == "__main__":
    # Demo: crear -> consultar -> actualizar -> consultar -> eliminar -> consultar
    print("PENDIENTE (Integrante 1)")
