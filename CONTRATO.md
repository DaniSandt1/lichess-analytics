# Contrato del proyecto

Este archivo fija los nombres y formatos que comparten todos. Si cada uno respeta el contrato,
las piezas encajan sin coordinarse a cada rato.

**Regla:** el contrato no se cambia sin avisar al grupo. Si algo hay que cambiar, se cambia aquí
**y** en [comun/contrato.py](comun/contrato.py), en el mismo commit, y se avisa por el chat.

Todos los nombres (colecciones, tablas, etiquetas) están como constantes en `comun/contrato.py`.
Impórtenlos desde ahí en vez de escribirlos a mano.

---

## 1. Registro limpio

Es lo que produce `validar_y_limpiar` y lo que reciben Cassandra, Neo4j y los KPIs.
Formato: **JSONL** (un objeto JSON por línea, en UTF-8).

| Campo | Tipo | Ejemplo | De dónde sale (API de Lichess) |
|---|---|---|---|
| `id_partida` | str | `"8Y0wdeIi"` | `id` |
| `fecha` | str `YYYY-MM-DD` (UTC) | `"2026-11-11"` | `createdAt` |
| `fecha_hora` | str ISO-8601 UTC con `Z` | `"2026-11-11T06:56:29Z"` | `createdAt` |
| `ritmo` | str: `bullet`, `blitz`, `rapid`, `classical` | `"blitz"` | `speed` |
| `tiempo_inicial_seg` | int | `180` | `clock.initial` |
| `incremento_seg` | int | `0` | `clock.increment` |
| `origen` | str | `"pool"` | `source` (pool, arena, lobby, friend, swiss) |
| `jugador_blancas` | str, id en minúsculas | `"realdavidnavara"` | `players.white.user.id` |
| `nombre_blancas` | str | `"RealDavidNavara"` | `players.white.user.name` |
| `titulo_blancas` | str o `null` | `"GM"` | `players.white.user.title` |
| `rating_blancas` | int | `2926` | `players.white.rating` |
| `dif_rating_blancas` | int o `null` | `3` | `players.white.ratingDiff` |
| `jugador_negras` | str | `"the_reverse_flash"` | `players.black.user.id` |
| `nombre_negras` | str | `"The_reverse_flash"` | `players.black.user.name` |
| `titulo_negras` | str o `null` | `"CM"` | `players.black.user.title` |
| `rating_negras` | int | `2546` | `players.black.rating` |
| `dif_rating_negras` | int o `null` | `-2` | `players.black.ratingDiff` |
| `ganador` | str: `blancas`, `negras`, `tablas` | `"blancas"` | `winner` + `status` |
| `estado` | str | `"resign"` | `status` (mate, resign, outoftime, draw, stalemate...) |
| `codigo_eco` | str | `"A52"` | `opening.eco` |
| `nombre_apertura` | str | `"Indian Defense: Budapest Defense"` | `opening.name` |
| `familia_apertura` | str | `"Indian Defense"` | `opening.name` antes de los `:` |
| `cantidad_movimientos` | int, jugadas completas | `26` | `ceil(medias jugadas en moves / 2)` |

Las fechas están **en UTC** (Perú es UTC−5). No conviertan zonas horarias en ninguna base.

### Reglas de validación (las aplica `validar_y_limpiar`)

Se descarta una partida si:

1. no es variante `standard` (chess960, horde, etc. no traen apertura);
2. no es rankeada (`rated` falso);
3. su ritmo no es bullet, blitz, rapid ni classical;
4. algún jugador no tiene usuario (anónimo o IA) o no tiene rating;
5. no trae `opening.eco`;
6. no tiene resultado: sin `winner` y con `status` distinto de draw, stalemate, outoftime, timeout o insufficientMaterialClaim (es decir, abortadas, en curso o anuladas);
7. tiene menos de 2 medias jugadas;
8. su `id_partida` ya apareció antes en el mismo lote (duplicado).

En la muestra: de 300 partidas crudas quedan 233 limpias; las 67 descartadas son chess960 y horde.

