"""Carga en MongoDB.

Responsable: Integrante 1.
Estado: PLANTILLA.

Qué tiene que hacer (CONTRATO.md, sección 2):
- Colección `partidas`: guardar el documento CRUDO de cada partida que pasó la limpieza
  (los ids están en ruta_limpia), con _id = id de la partida, más _cargado_en y _lote.
  Usar upsert (replace_one(..., upsert=True) o bulk_write) para que reejecutar no duplique.
- Colección `jugadores`: un documento por jugador (_id = id en minúsculas) con nombre,
  título, último rating por ritmo, fecha de la última partida y total de partidas.
- Crear los índices de CONTRATO.md (puede ser en un carga_mongo/crear_indices.py).
"""

from comun.contrato import COLECCION_JUGADORES, COLECCION_PARTIDAS


def cargar_en_mongo(ruta_cruda: str, ruta_limpia: str) -> int:
    """FUNCIÓN DEL CONTRATO. Devuelve cuántas partidas se insertaron o actualizaron."""
    print(f"[PENDIENTE - Integrante 1] cargar_en_mongo({ruta_cruda}, {ruta_limpia})")
    print(f"[PENDIENTE - Integrante 1] colecciones: {COLECCION_PARTIDAS}, {COLECCION_JUGADORES}")
    return 0
