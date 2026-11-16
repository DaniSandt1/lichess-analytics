"""Crea la base `lichess`, sus colecciones e índices en MongoDB (CONTRATO.md, sección 2).

Responsable: Integrante 1.

Ejecutar desde la raíz del repositorio:
    python -m carga_mongo.crear_indices

También lo llama cargar_en_mongo al inicio. create_collection y create_index no hacen nada
si ya existen, así que se puede ejecutar las veces que se quiera.
"""

from pymongo import ASCENDING, DESCENDING

from comun.conexiones import obtener_mongo
from comun.contrato import COLECCION_JUGADORES, COLECCION_PARTIDAS

INDICES_PARTIDAS = [
    [("createdAt", DESCENDING)],
    [("players.white.user.id", ASCENDING)],
    [("players.black.user.id", ASCENDING)],
    [("opening.eco", ASCENDING)],
]


def crear_indices(db) -> None:
    existentes = set(db.list_collection_names())
    for coleccion in (COLECCION_PARTIDAS, COLECCION_JUGADORES):
        if coleccion not in existentes:
            db.create_collection(coleccion)
    for claves in INDICES_PARTIDAS:
        db[COLECCION_PARTIDAS].create_index(claves)


if __name__ == "__main__":
    db = obtener_mongo()
    crear_indices(db)
    for coleccion in (COLECCION_PARTIDAS, COLECCION_JUGADORES):
        nombres = [i["name"] for i in db[coleccion].list_indexes()]
        print(f"{db.name}.{coleccion}: índices {nombres}")
    db.client.close()