Para comprobar que un registro cumple el contrato: `from comun.contrato import validar_registro`.

---

## 2. MongoDB (Integrante 1)

- Base de datos: **`lichess`**
- Colección **`partidas`**: el documento **original** de la API, sin tocar, de cada partida que pasó la limpieza.
  - `_id` = `id` de la partida (así reinsertar no duplica: usen upsert).
  - Campos que se agregan: `_cargado_en` (fecha de carga, datetime UTC) y `_lote` (nombre del archivo crudo).
  - Índices: `createdAt` (descendente), `players.white.user.id`, `players.black.user.id`, `opening.eco`.
- Colección **`jugadores`**: un documento por jugador.

```json
{
  "_id": "dr_tiger",
  "nombre": "Dr_Tiger",
  "titulo": "GM",
  "ratings": {"blitz": 2922, "bullet": 3105},
  "ultima_partida": "2026-11-15T23:41:22Z (como datetime)",
  "total_partidas": 412
}
```

**Por qué Mongo:** cada partida es un JSON anidado y no todas traen los mismos campos (unas traen
`arenaTour`, otras `initialFen`, otras análisis). Mongo los guarda tal cual, sin esquema fijo, y
permite consultas ad hoc para el buscador del dashboard. Lichess mismo guarda sus partidas en MongoDB.

---

## 3. Cassandra (Integrante 2)

Keyspace **`lichess`**. Cada tabla se diseña a partir de la consulta que la usa. El script de
creación va en `carga_cassandra/esquema.cql`:

```sql
CREATE KEYSPACE IF NOT EXISTS lichess
  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

-- 1) Base: una fila por partida, particionada por día.
--    Consulta: SELECT * FROM partidas_por_fecha WHERE fecha = '2026-11-14';
CREATE TABLE IF NOT EXISTS lichess.partidas_por_fecha (
  fecha date,
  ritmo text,
  id_partida text,
  fecha_hora timestamp,
  jugador_blancas text,
  jugador_negras text,
  rating_blancas int,
  rating_negras int,
  ganador text,
  codigo_eco text,
  nombre_apertura text,
  cantidad_movimientos int,
  PRIMARY KEY ((fecha), ritmo, id_partida)
);

-- 2) Partidas de un día separadas por ritmo.
--    Consulta: SELECT * FROM partidas_por_dia WHERE fecha = '2026-11-14';
CREATE TABLE IF NOT EXISTS lichess.partidas_por_dia (
  fecha date,
  ritmo text,
  total int,
  victorias_blancas int,
  victorias_negras int,
  tablas int,
  PRIMARY KEY ((fecha), ritmo)
);

-- 3) Resumen de cada día, para la tendencia. Una partición por mes.
--    Consulta: SELECT * FROM resumen_diario WHERE anio_mes = '2026-11';
CREATE TABLE IF NOT EXISTS lichess.resumen_diario (
  anio_mes text,
  fecha date,
  total_partidas int,
  jugadores_activos int,
  victorias_blancas int,
  victorias_negras int,
  tablas int,
  promedio_movimientos double,
  PRIMARY KEY ((anio_mes), fecha)
) WITH CLUSTERING ORDER BY (fecha DESC);

-- 4) Historial de resultados de una apertura.
--    Consulta: SELECT * FROM resultados_por_apertura WHERE codigo_eco = 'B90';
CREATE TABLE IF NOT EXISTS lichess.resultados_por_apertura (
  codigo_eco text,
  fecha date,
  nombre_apertura text,
  total int,
  victorias_blancas int,
  victorias_negras int,
  tablas int,
  PRIMARY KEY ((codigo_eco), fecha)
) WITH CLUSTERING ORDER BY (fecha DESC);

-- 5) Actividad diaria de un jugador.
--    Consulta: SELECT * FROM actividad_por_jugador WHERE jugador = 'dr_tiger';
CREATE TABLE IF NOT EXISTS lichess.actividad_por_jugador (
  jugador text,
  fecha date,
  partidas int,
  victorias int,
  derrotas int,
  tablas int,
  rating_ultimo int,
  PRIMARY KEY ((jugador), fecha)
) WITH CLUSTERING ORDER BY (fecha DESC);

-- 6) KPIs calculados por el DAG (la llena Integrante 4).
--    Consulta: SELECT * FROM kpis_por_fecha WHERE fecha = '2026-11-14';
CREATE TABLE IF NOT EXISTS lichess.kpis_por_fecha (
  fecha date,
  kpi text,
  valor double,
  detalle text,
  calculado_en timestamp,
  PRIMARY KEY ((fecha), kpi)
);
```

