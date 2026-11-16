"""Conexiones a las tres bases de datos, para no repetir este código en cada carpeta.

    from comun.conexiones import obtener_mongo, obtener_cassandra, obtener_neo4j

    db = obtener_mongo()                     # pymongo Database
    sesion = obtener_cassandra()             # cassandra Session (ya en el keyspace si existe)
    with obtener_neo4j() as driver:          # neo4j Driver
        driver.execute_query("RETURN 1")

Los imports de cada librería están dentro de cada función: así quien solo trabaja
con Neo4j no necesita tener instalado el driver de Cassandra, y viceversa.
"""

from comun import configuracion as cfg


def obtener_mongo():
    from pymongo import MongoClient

    cliente = MongoClient(cfg.MONGO_URI, serverSelectionTimeoutMS=5000)
    return cliente[cfg.MONGO_DB]


def obtener_cassandra(usar_keyspace: bool = True):
    """Devuelve una sesión. Si el keyspace todavía no existe, la sesión queda sin keyspace."""
    from cassandra.cluster import Cluster

    cluster = Cluster(cfg.CASSANDRA_HOSTS, port=cfg.CASSANDRA_PORT)
    sesion = cluster.connect()
    if usar_keyspace:
        existe = sesion.execute(
            "SELECT keyspace_name FROM system_schema.keyspaces WHERE keyspace_name = %s",
            (cfg.CASSANDRA_KEYSPACE,),
        ).one()
        if existe:
            sesion.set_keyspace(cfg.CASSANDRA_KEYSPACE)
    return sesion


def obtener_neo4j():
    from neo4j import GraphDatabase

    return GraphDatabase.driver(cfg.NEO4J_URI, auth=(cfg.NEO4J_USER, cfg.NEO4J_PASSWORD))
