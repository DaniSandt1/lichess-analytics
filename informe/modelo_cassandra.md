# Modelo de datos de Cassandra

_Sección del informe a cargo de Integrante 2. Código en [carga_cassandra/](../carga_cassandra/)._

## Por qué Cassandra

Las partidas forman una **serie de tiempo** con muchas escrituras: la carga inicial (~60,000 partidas) y
luego un lote nuevo cada día. Además, el dashboard siempre consulta por una clave conocida: un día,
un mes, una apertura o un jugador. Cassandra encaja con eso por tres motivos:

1. **Escrituras baratas y sin bloqueo.** Cada `INSERT` se agrega al commit log y a una memtable, así que
   cargar decenas de miles de filas toma segundos.
2. **Modelado por consulta.** En vez de normalizar y hacer JOIN, se define una tabla por cada consulta del
   dashboard. Como la clave de partición es lo que trae el `WHERE`, cada consulta lee **una sola
   partición** de un solo nodo.
3. **Upsert natural.** Un `INSERT` con una clave primaria que ya existe sobrescribe la fila. Eso hace que
   reejecutar un lote (Airflow reintenta las tareas que fallan) no duplique datos.

La contrapartida es que la misma información se guarda varias veces (desnormalización) y que no hay
agregaciones ni JOIN en el servidor. Por eso los agregados se calculan en Python durante la carga.

## Tablas

Keyspace `lichess` con `SimpleStrategy` y `replication_factor = 1`, porque es un solo nodo en Docker.
En producción se usaría `NetworkTopologyStrategy` con factor 3.

| # | Tabla | Clave de partición | Clave de clustering | Consulta que resuelve | Quién la usa |
|---|---|---|---|---|---|
| 1 | `partidas_por_fecha` | `fecha` | `ritmo`, `id_partida` | Todas las partidas de un día, agrupadas por ritmo | Base para recalcular las tablas 2 a 5; KPI `apertura_top` |
| 2 | `partidas_por_dia` | `fecha` | `ritmo` | Total y resultados de un día por ritmo (bullet, blitz, rapid, classical) | Dashboard |
| 3 | `resumen_diario` | `anio_mes` | `fecha DESC` | Tendencia diaria de un mes: partidas, jugadores activos, resultados, promedio de jugadas | KPIs y gráfico de tendencia |
| 4 | `resultados_por_apertura` | `codigo_eco` | `fecha DESC` | Historial día a día de una apertura (ej. `B90`) | Dashboard |
| 5 | `actividad_por_jugador` | `jugador` | `fecha DESC` | Actividad diaria de un jugador: partidas, victorias, derrotas, tablas, último rating | Dashboard; demo del CRUD |
| 6 | `kpis_por_fecha` | `fecha` | `kpi` | Los 6 KPIs de un día | Dashboard (la llena Integrante 4) |

Decisiones de diseño:

- **`partidas_por_fecha` incluye `id_partida` en la clave.** Así cada partida es una fila única y, como
  `ritmo` va antes, las filas de la partición quedan ordenadas por ritmo.
- **`resumen_diario` se particiona por mes, no por día.** Un gráfico de tendencia necesita ~30 días
  seguidos. Con la partición por mes los lee de una sola vez y ya ordenados (`CLUSTERING ORDER BY
  (fecha DESC)`). Una partición por año también serviría, pero por mes las particiones se mantienen
  pequeñas y acotadas.
- **Tablas 4 y 5 con `fecha DESC`.** Lo más reciente sale primero, que es lo que quiere el dashboard,
  y `LIMIT n` devuelve los últimos `n` días sin ordenar en el cliente.
- **Sin columnas `counter`.** Un contador se incrementa en cada reintento y no hay forma de saber si
  ya se sumó. Las tablas 2 a 5 usan `int` normales que se **recalculan** completos.
- **Particiones acotadas.** La partición más grande es un día de `partidas_por_fecha`. Con ~40
  jugadores top son a lo sumo unos miles de filas, muy por debajo de los ~100 MB que se recomiendan
  como máximo por partición.

## Cómo se carga (idempotente)

`cargar_en_cassandra(ruta_limpia)` en [carga_cassandra/cargar.py](../carga_cassandra/cargar.py):

1. Ejecuta [esquema.cql](../carga_cassandra/esquema.cql) (`IF NOT EXISTS`), para que el DAG funcione aunque
   nadie haya creado el esquema antes.
2. Valida cada registro limpio con `validar_registro` del contrato y lo inserta en `partidas_por_fecha`
   con una sentencia preparada, en paralelo (`execute_concurrent_with_args`, 64 escrituras en vuelo).
3. Para cada fecha presente en el lote, **lee la partición completa** de esa fecha (incluidas partidas
   de lotes anteriores del mismo día) y recalcula desde cero sus filas en las tablas 2 a 5:
   - `partidas_por_dia`: conteo y resultados por ritmo.
   - `resumen_diario`: total, jugadores distintos (blancas ∪ negras), resultados y promedio de jugadas.
   - `resultados_por_apertura`: conteo y resultados por ECO; `nombre_apertura` es el de la partida más reciente.
   - `actividad_por_jugador`: cada partida cuenta para sus dos jugadores; `rating_ultimo` es el rating
     con que jugó su última partida del día.
4. Devuelve el número de partidas escritas en `partidas_por_fecha`.

Como los agregados se reescriben a partir de la tabla base, cargar el mismo lote dos veces deja
exactamente los mismos datos.

**Prueba con la muestra** (`datos/muestra/partidas_limpias.jsonl`), ejecutada dos veces seguidas con el
mismo resultado:

| Tabla | Filas |
|---|---|
| `partidas_por_fecha` | 233 |
| `partidas_por_dia` | 30 |
| `resumen_diario` | 24 (en 3 particiones: 2026-09, 2026-10, 2026-11) |
| `resultados_por_apertura` | 167 |
| `actividad_por_jugador` | 165 |

La suma de victorias de blancas, de negras y de tablas en `partidas_por_dia` (108 / 111 / 14) coincide
con la de los registros limpios.

## CRUD

[carga_cassandra/crud.py](../carga_cassandra/crud.py) trabaja sobre `actividad_por_jugador`. Cada operación
va a una partición (`jugador`) y a una fila (`fecha`):

| Operación | CQL |
|---|---|
| `insertar_actividad` | `INSERT INTO actividad_por_jugador (jugador, fecha, ...) VALUES (...)` |
| `consultar_actividad` | `SELECT * FROM actividad_por_jugador WHERE jugador = ?` |
| `actualizar_actividad` | `UPDATE actividad_por_jugador SET ... WHERE jugador = ? AND fecha = ?` |
| `eliminar_actividad` | `DELETE FROM actividad_por_jugador WHERE jugador = ? AND fecha = ?` |

Demo para el video: `python -m carga_cassandra.crud`. Inserta dos fechas de `jugador_demo`, actualiza
una, borra las dos (mostrando la tabla después de cada paso) y al final consulta un jugador real cargado
desde la muestra.

Ojo, en Cassandra `INSERT` y `UPDATE` son ambos upserts: un `UPDATE` sobre una fila que no existe la
crea. El `DELETE` no borra en el momento, sino que escribe un *tombstone* que se limpia en la
compactación.
