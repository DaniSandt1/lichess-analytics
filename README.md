# Lichess Analytics

Proyecto Grupal II de Big Data (UTEC): arquitectura multimodelo con MongoDB, Cassandra y Neo4j,
orquestada con Apache Airflow y visualizada en un dashboard de Streamlit.

**Problema:** ¿cómo juegan los mejores jugadores de Lichess? Qué aperturas usan, quién gana más,
cómo cambia su actividad día a día y quién se enfrenta con quién.

**Dataset:** partidas en JSON de la API pública de Lichess, de 40 jugadores top y sus rivales.
Carga inicial de 55,524 partidas limpias (56,581 descargadas) y una carga incremental diaria con las
partidas nuevas.

> **Antes de escribir una línea de código, lean [CONTRATO.md](CONTRATO.md).** Ahí están los nombres
> de las colecciones, tablas, nodos y funciones que todos comparten.

---

## Equipo y roles

| Integrante | Nombre | Rol | Carpetas | Sección del informe |
|---|---|---|---|---|
| Coordinador | Daniel Guillermo Sandoval Toro | Infraestructura y Airflow | `dags/`, `comun/`, `infra/`, `docker-compose.yml` | Arquitectura propuesta y explicación del DAG |
| Integrante 1 | Estefano Zárate | Datos y MongoDB | `extraccion/`, `carga_mongo/` | Descripción del dataset y modelo de MongoDB |
| Integrante 2 | Matias Castillo | Cassandra | `carga_cassandra/` | Modelo de datos de Cassandra |
| Integrante 3 | Elizabeth Huaman Santillan | Neo4j | `carga_neo4j/` | Modelo de grafo en Neo4j |
| Integrante 4 | _(completar)_ | KPIs y dashboard | `kpis/`, `dashboard/` | KPIs implementados y capturas del dashboard |

Introducción, descripción del problema y conclusiones: entre todos (o quien termine primero).

---

## Lo que ya está hecho (Coordinador)

- [x] **Repositorio y estructura de carpetas**, una carpeta por rol para no pisarse en git.
- [x] **[CONTRATO.md](CONTRATO.md)**: registro limpio, colecciones de Mongo, tablas de Cassandra
      (con el CQL listo), modelo del grafo de Neo4j, firmas de las funciones del DAG y fórmulas de los KPIs.
      Su versión en código está en [comun/contrato.py](comun/contrato.py), con `validar_registro()` para probar.
- [x] **Muestra de datos reales** en [datos/muestra/](datos/muestra/), descargada de la API de Lichess
      el 15/11/2026 (jugadores RealDavidNavara, Dr_Tiger y onepoundrook):
  - `partidas_crudas.jsonl`: 300 partidas tal como las devuelve la API.
  - `partidas_limpias.jsonl`: 233 partidas en el formato del contrato (133 jugadores, 80 aperturas, 24 días distintos).
- [x] **Limpieza funcionando**: [extraccion/limpieza.py](extraccion/limpieza.py) (`validar_y_limpiar`)
      con las 8 reglas de validación del contrato. Se usó para generar la muestra limpia.
- [x] **Infraestructura**: [docker-compose.yml](docker-compose.yml) con MongoDB 7, Cassandra 4.1, Neo4j 5
      y Airflow 2.10 (imagen propia con los drivers en [infra/airflow/](infra/airflow/)), más
      [.env.ejemplo](.env.ejemplo) y [comun/configuracion.py](comun/configuracion.py), que lee el `.env`.
- [x] **Conexiones compartidas** en [comun/conexiones.py](comun/conexiones.py): `obtener_mongo()`,
      `obtener_cassandra()` y `obtener_neo4j()`.
- [x] **Plantillas** en cada carpeta con la firma exacta del contrato. Imprimen `PENDIENTE` y devuelven
      un valor válido, así el DAG corre aunque nadie haya terminado.
- [x] **DAG** [dags/pipeline_lichess.py](dags/pipeline_lichess.py), programado `@daily`, con las 6 etapas
      del enunciado: extraer → validar_y_limpiar → cargar_mongo → (cargar_cassandra ∥ construir_grafo) → calcular_kpis.
      Probado de punta a punta con las plantillas.
