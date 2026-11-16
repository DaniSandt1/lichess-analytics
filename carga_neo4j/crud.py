"""CRUD de Neo4j para la demostración en el video.

Responsable: Integrante 3.
Estado: PLANTILLA.

Ejecutar:  python -m carga_neo4j.crud
"""

from comun.conexiones import obtener_neo4j  # noqa: F401


def crear_jugador(id_jugador: str, nombre: str, titulo: str | None = None) -> None:
    """Crear nodo."""
    raise NotImplementedError("Integrante 3")


def crear_enfrentamiento(id_a: str, id_b: str) -> None:
    """Crear relación ENFRENTO entre dos jugadores."""
    raise NotImplementedError("Integrante 3")


def actualizar_jugador(id_jugador: str, propiedades: dict) -> None:
    """Actualizar propiedades (SET j += $propiedades)."""
    raise NotImplementedError("Integrante 3")


def eliminar_jugador(id_jugador: str) -> None:
    """Eliminar nodo con sus relaciones (DETACH DELETE)."""
    raise NotImplementedError("Integrante 3")


def eliminar_enfrentamiento(id_a: str, id_b: str) -> None:
    """Eliminar relación."""
    raise NotImplementedError("Integrante 3")


if __name__ == "__main__":
    print("PENDIENTE (Integrante 3)")
