# Modelo de grafo en Neo4j

*Sección del informe a cargo del Integrante 3. Código en [carga_neo4j/](../carga_neo4j/).*

## Por qué Neo4j

Neo4j es una base de datos orientada a grafos que permite representar entidades y sus conexiones mediante nodos y relaciones. En este proyecto se utiliza para analizar las interacciones entre jugadores de Lichess, las partidas disputadas y las aperturas utilizadas.

Se eligió Neo4j por tres motivos principales:

1. **Representación de relaciones.** Permite modelar directamente los enfrentamientos entre jugadores y asociarlos con sus partidas y aperturas.
2. **Consultas de conectividad.** El lenguaje Cypher facilita identificar jugadores con más rivales distintos, aperturas que conectan a más jugadores y redes de enfrentamientos.
3. **Visualización del grafo.** Neo4j Browser permite explorar las conexiones entre entidades y comprender las interacciones entre los jugadores.

A diferencia de MongoDB, que conserva los documentos originales de las partidas, y Cassandra, que organiza información para consultas y agregaciones temporales, Neo4j se enfoca en analizar las relaciones entre las entidades.

## Modelo del grafo

Se definieron tres tipos de nodos y cuatro tipos de relaciones.

### Nodos

| Nodo | Identificador | Propiedades principales |
|---|---|---|
| `Jugador` | `id` | `nombre`, `titulo` |
| `Partida` | `id` | `fecha`, `ritmo`, `ganador`, `estado`, `cantidad_movimientos` |
| `Apertura` | `codigo_eco` | `nombre`, `familia` |

### Relaciones

| Relación | Origen | Destino | Descripción |
|---|---|---|---|
| `JUEGA_BLANCAS` | Jugador | Partida | Identifica al jugador que utilizó las piezas blancas |
| `JUEGA_NEGRAS` | Jugador | Partida | Identifica al jugador que utilizó las piezas negras |
| `USA_APERTURA` | Partida | Apertura | Asocia una partida con su apertura |
| `ENFRENTO` | Jugador | Jugador | Resume los enfrentamientos entre dos jugadores |

Las relaciones `JUEGA_BLANCAS` y `JUEGA_NEGRAS` contienen propiedades como el rating y su variación. La relación `ENFRENTO` almacena `veces`, que representa la cantidad de partidas entre dos jugadores, y `ultima_fecha`, correspondiente a su enfrentamiento más reciente.

Los enfrentamientos se representan mediante una única relación entre cada pareja de jugadores, siguiendo un orden consistente de identificadores para evitar duplicaciones.

**Figura 1.** Visualización del grafo de enfrentamientos de RealDavidNavara.  
*Insertar captura `04_grafo.png`.*

## Restricciones de unicidad

Se implementaron tres restricciones de unicidad mediante `CREATE CONSTRAINT ... IF NOT EXISTS`:

| Constraint | Nodo | Propiedad |
|---|---|---|
| `jugador_id` | Jugador | `id` |
| `partida_id` | Partida | `id` |
| `apertura_eco` | Apertura | `codigo_eco` |

Estas restricciones garantizan que no existan dos nodos del mismo tipo con el mismo identificador y complementan el uso de `MERGE` durante la carga.

## Carga del grafo

La función `construir_grafo_neo4j(ruta_limpia)` se implementó en [carga_neo4j/cargar.py](../carga_neo4j/cargar.py).

El proceso comprende las siguientes etapas:

1. Leer el archivo JSONL de partidas limpias generado por el proceso de extracción y transformación.
2. Validar los registros mediante `validar_registro()`, definido en el contrato compartido.
3. Agrupar los registros en lotes de hasta 500 partidas.
4. Utilizar `UNWIND` para procesar las partidas de cada lote.
5. Crear o encontrar los nodos `Jugador`, `Partida` y `Apertura` mediante `MERGE`.
6. Crear las relaciones entre jugadores, partidas y aperturas.
7. Actualizar `ENFRENTO.veces` únicamente cuando se incorpora una partida nueva.

La carga se diseñó para ser **idempotente**, de manera que procesar nuevamente un mismo lote no duplique partidas ni incremente incorrectamente los enfrentamientos.

Esta propiedad es importante para la integración con Apache Airflow, dado que una tarea puede volver a ejecutarse durante un reintento.

