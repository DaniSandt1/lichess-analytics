# Descripción del dataset y modelo de MongoDB

_Sección del informe a cargo de Integrante 1. Código en [extraccion/](../extraccion/) y [carga_mongo/](../carga_mongo/)._

## Descripción del dataset

**Origen.** API pública de Lichess (https://lichess.org/api), servidor de ajedrez en línea libre y de
código abierto. No hace falta cuenta. Con un token personal sin permisos el límite sube de 20 a 30
partidas por segundo.

| Endpoint | Uso |
|---|---|
| `GET /api/player/top/50/blitz` | Lista de los mejores jugadores de blitz. Se tomaron los 40 primeros (lista fija en `extraccion/extraer.py`). |
| `GET /api/games/user/{usuario}` | Partidas de un jugador en NDJSON (una partida por línea), filtradas por `since`/`until` en milisegundos. |

**Campos principales de cada partida (JSON anidado):**

| Campo | Contenido |
|---|---|
| `id` | Identificador de 8 caracteres |
| `rated`, `variant`, `speed`, `perf` | Si es rankeada, variante (standard, chess960...), ritmo (bullet, blitz, rapid, classical) |
| `createdAt`, `lastMoveAt` | Inicio y última jugada, en milisegundos UTC |
| `status`, `winner` | Cómo terminó (mate, resign, outoftime, draw...) y quién ganó (`white`/`black`; sin `winner` si fue tablas) |
| `players.white` / `players.black` | `user` (`id`, `name`, `title`), `rating` y `ratingDiff` de cada jugador |
| `opening` | `eco` (código ECO), `name` y `ply` de la apertura |
| `moves` | Jugadas en notación algebraica, separadas por espacios |
| `clock` | `initial` e `increment` en segundos |
| `source`, `tournament`, `swiss` | Origen (pool, arena, lobby, friend, swiss) y torneo, cuando aplica |

No todas las partidas traen los mismos campos: `tournament` solo aparece en partidas de arena,
`winner` falta en las tablas, `title` falta en jugadores sin título, etc.

**Volumen.**

| Carga | Partidas crudas | Partidas limpias | Jugadores distintos |
|---|---|---|---|
| Muestra (`datos/muestra/`) | 300 | 233 | 133 |
| Carga inicial (`datos/lotes/crudo_inicial.jsonl`, 52 MB) | 56,581 | **55,524** | 10,655 |

La carga inicial (`python -m extraccion.carga_inicial`, 16/11/2026) bajó hasta 1,500 partidas de cada
uno de los 40 jugadores en 32 minutos, con token. 34 jugadores llegaron al máximo; los que juegan
menos aportaron entre 119 y 1,460. Se descartaron 1,057 partidas: 934 duplicadas (partidas entre dos
jugadores de la lista, que aparecen en la descarga de ambos), 56 sin apertura, 48 sin jugadas y 19 de
otra variante.

Características de las 55,524 partidas limpias:

| Ritmo | Partidas |
|---|---|
| blitz | 36,329 |
| bullet | 18,342 |
| rapid | 804 |
| classical | 49 |

- 219 códigos ECO distintos y 1,340 días con partidas, entre 2020-07-04 y 2026-11-16.
- El 68% de las partidas (37,620) son de 2026 y 7,624 de 2025. Las 1,500 partidas más recientes de un
  jugador cubren desde 19 días hasta casi 6 años, según cuánto juegue (mediana: 322 días).

**Frecuencia de actualización.** El DAG corre `@daily`: `extraer_partidas(desde, hasta)` baja solo las
partidas de los 40 jugadores jugadas en el intervalo del DAG (el día anterior) y las escribe en
`datos/lotes/crudo_<YYYYMMDD_HHMM>.jsonl`. Si la tarea se reintenta, el archivo se sobrescribe.
Prueba con el 15/11/2026: 137 partidas crudas y 134 limpias, unas 150 partidas nuevas por día.

**Limpieza.** `validar_y_limpiar` aplica las 8 reglas de CONTRATO.md (solo variante standard,
rankeadas, con ambos jugadores con usuario y rating, con apertura, con resultado, con al menos 2 medias
jugadas y sin duplicados) y produce el registro limpio plano que usan Cassandra, Neo4j y los KPIs.

## Modelo de MongoDB

Base de datos `lichess`, con dos colecciones.

### `partidas`

El documento **original** de la API, tal como llega, de cada partida que pasó la limpieza.

- `_id` = `id` de la partida. Reinsertar el mismo lote no duplica porque la carga usa `ReplaceOne` con
  `upsert=True` en lotes de 1,000 (`bulk_write`).
- Campos agregados: `_cargado_en` (fecha de carga, UTC) y `_lote` (archivo crudo de origen), para
  rastrear de qué ejecución del DAG vino cada documento.

Índices (script de creación: `python -m carga_mongo.crear_indices`, que también corre al inicio de la carga):

| Índice | Para qué |
|---|---|
| `createdAt` descendente | Últimas partidas primero; filtros por rango de fechas |
| `players.white.user.id` | Buscar partidas de un jugador con blancas |
| `players.black.user.id` | Buscar partidas de un jugador con negras |
| `opening.eco` | Buscar partidas por apertura |

Ejemplo de consulta del buscador del dashboard:

```js
db.partidas.find({$or: [{"players.white.user.id": "dr_tiger"}, {"players.black.user.id": "dr_tiger"}]})
           .sort({createdAt: -1}).limit(20)
```

### `jugadores`

Un documento por jugador:

```json
{
  "_id": "dr_tiger",
  "nombre": "Dr_Tiger",
  "titulo": "GM",
  "ratings": {"bullet": 3331, "blitz": 2922},
  "ultima_partida": ISODate("2026-11-15T15:34:42Z"),
  "total_partidas": 100
}
```

No se actualiza con `$inc`, porque un reintento contaría doble. Después de cargar las partidas, una
agregación sobre `partidas` (`$match` → `$unwind` de los dos lados → `$group` por jugador y ritmo →
`$group` por jugador) recalcula el resumen de cada jugador del lote y lo escribe con `$merge`
(`whenMatched: "replace"`). Así `total_partidas` y el último rating de cada ritmo siempre cuadran con
las partidas guardadas.

### Por qué MongoDB

- **Documentos anidados y heterogéneos.** Cada partida es un JSON con objetos dentro de objetos
  (`players.white.user`, `opening`, `clock`) y campos opcionales. Mongo los guarda tal cual, sin
  aplanar ni definir un esquema fijo, y conserva el dato original para futuros análisis.
- **Consultas ad hoc.** El buscador del dashboard filtra por campos anidados (jugador, apertura,
  fecha) con índices secundarios, sin haber diseñado una tabla para cada consulta como en Cassandra.
- **Agregaciones.** El pipeline de agregación calcula resúmenes como la colección `jugadores`
  directamente en la base.
- Lichess mismo guarda sus partidas en MongoDB.

## CRUD

[carga_mongo/crud.py](../carga_mongo/crud.py), demo con `python -m carga_mongo.crud`. Copia una partida real
de la muestra con otro `_id` para no tocar los datos cargados:

| Operación | Método de pymongo |
|---|---|
| `crear_partida` | `insert_one` |
| `consultar_partida` | `find_one({"_id": ...})` |
| `actualizar_partida` | `update_one({"_id": ...}, {"$set": ...})` |
| `eliminar_partida` | `delete_one({"_id": ...})` |

## Pruebas de la carga

Cada carga se ejecutó dos veces seguidas con el mismo resultado:

| Lote | `partidas` | `jugadores` | Suma de `total_partidas` | Tiempo |
|---|---|---|---|---|
| Muestra | 233 | 133 | 466 | < 1 s |
| Carga inicial | 55,524 | 10,655 | 111,048 | ~3 s |
| Lote diario del 15/11 (sobre la carga inicial) | 55,524 (sin duplicar) | 10,655 | 111,048 | < 1 s |

La suma de `total_partidas` es el doble de las partidas, porque cada una cuenta para sus dos jugadores.