**Cómo se cargan (idempotente):** primero se insertan los registros en `partidas_por_fecha`
(en Cassandra un INSERT con la misma clave sobrescribe, así que reejecutar no duplica). Después,
para cada fecha del lote, se lee esa partición completa y se **recalculan** las filas de las tablas
2 a 5 para esa fecha. No usen columnas `counter`: si Airflow reintenta una tarea, contarían doble.

**Por qué Cassandra:** son series de tiempo con muchas escrituras que siempre se consultan por
una clave conocida (fecha, mes, jugador o apertura). Cada consulta del dashboard lee una sola partición.

---

## 4. Neo4j (Integrante 3)

```
(:Jugador)-[:JUEGA_BLANCAS {rating, dif_rating}]->(:Partida)
(:Jugador)-[:JUEGA_NEGRAS  {rating, dif_rating}]->(:Partida)
(:Partida)-[:USA_APERTURA]->(:Apertura)
(:Jugador)-[:ENFRENTO {veces, ultima_fecha}]->(:Jugador)
```

| Nodo | Clave única | Propiedades |
|---|---|---|
| `Jugador` | `id` | `nombre`, `titulo` |
| `Partida` | `id` | `fecha` (date), `ritmo`, `ganador`, `estado`, `cantidad_movimientos` |
| `Apertura` | `codigo_eco` | `nombre` (el último visto), `familia` |

- `ENFRENTO` va **una sola vez por pareja**, del `id` alfabéticamente menor al mayor. En las consultas
  úsenla sin dirección: `(a:Jugador)-[:ENFRENTO]-(b:Jugador)`.
- `veces` se incrementa solo cuando la `Partida` se crea por primera vez (`ON CREATE`), para que
  reejecutar un lote no infle el conteo.

Script de creación (`carga_neo4j/esquema.cypher`):

```cypher
CREATE CONSTRAINT jugador_id IF NOT EXISTS FOR (j:Jugador) REQUIRE j.id IS UNIQUE;
CREATE CONSTRAINT partida_id IF NOT EXISTS FOR (p:Partida) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT apertura_eco IF NOT EXISTS FOR (a:Apertura) REQUIRE a.codigo_eco IS UNIQUE;
```

**Por qué Neo4j:** preguntas como "¿quién se enfrentó con más rivales distintos?" o "¿qué apertura
conecta a más jugadores?" son recorridos de relaciones. En tablas serían varios JOIN sobre sí mismas;
en un grafo son una consulta corta.

---

## 5. Funciones que llama el DAG

El DAG ([dags/pipeline_lichess.py](dags/pipeline_lichess.py)) solo importa estas funciones. **No
cambien su nombre, sus parámetros ni lo que devuelven.** Por dentro pueden hacer lo que quieran.

