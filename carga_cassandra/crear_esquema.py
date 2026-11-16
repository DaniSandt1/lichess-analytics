"""Crea el keyspace y las 6 tablas de Cassandra a partir de esquema.cql.

Responsable: Integrante 2.

Ejecutar desde la raíz del repositorio:
    python -m carga_cassandra.crear_esquema

También lo llama cargar_en_cassandra al inicio, así el DAG funciona aunque nadie lo
haya corrido antes. Todo el CQL usa IF NOT EXISTS: ejecutarlo dos veces no hace nada.
"""

from pathlib import Path

from comun import configuracion as cfg
from comun.conexiones import obtener_cassandra

RUTA_ESQUEMA = Path(__file__).resolve().parent / "esquema.cql"


def leer_sentencias(ruta: Path = RUTA_ESQUEMA) -> list[str]:
    """Devuelve las sentencias CQL del archivo, sin comentarios ni líneas vacías."""
    lineas = [
        linea for linea in ruta.read_text(encoding="utf-8").splitlines()
        if linea.strip() and not linea.strip().startswith("--")
    ]
    return [s.strip() for s in "\n".join(lineas).split(";") if s.strip()]


def crear_esquema(sesion=None) -> None:
    """Ejecuta esquema.cql. Si recibe una sesión la reutiliza y la deja en el keyspace."""
    propia = sesion is None
    if propia:
        sesion = obtener_cassandra(usar_keyspace=False)
    try:
        for sentencia in leer_sentencias():
            sesion.execute(sentencia)
        sesion.set_keyspace(cfg.CASSANDRA_KEYSPACE)
    finally:
        if propia:
            sesion.cluster.shutdown()


if __name__ == "__main__":
    crear_esquema()
    print(f"Esquema listo: keyspace '{cfg.CASSANDRA_KEYSPACE}' con {len(leer_sentencias()) - 1} tablas")
