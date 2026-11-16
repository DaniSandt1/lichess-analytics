"""DAG principal: Lichess -> MongoDB -> Cassandra + Neo4j -> KPIs.

Responsable: Coordinador (infraestructura y Airflow).

Cada tarea solo importa y llama a la función del contrato de su integrante. Los imports
van DENTRO de cada tarea: si el módulo de alguien tiene un error, falla solo su tarea
y el DAG se sigue viendo en Airflow.

Etapas que pide el enunciado:
  1. extraer            -> extraccion.extraer.extraer_partidas            (Integrante 1)
  2. validar_y_limpiar  -> extraccion.limpieza.validar_y_limpiar          (Integrante 1)
  3. cargar_mongo       -> carga_mongo.cargar.cargar_en_mongo             (Integrante 1)
  4. cargar_cassandra   -> carga_cassandra.cargar.cargar_en_cassandra     (Integrante 2)
  5. construir_grafo    -> carga_neo4j.cargar.construir_grafo_neo4j       (Integrante 3)
  6. calcular_kpis      -> kpis.calcular.calcular_kpis                    (Integrante 4)
"""

from datetime import datetime, timedelta

from airflow.decorators import dag, task


@dag(
    dag_id="pipeline_lichess",
    description="Extrae partidas de Lichess y las carga en MongoDB, Cassandra y Neo4j",
    schedule="@daily",
    start_date=datetime(2026, 11, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=2)},
    tags=["lichess", "bigdata"],
)
def pipeline_lichess():
    @task
    def extraer(data_interval_start=None, data_interval_end=None) -> str:
        from extraccion.extraer import extraer_partidas

        return extraer_partidas(data_interval_start, data_interval_end)

    @task
    def validar_y_limpiar(ruta_cruda: str) -> str:
        from extraccion.limpieza import validar_y_limpiar as limpiar

        return limpiar(ruta_cruda)

    @task
    def cargar_mongo(ruta_cruda: str, ruta_limpia: str) -> int:
        from carga_mongo.cargar import cargar_en_mongo

        return cargar_en_mongo(ruta_cruda, ruta_limpia)

    @task
    def cargar_cassandra(ruta_limpia: str) -> int:
        from carga_cassandra.cargar import cargar_en_cassandra

        return cargar_en_cassandra(ruta_limpia)

    @task
    def construir_grafo(ruta_limpia: str) -> int:
        from carga_neo4j.cargar import construir_grafo_neo4j

        return construir_grafo_neo4j(ruta_limpia)

    @task
    def calcular_kpis(ds=None) -> dict:
        from kpis.calcular import calcular_kpis as calcular

        return calcular(ds)

    ruta_cruda = extraer()
    ruta_limpia = validar_y_limpiar(ruta_cruda)
    en_mongo = cargar_mongo(ruta_cruda, ruta_limpia)
    en_cassandra = cargar_cassandra(ruta_limpia)
    en_neo4j = construir_grafo(ruta_limpia)

    # Mongo primero (guarda el original); luego Cassandra y Neo4j; al final los KPIs.
    en_mongo >> [en_cassandra, en_neo4j] >> calcular_kpis()


pipeline_lichess()