## Consultas analíticas

Se implementaron tres consultas Cypher en [carga_neo4j/consultas.cypher](../carga_neo4j/consultas.cypher).

### Consulta 1. Jugador con más rivales distintos

Identifica al jugador que se ha enfrentado a la mayor cantidad de oponentes diferentes mediante `COUNT(DISTINCT rival)`.

**Resultado con la muestra:** `Dr_Tiger`, con 59 rivales distintos.

### Consulta 2. Apertura que conecta a más jugadores

Relaciona las aperturas con las partidas y los jugadores que participaron en ellas, contabilizando los jugadores diferentes mediante `COUNT(DISTINCT j)`.

**Resultado con la muestra:** apertura `A01`, *Nimzo-Larsen Attack*, con 11 jugadores distintos.

### Consulta 3. Subgrafo de un jugador

Obtiene los rivales de un jugador determinado y sus relaciones `ENFRENTO`, permitiendo visualizar la red de oponentes en Neo4j Browser.

Para la demostración se utilizó el jugador `realdavidnavara`.

Estas consultas muestran cómo el modelo de grafos facilita analizar conexiones entre jugadores y aperturas sin reconstruir manualmente las relaciones entre entidades.

## Operaciones CRUD

Se implementaron las operaciones CRUD en [carga_neo4j/crud.py](../carga_neo4j/crud.py), utilizando Python y el driver oficial de Neo4j.

| Operación | Instrucción Cypher | Implementación |
|---|---|---|
| Crear jugador | `MERGE` | `crear_jugador()` |
| Consultar jugador | `MATCH`, `RETURN` | `consultar_jugador()` |
| Crear enfrentamiento | `MERGE` | `crear_enfrentamiento()` |
| Actualizar jugador | `SET` | `actualizar_jugador()` |
| Eliminar enfrentamiento | `DELETE` | `eliminar_enfrentamiento()` |
| Eliminar jugador | `DETACH DELETE` | `eliminar_jugador()` |

La demostración se ejecuta desde la raíz del repositorio:

`python -m carga_neo4j.crud`

El procedimiento crea dos jugadores ficticios, consulta sus propiedades, establece un enfrentamiento, actualiza los datos de un jugador y finalmente elimina la relación y los nodos de prueba.

Al finalizar, se comprobó que no permanecieran nodos con identificadores de demostración.

## Pruebas y validación

La implementación se probó localmente utilizando `datos/muestra/partidas_limpias.jsonl`, que contiene 233 partidas válidas.

### Resultados de la carga

| Elemento | Cantidad |
|---|---:|
| Jugadores | 133 |
| Partidas | 233 |
| Aperturas | 80 |
| Relaciones `JUEGA_BLANCAS` | 233 |
| Relaciones `JUEGA_NEGRAS` | 233 |
| Relaciones `USA_APERTURA` | 233 |
| Relaciones `ENFRENTO` | 134 |

### Prueba de idempotencia

Se ejecutó nuevamente la carga utilizando el mismo archivo de 233 partidas.

Los resultados permanecieron constantes:

| Métrica | Resultado después de repetir la carga |
|---|---:|
| Partidas | 233 |
| Relaciones `ENFRENTO` | 134 |
| Suma de `ENFRENTO.veces` | 233 |

Esto confirma que la repetición del lote de prueba no produjo duplicación de partidas ni incremento incorrecto del contador de enfrentamientos.

Asimismo, se ejecutaron las consultas analíticas y la demostración CRUD sin errores.

**Figura 2.** Resultado de la prueba de idempotencia.  


**Figura 3.** Ejecución de las operaciones CRUD desde Python.  


Las pruebas descritas corresponden al dataset de muestra. La validación con la carga inicial completa y la ejecución integrada del DAG corresponden a las pruebas generales del proyecto.

## Conclusión del componente

La implementación de Neo4j permite representar y analizar las conexiones entre jugadores, partidas y aperturas de Lichess mediante un modelo de grafos.

Las consultas implementadas facilitan identificar rivales frecuentes, jugadores con mayor diversidad de oponentes y aperturas compartidas. Además, las restricciones de unicidad y la carga idempotente contribuyen a mantener la consistencia de los datos durante las ejecuciones del pipeline.

El componente fue validado con la muestra proporcionada y está preparado para su integración con los demás componentes del proyecto.