| Orden | Función | Archivo | Responsable | Recibe | Devuelve |
|---|---|---|---|---|---|
| 1 | `extraer_partidas(desde, hasta)` | `extraccion/extraer.py` | Integrante 1 | `datetime` UTC o `None` | `str`: ruta del JSONL crudo |
| 2 | `validar_y_limpiar(ruta_cruda)` | `extraccion/limpieza.py` | Integrante 1 | ruta cruda | `str`: ruta del JSONL limpio |
| 3 | `cargar_en_mongo(ruta_cruda, ruta_limpia)` | `carga_mongo/cargar.py` | Integrante 1 | las dos rutas | `int`: partidas cargadas |
| 4 | `cargar_en_cassandra(ruta_limpia)` | `carga_cassandra/cargar.py` | Integrante 2 | ruta limpia | `int`: filas en `partidas_por_fecha` |
| 5 | `construir_grafo_neo4j(ruta_limpia)` | `carga_neo4j/cargar.py` | Integrante 3 | ruta limpia | `int`: partidas procesadas |
| 6 | `calcular_kpis(fecha)` | `kpis/calcular.py` | Integrante 4 | `str` `YYYY-MM-DD` | `dict`: `{kpi: valor}` |

- Cassandra y Neo4j leen el **archivo limpio del lote**, no Mongo. Así no dependen de que Mongo esté listo.
- Los lotes se guardan en `datos/lotes/` (no se suben a git): `crudo_<YYYYMMDD_HHMM>.jsonl` y
  `limpio_<YYYYMMDD_HHMM>.jsonl`, donde la fecha es `desde`. La carga inicial usa `crudo_inicial.jsonl`.
- Cada función debe poder ejecutarse dos veces con el mismo lote sin duplicar nada.
- Las conexiones se piden a `comun/conexiones.py` y la configuración a `comun/configuracion.py`.

### API de Lichess (Integrante 1)

- Partidas de un jugador: `GET https://lichess.org/api/games/user/{usuario}`
- Cabeceras obligatorias: `Accept: application/x-ndjson` y **`User-Agent`** (sin él, Lichess responde 404).
- Parámetros: `since` y `until` en **milisegundos**, `rated=true`, `opening=true`, `moves=true`,
  `perfType=bullet,blitz,rapid,classical`, `clocks=false`, `evals=false`, `max` para la carga inicial.
- Lista de jugadores: `GET https://lichess.org/api/player/top/50/blitz`
- Límite: 20 partidas/s sin token, 30 con token. Descarguen un jugador a la vez; si responde 429, esperen 60 s.

---

## 6. KPIs (Integrante 4)

Se calculan para cada `fecha` y se guardan en `kpis_por_fecha` con estos nombres en la columna `kpi`:

| `kpi` | Definición | Fórmula | Fuente |
|---|---|---|---|
| `partidas_dia` | Partidas procesadas en el día | P(d) = nº de partidas con `fecha` = d | `resumen_diario` |
| `crecimiento_diario_pct` | Variación de partidas respecto al día anterior | (P(d) − P(d−1)) / P(d−1) × 100 | `resumen_diario` |
| `tasa_victoria_blancas_pct` | Qué tan seguido ganan las blancas | victorias_blancas(d) / P(d) × 100 | `resumen_diario` |
| `apertura_top` | Apertura más jugada del día y su rendimiento | ECO con más partidas en d; `valor` = (victorias blancas + 0.5 × tablas) / partidas × 100; `detalle` = código y nombre | `partidas_por_fecha` (partición del día) |
| `jugador_mas_rivales` | Jugador con más rivales distintos (acumulado) | max sobre j de nº de vecinos por `ENFRENTO`; `detalle` = id del jugador | Neo4j |
| `promedio_partidas_por_jugador` | Partidas promedio por jugador activo | 2 × P(d) / jugadores_activos(d) (cada partida cuenta para sus dos jugadores) | `resumen_diario` |

La interpretación de cada KPI la redacta Integrante 4 en el informe. Ojo: los datos son de los
jugadores que descargamos y de sus rivales, no de todo Lichess; hay que decirlo al interpretar.

---

## 7. Dashboard (Integrante 4)

`streamlit run dashboard/app.py`, conectado a las tres bases:

- **Cassandra:** tarjetas con los KPIs de la fecha elegida y gráfico de tendencia de `resumen_diario`.
- **MongoDB:** buscador de partidas por jugador o por id, mostrando el documento original.
- **Neo4j:** grafo de enfrentamientos (pyvis), con el jugador elegido y sus rivales.
