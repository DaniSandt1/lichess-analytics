"""Comprueba que las tres bases de datos responden con la configuración del .env.

Ejecutar desde la raíz del repositorio, con los contenedores levantados:
    python -m scripts.verificar_entorno
"""

from comun import configuracion as cfg
from comun.conexiones import obtener_cassandra, obtener_mongo, obtener_neo4j


def probar(nombre, funcion):
    try:
        detalle = funcion()
        print(f"  OK     {nombre}: {detalle}")
        return True
    except Exception as error:  # noqa: BLE001 - queremos ver cualquier fallo
        print(f"  FALLA  {nombre}: {type(error).__name__}: {error}")
        return False


def _mongo():
    db = obtener_mongo()
    version = db.client.server_info()["version"]
    return f"MongoDB {version} en {cfg.MONGO_HOST}:{cfg.MONGO_PORT}, base '{cfg.MONGO_DB}'"


def _cassandra():
    sesion = obtener_cassandra(usar_keyspace=False)
    version = sesion.execute("SELECT release_version FROM system.local").one().release_version
    sesion.cluster.shutdown()
    return f"Cassandra {version} en {cfg.CASSANDRA_HOSTS}:{cfg.CASSANDRA_PORT}"


def _neo4j():
    with obtener_neo4j() as driver:
        driver.verify_connectivity()
        registros, _, _ = driver.execute_query("CALL dbms.components() YIELD versions RETURN versions[0] AS v")
        return f"Neo4j {registros[0]['v']} en {cfg.NEO4J_URI}"


if __name__ == "__main__":
    print("Verificando conexiones...")
    resultados = [probar("MongoDB", _mongo), probar("Cassandra", _cassandra), probar("Neo4j", _neo4j)]
    print("Todo listo." if all(resultados) else "Hay bases que no responden: revisen 'docker compose ps'.")
