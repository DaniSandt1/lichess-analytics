"""Carga en MongoDB.

Responsable: Integrante 1.

Cómo funciona (CONTRATO.md, sección 2):
- Colección `partidas`: el documento CRUDO de cada partida que pasó la limpieza (sus ids están
  en ruta_limpia), con _id = id de la partida, más _cargado_en y _lote. Se usa upsert
  (ReplaceOne con upsert=True), así reejecutar el lote no duplica.
- Colección `jugadores`: un documento por jugador del lote, RECALCULADO con una agregación sobre
  `partidas` y escrito con $merge. Como sale de los datos ya guardados, reejecutar no infla
  total_partidas.
- Colecciones e índices de CONTRATO.md con crear_indices.py (no hace nada si ya existen).

Probar con la muestra, sin Airflow:
    python -m carga_mongo.cargar
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from pymongo import ReplaceOne

from carga_mongo.crear_indices import crear_indices
from comun import configuracion as cfg
from comun.conexiones import obtener_mongo
from comun.contrato import COLECCION_JUGADORES, COLECCION_PARTIDAS

TAMANO_LOTE = 1000


def _ids_limpios(ruta_limpia: str) -> set[str]:
    with open(ruta_limpia, encoding="utf-8") as archivo:
        return {json.loads(linea)["id_partida"] for linea in archivo if linea.strip()}


def _cargar_partidas(db, ruta_cruda: str, ids: set[str]) -> tuple[int, set[str]]:
    """Upsert de los documentos crudos cuyos ids están en `ids`. Devuelve (cargadas, jugadores)."""
    coleccion = db[COLECCION_PARTIDAS]
    lote = Path(ruta_cruda).name
    ahora = datetime.now(timezone.utc)
    vistos, jugadores, operaciones = set(), set(), []

    with open(ruta_cruda, encoding="utf-8") as archivo:
        for linea in archivo:
            if not linea.strip():
                continue
            documento = json.loads(linea)
            id_partida = documento.get("id")
            # Solo partidas que pasaron la limpieza, y cada una una vez
            # (una partida entre dos jugadores de la lista aparece dos veces en el crudo)
            if id_partida not in ids or id_partida in vistos:
                continue
            vistos.add(id_partida)
            for color in ("white", "black"):
                jugadores.add(documento["players"][color]["user"]["id"])

            documento.update({"_id": id_partida, "_cargado_en": ahora, "_lote": lote})
            operaciones.append(ReplaceOne({"_id": id_partida}, documento, upsert=True))
            if len(operaciones) >= TAMANO_LOTE:
                coleccion.bulk_write(operaciones, ordered=False)
                operaciones = []

    if operaciones:
        coleccion.bulk_write(operaciones, ordered=False)
    return len(vistos), jugadores


def _recalcular_jugadores(db, jugadores: set[str]) -> None:
    """Reescribe en `jugadores` el resumen de cada jugador a partir de TODAS sus partidas."""
    if not jugadores:
        return
    ids = sorted(jugadores)
    tuberia = [
        {"$match": {"$or": [
            {"players.white.user.id": {"$in": ids}},
            {"players.black.user.id": {"$in": ids}},
        ]}},
        # Una fila por (partida, lado) para tratar igual a blancas y negras
        {"$project": {"createdAt": 1, "speed": 1, "lados": [
            {"usuario": "$players.white.user", "rating": "$players.white.rating"},
            {"usuario": "$players.black.user", "rating": "$players.black.rating"},
        ]}},
        {"$unwind": "$lados"},
        {"$match": {"lados.usuario.id": {"$in": ids}}},
        {"$sort": {"createdAt": 1}},
        # Último rating por ritmo
        {"$group": {
            "_id": {"jugador": "$lados.usuario.id", "ritmo": "$speed"},
            "nombre": {"$last": "$lados.usuario.name"},
            "titulo": {"$last": "$lados.usuario.title"},
            "rating": {"$last": "$lados.rating"},
            "ultima": {"$max": "$createdAt"},
            "partidas": {"$sum": 1},
        }},
        {"$sort": {"ultima": 1}},
        {"$group": {
            "_id": "$_id.jugador",
            "nombre": {"$last": "$nombre"},
            "titulo": {"$last": "$titulo"},
            "ratings": {"$push": {"k": "$_id.ritmo", "v": "$rating"}},
            "ultima": {"$max": "$ultima"},
            "total_partidas": {"$sum": "$partidas"},
        }},
        {"$project": {
            "nombre": 1,
            "titulo": {"$ifNull": ["$titulo", None]},
            "ratings": {"$arrayToObject": "$ratings"},
            "ultima_partida": {"$toDate": "$ultima"},
            "total_partidas": 1,
        }},
        {"$merge": {"into": COLECCION_JUGADORES, "whenMatched": "replace", "whenNotMatched": "insert"}},
    ]
    db[COLECCION_PARTIDAS].aggregate(tuberia, allowDiskUse=True)


def cargar_en_mongo(ruta_cruda: str, ruta_limpia: str) -> int:
    """FUNCIÓN DEL CONTRATO. Devuelve cuántas partidas se insertaron o actualizaron."""
    db = obtener_mongo()
    try:
        crear_indices(db)
        cargadas, jugadores = _cargar_partidas(db, ruta_cruda, _ids_limpios(ruta_limpia))
        _recalcular_jugadores(db, jugadores)
    finally:
        db.client.close()
    print(f"MongoDB: {cargadas} partidas en '{COLECCION_PARTIDAS}', {len(jugadores)} jugadores actualizados")
    return cargadas


if __name__ == "__main__":
    cargar_en_mongo(
        str(cfg.DIR_MUESTRA / "partidas_crudas.jsonl"),
        str(cfg.DIR_MUESTRA / "partidas_limpias.jsonl"),
    )
