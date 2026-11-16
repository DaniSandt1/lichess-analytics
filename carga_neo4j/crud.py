
"""CRUD de Neo4j para la demostración del proyecto Lichess.

Ejecutar desde la raíz:
    python -m carga_neo4j.crud
"""

from comun.conexiones import obtener_neo4j


def crear_jugador(id_jugador: str, nombre: str, titulo: str | None = None) -> None:
    """CREATE: crear o encontrar un jugador."""
    consulta = """
    MERGE (j:Jugador {id: $id})
    SET j.nombre = $nombre,
        j.titulo = $titulo
    """
    with obtener_neo4j() as driver:
        with driver.session() as session:
            session.run(
                consulta, id=id_jugador,
                nombre=nombre, titulo=titulo
            ).consume()


def consultar_jugador(id_jugador: str) -> dict | None:
    """READ: consultar un jugador por ID."""
    consulta = """
    MATCH (j:Jugador {id: $id})
    RETURN j.id AS id, j.nombre AS nombre,
           j.titulo AS titulo
    """
    with obtener_neo4j() as driver:
        with driver.session() as session:
            resultado = session.run(consulta, id=id_jugador).single()
            return dict(resultado) if resultado else None


def crear_enfrentamiento(id_a: str, id_b: str) -> None:
    """CREATE: crear relación entre dos jugadores existentes."""
    if id_a == id_b:
        raise ValueError("Los jugadores deben ser diferentes")

    menor, mayor = sorted([id_a, id_b])

    consulta = """
    MATCH (a:Jugador {id: $menor})
    MATCH (b:Jugador {id: $mayor})
    MERGE (a)-[r:ENFRENTO]->(b)
    ON CREATE SET r.veces = 1,
                  r.ultima_fecha = date()
    """
    with obtener_neo4j() as driver:
        with driver.session() as session:
            session.run(
                consulta, menor=menor, mayor=mayor
            ).consume()


def actualizar_jugador(id_jugador: str, propiedades: dict) -> None:
    """UPDATE: modificar propiedades de un jugador."""
    if "id" in propiedades:
        raise ValueError("No se puede modificar el ID del jugador")

    consulta = """
    MATCH (j:Jugador {id: $id})
    SET j += $propiedades
    """
    with obtener_neo4j() as driver:
        with driver.session() as session:
            session.run(
                consulta,
                id=id_jugador,
                propiedades=propiedades
            ).consume()


def eliminar_enfrentamiento(id_a: str, id_b: str) -> None:
    """DELETE: eliminar una relación ENFRENTO."""
    menor, mayor = sorted([id_a, id_b])

    consulta = """
    MATCH (a:Jugador {id: $menor})
          -[r:ENFRENTO]->
          (b:Jugador {id: $mayor})
    DELETE r
    """
    with obtener_neo4j() as driver:
        with driver.session() as session:
            session.run(
                consulta, menor=menor, mayor=mayor
            ).consume()


def eliminar_jugador(id_jugador: str) -> None:
    """DELETE: eliminar nodo y todas sus relaciones."""
    consulta = """
    MATCH (j:Jugador {id: $id})
    DETACH DELETE j
    """
    with obtener_neo4j() as driver:
        with driver.session() as session:
            session.run(consulta, id=id_jugador).consume()


def demostracion():
    """Ejecutar las operaciones CRUD con datos de prueba."""
    id_a = "demo_neo4j_a"
    id_b = "demo_neo4j_b"

    print("\n=== DEMOSTRACION CRUD NEO4J ===")

    try:
        print("\n1. CREATE: Crear jugadores")
        crear_jugador(id_a, "Jugador Demo A", "GM")
        crear_jugador(id_b, "Jugador Demo B", "FM")

        print("\n2. READ: Consultar jugador")
        print(consultar_jugador(id_a))

        print("\n3. CREATE: Crear enfrentamiento")
        crear_enfrentamiento(id_a, id_b)
        print("Relacion ENFRENTO creada")

        print("\n4. UPDATE: Actualizar jugador")
        actualizar_jugador(
            id_a, {"nombre": "Jugador Actualizado", "titulo": "IM"}
        )
        print(consultar_jugador(id_a))

        print("\n5. DELETE: Eliminar enfrentamiento")
        eliminar_enfrentamiento(id_a, id_b)
        print("Relacion eliminada")

    finally:
        print("\n6. DELETE: Eliminar jugadores de prueba")
        eliminar_jugador(id_a)
        eliminar_jugador(id_b)
        print("Jugadores de prueba eliminados")

    print("\n=== CRUD FINALIZADO ===")


if __name__ == "__main__":
    demostracion()