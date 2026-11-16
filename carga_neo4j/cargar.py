"""Construcción del grafo en Neo4j.

Responsable: Integrante 3.
Estado: PLANTILLA.

Qué tiene que hacer (CONTRATO.md, sección 4):
- carga_neo4j/esquema.cypher: las 3 constraints de unicidad del contrato.
- construir_grafo_neo4j: por cada registro limpio (en lotes de ~500 con UNWIND):
    MERGE de los dos (:Jugador), la (:Partida) y la (:Apertura),
    las relaciones JUEGA_BLANCAS, JUEGA_NEGRAS y USA_APERTURA,
    y ENFRENTO entre los dos jugadores sumando 1 a `veces` SOLO si la Partida es nueva
    (ON CREATE), para que reejecutar el mismo lote no infle el conteo.
- carga_neo4j/consultas.cypher: las consultas que usa el dashboard (jugador con más rivales,
  apertura que conecta más jugadores, subgrafo de enfrentamientos para pyvis).
"""

from comun.contrato import NODO_APERTURA, NODO_JUGADOR, NODO_PARTIDA


def construir_grafo_neo4j(ruta_limpia: str) -> int:
    """FUNCIÓN DEL CONTRATO. Devuelve cuántas partidas se procesaron."""
    print(f"[PENDIENTE - Integrante 3] construir_grafo_neo4j({ruta_limpia}) -> "
          f"{NODO_JUGADOR}, {NODO_PARTIDA}, {NODO_APERTURA}")
    return 0