- [x] **[scripts/verificar_entorno.py](scripts/verificar_entorno.py)**: comprueba que las tres bases responden.
- [x] Hallazgo útil: **la API de Lichess responde 404 si la petición no trae `User-Agent`**. Ya está en la configuración.

**Pendiente del Coordinador:** integrar cada parte a medida que llegue, correr el DAG con los datos
completos, revisar los PRs y escribir las secciones de arquitectura y del DAG del informe.

---

## Avance por integrante

| Integrante | Estado | PR |
|---|---|---|
| Integrante 1 — Datos y MongoDB | Terminado | [#5](https://github.com/DaniSandt1/lichess-analytics/pull/5) (en `main`) |
| Integrante 2 — Cassandra | Terminado | [#3](https://github.com/DaniSandt1/lichess-analytics/pull/3) (en `main`) |
| Integrante 3 — Neo4j | Código terminado; falta la sección del informe | [#1](https://github.com/DaniSandt1/lichess-analytics/pull/1), [#2](https://github.com/DaniSandt1/lichess-analytics/pull/2) (en `main`) |
| Integrante 4 — KPIs y dashboard | Código terminado; falta la sección del informe y las capturas | [#6](https://github.com/DaniSandt1/lichess-analytics/pull/6) (en `main`) |

### Integrante 1 — Estefano Zárate

- [x] **Extracción** en [extraccion/extraer.py](extraccion/extraer.py): `extraer_partidas(desde, hasta)` baja
      las partidas del intervalo de 40 jugadores top (lista fija `JUGADORES`), de uno en uno y con
      reintento ante 429. Probada con el 15/11/2026: 137 partidas crudas, 134 limpias.
- [x] **Descarga inicial** con [extraccion/carga_inicial.py](extraccion/carga_inicial.py): hasta 1,500 partidas
      por jugador. Si se corta, retoma desde el último jugador completo. Resultado:
      **56,581 partidas crudas → 55,524 limpias**, 10,655 jugadores, 219 aperturas y 1,340 días (32 min con token).
      El archivo `crudo_inicial.jsonl` (50 MB, 11 MB en zip) no va en git: se pasa por Drive o WhatsApp.
- [x] **MongoDB**: [carga_mongo/crear_indices.py](carga_mongo/crear_indices.py) (colecciones e índices) y
      [carga_mongo/cargar.py](carga_mongo/cargar.py), con `cargar_en_mongo`. Hace upsert del documento original
      en `partidas` y recalcula `jugadores` con una agregación y `$merge`. Reejecutar no duplica.
- [x] **CRUD** en [carga_mongo/crud.py](carga_mongo/crud.py): `python -m carga_mongo.crud`.
- [x] **Informe**: [informe/dataset_y_mongo.md](informe/dataset_y_mongo.md).

### Integrante 2 — Matias Castillo

- [x] **Esquema** en [carga_cassandra/esquema.cql](carga_cassandra/esquema.cql) (keyspace y las 6 tablas) y
      [carga_cassandra/crear_esquema.py](carga_cassandra/crear_esquema.py): `python -m carga_cassandra.crear_esquema`.
- [x] **Carga** en [carga_cassandra/cargar.py](carga_cassandra/cargar.py): `cargar_en_cassandra` hace upsert
      en `partidas_por_fecha` y recalcula los agregados de cada fecha del lote (sin `counter`). Probada con la
      carga inicial: 55,524 partidas y 1,340 días en ~20 s. Reejecutar no duplica.
- [x] **CRUD** en [carga_cassandra/crud.py](carga_cassandra/crud.py) sobre `actividad_por_jugador`:
      `python -m carga_cassandra.crud`.
- [x] **Informe**: [informe/modelo_cassandra.md](informe/modelo_cassandra.md).
- `kpis_por_fecha` ya se crea con el esquema; la llena Integrante 4.

### Cargar la carga inicial en las tres bases (Coordinador)

Con `crudo_inicial.jsonl` en `datos/lotes/` y las bases levantadas:

```bash
python -m extraccion.limpieza datos/lotes/crudo_inicial.jsonl datos/lotes/limpio_inicial.jsonl
python -c "from carga_mongo.cargar import cargar_en_mongo; cargar_en_mongo('datos/lotes/crudo_inicial.jsonl', 'datos/lotes/limpio_inicial.jsonl')"
python -c "from carga_cassandra.cargar import cargar_en_cassandra; cargar_en_cassandra('datos/lotes/limpio_inicial.jsonl')"
python -c "from carga_neo4j.cargar import construir_grafo_neo4j; construir_grafo_neo4j('datos/lotes/limpio_inicial.jsonl')"
python -m kpis.calcular --desde 2026-08-01 --hasta 2026-11-16   # KPIs de cada día, para el dashboard
```

Probado el 16/11/2026 sobre bases vacías: limpieza 7 s, Mongo 10 s, Cassandra 97 s y Neo4j 32 s.
Las tres bases quedan con 55,524 partidas, y repetir los comandos no duplica nada.

### Lo que falta para cumplir el enunciado

- **Integrante 4:** sección de KPIs del informe (definición, fórmula e interpretación de cada uno)
  y capturas del dashboard.
- **Integrante 3:** sección del informe del modelo de grafo en Neo4j.
- **Coordinador:** cargar la carga inicial, correr el DAG con los datos completos y escribir las
  secciones de arquitectura y del DAG.
- **Todos:** introducción, descripción del problema, conclusiones, armar el PDF y grabar el video.

---

## Qué tiene que hacer cada integrante

Cada uno trabaja con la muestra (`datos/muestra/partidas_limpias.jsonl`) desde el primer minuto.
No esperen a que Integrante 1 termine la descarga completa.

### Integrante 1 — Datos y MongoDB

> **PRIORIDAD N.º 1: dejar corriendo la descarga completa HOY, antes que Mongo y el CRUD.**
> Es lo único lento del proyecto (la API entrega 20 partidas por segundo), y el DAG con datos reales,
> el dashboard y la grabación del video dependen de ella. Descargar no necesita Docker ni las bases:
> solo internet.

1. **Extracción** en [extraccion/extraer.py](extraccion/extraer.py): implementar
   `extraer_partidas(desde, hasta)` contra la API de Lichess (detalles en CONTRATO.md, sección 5).
   Devuelve la ruta del JSONL crudo en `datos/lotes/`.
2. **Descarga inicial**: un script `extraccion/carga_inicial.py` que baje ~1,500 partidas de cada uno
   de ~40 jugadores top (≈ 60,000) y las escriba **crudas** en `datos/lotes/crudo_inicial.jsonl`.
   Solo descarga: no limpia ni carga en las bases (eso lo hace después el Coordinador con las
   funciones del contrato, y tarda pocos minutos).
   - **Tiempo:** 60,000 partidas ÷ 20 por segundo ≈ 50 minutos.
   - **Para que tarde menos:**
     - Con un token gratuito de https://lichess.org/account/oauth/token (sin marcar permisos),
       puesto en `LICHESS_TOKEN` del `.env`, el límite sube a 30 por segundo (≈ 35 minutos).
     - Pueden repartirse la lista de jugadores: el límite es por persona, así que si dos integrantes
       bajan 20 jugadores cada uno al mismo tiempo, cada uno tarda la mitad. Para eso, que el script
       acepte qué parte de la lista bajar (por ejemplo `--desde 0 --hasta 20`) y un nombre de archivo
       de salida distinto; al final se unen los archivos en `crudo_inicial.jsonl`.
   - **Para entregarlo:** el archivo pesa unos 55 MB y `datos/lotes/` no se sube a git. Pásenlo al
     Coordinador por Drive o WhatsApp; él lo pone en `datos/lotes/` y lo carga.
   - Si la descarga se corta, que el script pueda retomarla desde el último jugador completado
     en vez de empezar de cero.
3. **Limpieza**: ya funciona. Revisen las reglas y, si encuentran casos nuevos en la descarga grande, agréguenlos.
4. **Carga en MongoDB** en [carga_mongo/cargar.py](carga_mongo/cargar.py): `cargar_en_mongo(ruta_cruda, ruta_limpia)`,
   colecciones `partidas` (documento original, `_id` = id) y `jugadores`, con upsert e índices.
5. **CRUD** en [carga_mongo/crud.py](carga_mongo/crud.py): crear, consultar, actualizar y eliminar documento,
   con una demo que se corra con `python -m carga_mongo.crud`.
6. **Informe:** descripción del dataset (origen, campos, volumen, frecuencia de actualización) y modelo de MongoDB.

### Integrante 2 — Cassandra

1. **Esquema**: `carga_cassandra/esquema.cql` con el keyspace y las 6 tablas del contrato
   (el CQL ya está en CONTRATO.md, sección 3) y `carga_cassandra/crear_esquema.py` que lo ejecute.
2. **Carga** en [carga_cassandra/cargar.py](carga_cassandra/cargar.py): `cargar_en_cassandra(ruta_limpia)`.
   Inserta en `partidas_por_fecha` y recalcula los agregados de cada fecha del lote (sin `counter`).
3. **CRUD** en [carga_cassandra/crud.py](carga_cassandra/crud.py): inserción, consulta, actualización y
   eliminación, con demo `python -m carga_cassandra.crud`.
4. **Informe:** modelo de Cassandra: cada tabla, su clave de partición y de clustering, y la consulta que resuelve.

### Integrante 3 — Neo4j

1. **Esquema**: `carga_neo4j/esquema.cypher` con las 3 constraints del contrato.
2. **Grafo** en [carga_neo4j/cargar.py](carga_neo4j/cargar.py): `construir_grafo_neo4j(ruta_limpia)`, con
   `UNWIND` por lotes y `MERGE`. `ENFRENTO.veces` solo sube cuando la partida es nueva.
3. **Consultas** en `carga_neo4j/consultas.cypher` (o funciones en Python) que necesita Integrante 4:
   jugador con más rivales distintos, apertura que conecta más jugadores y subgrafo de un jugador y sus rivales.
4. **CRUD** en [carga_neo4j/crud.py](carga_neo4j/crud.py): crear nodo, crear relación, actualizar propiedades
   y eliminar nodos o relaciones, con demo `python -m carga_neo4j.crud`.
5. **Informe:** modelo de grafo (diagrama de nodos y relaciones) y por qué conviene un grafo aquí.

### Integrante 4 — KPIs y dashboard

1. **KPIs** en [kpis/calcular.py](kpis/calcular.py): `calcular_kpis(fecha)` calcula los 6 KPIs del contrato
   (sección 6) y los guarda en `kpis_por_fecha`. Mientras Cassandra no esté lista, pueden prototipar
   las fórmulas con pandas sobre la muestra.
2. **Dashboard** en [dashboard/app.py](dashboard/app.py) (Streamlit), conectado a las tres bases:
   tarjetas de KPIs y tendencia (Cassandra), buscador de partidas (MongoDB) y grafo de enfrentamientos
   con pyvis (Neo4j).
3. **Informe:** definición, fórmula e interpretación de cada KPI, capturas del dashboard y armado final del PDF.

---

## Cómo empezar

Requisitos: Git, Docker Desktop y Python 3.11.

```bash
git clone <url-del-repo>
cd <carpeta-del-repo>
cp .env.ejemplo .env                      # en Windows: copy .env.ejemplo .env

python -m venv .venv
.venv\Scripts\activate                    # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Levanten **solo la base que necesitan** (ahorra memoria):

```bash
docker compose up -d mongo                # Integrante 1
docker compose up -d cassandra            # Integrante 2 (tarda ~1 min en estar lista)
docker compose up -d neo4j                # Integrante 3 (navegador en http://localhost:7474)
docker compose up -d                      # todo, incluido Airflow (Integrante 4 y Coordinador)

docker compose ps                         # todas deben decir "healthy"
python -m scripts.verificar_entorno       # comprueba la conexión desde Python
```

Para probar su función con la muestra, sin Airflow:

```bash
python -c "from carga_cassandra.cargar import cargar_en_cassandra; print(cargar_en_cassandra('datos/muestra/partidas_limpias.jsonl'))"
```

Si Docker dice `port is already allocated`, otro programa usa ese puerto. Para Airflow, cambien
`AIRFLOW_PORT` en su `.env` (por ejemplo a 8081) y vuelvan a correr `docker compose up -d`.

**Airflow:** http://localhost:8080 (usuario `admin`, contraseña `admin`). El DAG se llama
`pipeline_lichess`; para correrlo a mano, botón ▶ (Trigger DAG). Los logs de cada tarea muestran los `print`.

| Servicio | Dirección | Usuario / contraseña |
|---|---|---|
| MongoDB | `localhost:27017` | `admin` / `admin123` |
| Cassandra | `localhost:9042` | sin autenticación |
| Neo4j | http://localhost:7474 (bolt `localhost:7687`) | `neo4j` / `lichess123` |
| Airflow | http://localhost:8080 | `admin` / `admin` |

---

## Estructura del repositorio

```
├── CONTRATO.md               nombres y formatos compartidos (leer primero)
├── docker-compose.yml        Mongo, Cassandra, Neo4j y Airflow
├── .env.ejemplo              copiar como .env
├── requirements.txt          dependencias para trabajar en la laptop
├── comun/                    configuración, contrato en código y conexiones (Coordinador)
├── dags/                     DAG de Airflow (Coordinador)
├── infra/airflow/            imagen de Airflow con los drivers (Coordinador)
├── extraccion/               extracción y limpieza (Integrante 1)
├── carga_mongo/              carga y CRUD de MongoDB (Integrante 1)
├── carga_cassandra/          esquema, carga y CRUD de Cassandra (Integrante 2)
├── carga_neo4j/              esquema, grafo, consultas y CRUD de Neo4j (Integrante 3)
├── kpis/                     cálculo de KPIs (Integrante 4)
├── dashboard/                app de Streamlit (Integrante 4)
├── scripts/                  utilidades (verificar_entorno.py)
├── datos/muestra/            muestra real: 300 crudas y 233 limpias
├── datos/lotes/              lotes que genera el DAG (no se suben a git)
└── informe/                  informe técnico y capturas
```

Las carpetas se llaman `carga_mongo`, `carga_cassandra` y `carga_neo4j` a propósito: si se llamaran
`cassandra/` o `neo4j/`, Python las confundiría con las librerías y los `import` fallarían.

---

## Reglas de trabajo

1. **Una rama por persona**: `integrante-1`, `integrante-2`, etc. Nadie trabaja directo en `main`.
2. **Cada uno toca solo sus carpetas.** Si necesitan algo de otra carpeta, pídanlo por el chat.
3. **El contrato no se cambia sin avisar.** Si hay que cambiarlo, se cambia CONTRATO.md y `comun/contrato.py` juntos.
4. **Pull request a `main`** cuando su función funcione con la muestra. El Coordinador revisa y hace merge.
5. **Nada de contraseñas en el código**: todo sale de `comun/configuracion.py`.
6. **Cada función debe poder ejecutarse dos veces con el mismo lote sin duplicar datos** (Airflow reintenta tareas).

```bash
git checkout -b integrante-2
# ... trabajar ...
git add carga_cassandra/
git commit -m "Cassandra: esquema y carga de partidas_por_fecha"
git push -u origin integrante-2           # y abrir el PR en GitHub
```

---

## Cronograma (entrega: lunes 16 de noviembre)

| Cuándo | Qué |
|---|---|
| Domingo 15, noche | Integrante 1: lo primero, la descarga inicial, y pasar `crudo_inicial.jsonl` al Coordinador. Todos: clonar, levantar su base y correr su función con la muestra. |
| Lunes 16, mañana | Cada uno sube su PR. El Coordinador integra, carga `crudo_inicial.jsonl` en las tres bases (minutos) y corre el DAG. |
| Lunes 16, mediodía | Integrante 4 termina el dashboard con los datos completos y saca las capturas. |
| Lunes 16, tarde | Informe en PDF, video y entrega. |

## Video (20 a 25 minutos)

Cada integrante habla 4 o 5 minutos: qué hizo, por qué esa base de datos y su CRUD en vivo.

1. Coordinador: problema, arquitectura y contrato.
2. Integrante 1: dataset, extracción, limpieza, MongoDB y su CRUD.
3. Integrante 2: modelo de Cassandra y su CRUD.
4. Integrante 3: grafo en Neo4j, consultas y su CRUD.
5. Coordinador: el DAG ejecutándose en Airflow.
6. Integrante 4: KPIs y dashboard.
