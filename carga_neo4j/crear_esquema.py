"""Crea en Neo4j las constraints de unicidad de esquema.cypher (CONTRATO.md, sección 4).

Responsable: Integrante 3.

Ejecutar desde la raíz del repositorio:
    python -m carga_neo4j.crear_esquema

También lo llama construir_grafo_neo4j al inicio, como hacen Mongo y Cassandra, así el DAG
funciona en una base vacía sin pasos manuales. Todo usa IF NOT EXISTS: ejecutarlo dos veces
no hace nada.

Las constraints son necesarias para el rendimiento, no solo para la unicidad: cada una crea
un índice. Sin ellas, cada MERGE de Jugador o Partida recorre todos los nodos de esa etiqueta
y la carga de ~55,000 partidas puede tardar horas.
"""

import re
from pathlib import Path

from comun.conexiones import obtener_neo4j

RUTA_ESQUEMA = Path(__file__).resolve().parent / "esquema.cypher"
ESPERA_INDICES_SEG = 300


def leer_sentencias(ruta: Path = RUTA_ESQUEMA) -> list[str]:
    """Devuelve las sentencias Cypher del archivo, sin comentarios ni líneas vacías."""
    texto = ruta.read_text(encoding="utf-8")
    texto = re.sub(r"/\*.*?\*/", "", texto, flags=re.DOTALL)  # comentarios /* ... */
    texto = re.sub(r"//[^\n]*", "", texto)                     # comentarios // ...
    return [s.strip() for s in texto.split(";") if s.strip()]


def crear_esquema(driver=None) -> None:
    """Ejecuta esquema.cypher y espera a que los índices queden listos.

    Si recibe un driver lo reutiliza; si no, abre y cierra uno propio.
    """
    propio = driver is None
    if propio:
        driver = obtener_neo4j()
    try:
        with driver.session() as sesion:
            for sentencia in leer_sentencias():
                sesion.run(sentencia).consume()
            # Si la base ya tenía datos, el índice se llena en segundo plano: hay que esperarlo
            # antes de cargar, o los MERGE seguirían recorriendo todos los nodos.
            sesion.run(f"CALL db.awaitIndexes({ESPERA_INDICES_SEG})").consume()
    finally:
        if propio:
            driver.close()


if __name__ == "__main__":
    crear_esquema()
    print(f"Esquema listo: {len(leer_sentencias())} constraints en Neo4j")
