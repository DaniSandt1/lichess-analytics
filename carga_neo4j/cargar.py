
"""Carga de partidas limpias al grafo Neo4j.

Integrante 3 - Proyecto Big Data Lichess.
"""

import json

from comun.conexiones import obtener_neo4j
from comun.contrato import validar_registro


CONSULTA_CARGA = """
UNWIND $partidas AS r

// Comprobar si la partida ya existía
OPTIONAL MATCH (existente:Partida {id: r.id_partida})
WITH r, existente IS NULL AS es_nueva

// Crear o encontrar los jugadores
MERGE (blancas:Jugador {id: r.jugador_blancas})
SET blancas.nombre = r.nombre_blancas,
    blancas.titulo = r.titulo_blancas

MERGE (negras:Jugador {id: r.jugador_negras})
SET negras.nombre = r.nombre_negras,
    negras.titulo = r.titulo_negras

// Crear o encontrar la partida
MERGE (partida:Partida {id: r.id_partida})
SET partida.fecha = date(r.fecha),
    partida.ritmo = r.ritmo,
    partida.ganador = r.ganador,
    partida.estado = r.estado,
    partida.cantidad_movimientos = r.cantidad_movimientos

// Crear o encontrar la apertura
MERGE (apertura:Apertura {codigo_eco: r.codigo_eco})
SET apertura.nombre = r.nombre_apertura,
    apertura.familia = r.familia_apertura

// Relacionar jugadores con la partida
MERGE (blancas)-[rb:JUEGA_BLANCAS]->(partida)
SET rb.rating = r.rating_blancas,
    rb.dif_rating = r.dif_rating_blancas

MERGE (negras)-[rn:JUEGA_NEGRAS]->(partida)
SET rn.rating = r.rating_negras,
    rn.dif_rating = r.dif_rating_negras

// Relacionar partida con apertura
MERGE (partida)-[:USA_APERTURA]->(apertura)

// Ordenar los jugadores alfabéticamente
WITH r, blancas, negras, es_nueva,
     CASE WHEN blancas.id < negras.id
          THEN blancas ELSE negras END AS menor,
     CASE WHEN blancas.id < negras.id
          THEN negras ELSE blancas END AS mayor

// Actualizar enfrentamientos solo para partidas nuevas
FOREACH (ignorar IN CASE WHEN es_nueva THEN [1] ELSE [] END |
    MERGE (menor)-[e:ENFRENTO]->(mayor)
    ON CREATE SET e.veces = 0
    SET e.veces = e.veces + 1,
        e.ultima_fecha =
            CASE
                WHEN e.ultima_fecha IS NULL
                     OR e.ultima_fecha < date(r.fecha)
                THEN date(r.fecha)
                ELSE e.ultima_fecha
            END
)
"""


def _cargar_lote(tx, partidas):
    """Ejecuta la carga de un lote en una transacción."""
    tx.run(CONSULTA_CARGA, partidas=partidas).consume()


def construir_grafo_neo4j(ruta_limpia: str) -> int:
    """Carga el JSONL limpio y devuelve las partidas procesadas."""
    total = 0
    lote = []
    tamano_lote = 500

    with obtener_neo4j() as driver:
        with driver.session() as session:
            with open(ruta_limpia, "r", encoding="utf-8") as archivo:
                for linea in archivo:
                    if not linea.strip():
                        continue

                    partida = json.loads(linea)
                    validar_registro(partida)
                    lote.append(partida)

                    if len(lote) >= tamano_lote:
                        session.execute_write(_cargar_lote, lote)
                        total += len(lote)
                        lote = []

                if lote:
                    session.execute_write(_cargar_lote, lote)
                    total += len(lote)

    print(f"Partidas procesadas en Neo4j: {total}")
    return total


if __name__ == "__main__":
    construir_grafo_neo4j(
        "datos/muestra/partidas_limpias.jsonl"
    )