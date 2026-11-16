"""CRUD de MongoDB para la demostración en el video.

Responsable: Integrante 1.

Ejecutar desde la raíz del repositorio (con Mongo levantado):
    python -m carga_mongo.crud

Muestra en consola las cuatro operaciones sobre la colección `partidas`.
"""

import json
from datetime import datetime, timezone

from comun import configuracion as cfg
from comun.conexiones import obtener_mongo
from comun.contrato import COLECCION_PARTIDAS

_db = None


def _partidas():
    global _db
    if _db is None:
        _db = obtener_mongo()
    return _db[COLECCION_PARTIDAS]


def crear_partida(documento: dict) -> str:
    """Crear documento. Devuelve el _id insertado."""
    documento = {**documento, "_id": documento.get("_id", documento.get("id"))}
    return _partidas().insert_one(documento).inserted_id


def consultar_partida(id_partida: str) -> dict | None:
    """Consultar documento por _id."""
    return _partidas().find_one({"_id": id_partida})


def actualizar_partida(id_partida: str, cambios: dict) -> int:
    """Actualizar documento ($set). Devuelve cuántos se modificaron."""
    return _partidas().update_one({"_id": id_partida}, {"$set": cambios}).modified_count


def eliminar_partida(id_partida: str) -> int:
    """Eliminar documento. Devuelve cuántos se eliminaron."""
    return _partidas().delete_one({"_id": id_partida}).deleted_count


def _resumen(doc: dict | None) -> str:
    if doc is None:
        return "  (no existe)"
    blancas = doc["players"]["white"]["user"]["name"]
    negras = doc["players"]["black"]["user"]["name"]
    extra = {k: v for k, v in doc.items() if k in ("estado_demo", "nota")}
    return (f"  _id={doc['_id']}  {blancas} vs {negras}  {doc['speed']}  "
            f"{doc['opening']['eco']} {doc['opening']['name']}  status={doc['status']}  {extra}")


if __name__ == "__main__":
    # Se toma una partida real de la muestra y se le cambia el id para no tocar los datos cargados
    with open(cfg.DIR_MUESTRA / "partidas_crudas.jsonl", encoding="utf-8") as archivo:
        original = next(d for d in map(json.loads, archivo) if d.get("variant") == "standard" and "opening" in d)
    id_demo = "demo" + original["id"]
    eliminar_partida(id_demo)  # por si quedó de una demo anterior

    print(f"Demo CRUD sobre la colección '{COLECCION_PARTIDAS}'\n")

    nuevo = {**original, "id": id_demo, "_id": id_demo, "_cargado_en": datetime.now(timezone.utc), "_lote": "demo"}
    print(f"1. CREATE  insert_one -> _id = {crear_partida(nuevo)}")
    print("2. READ    find_one")
    print(_resumen(consultar_partida(id_demo)))

    n = actualizar_partida(id_demo, {"nota": "partida revisada en la demo", "estado_demo": "actualizada"})
    print(f"3. UPDATE  update_one $set -> {n} modificado")
    print(_resumen(consultar_partida(id_demo)))

    n = eliminar_partida(id_demo)
    print(f"4. DELETE  delete_one -> {n} eliminado")
    print(_resumen(consultar_partida(id_demo)))

    total = _partidas().count_documents({})
    print(f"\nPartidas en la colección: {total}")
    _db.client.close()
