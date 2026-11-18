"""Configuración compartida del proyecto.

Lee los valores del archivo .env (en la raíz del repositorio) y de las variables
de entorno. Nadie debe escribir hosts, puertos ni contraseñas a mano en su código:
importen desde aquí.

    from comun.configuracion import MONGO_URI, CASSANDRA_HOSTS

Si una variable de entorno existe, gana sobre el .env. Así el mismo código funciona
en tu laptop (localhost) y dentro del contenedor de Airflow (mongo, cassandra, neo4j).
"""

import os
from pathlib import Path

# El driver de Cassandra carga numpy, y su OpenBLAS reserva memoria para un hilo por núcleo al
# arrancar. Con Docker ocupando casi toda la RAM eso falla ("OpenBLAS error: Memory allocation
# still failed"). Nuestros scripts no hacen cálculo numérico pesado: un hilo basta.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent


def _cargar_env(ruta: Path) -> None:
    """Carga un archivo .env sencillo (CLAVE=valor) sin pisar variables ya definidas."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


_cargar_env(RAIZ_PROYECTO / ".env")

# --- MongoDB ---
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "admin123")
MONGO_DB = os.getenv("MONGO_DB", "lichess")
MONGO_URI = os.getenv(
    "MONGO_URI",
    f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin",
)

# --- Cassandra ---
CASSANDRA_HOSTS = [h.strip() for h in os.getenv("CASSANDRA_HOSTS", "localhost").split(",")]
CASSANDRA_PORT = int(os.getenv("CASSANDRA_PORT", "9042"))
CASSANDRA_KEYSPACE = os.getenv("CASSANDRA_KEYSPACE", "lichess")

# --- Neo4j ---
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "lichess123")

# --- API de Lichess ---
# Lichess responde 404 si la petición no trae un User-Agent propio. No lo quiten.
LICHESS_USER_AGENT = os.getenv("LICHESS_USER_AGENT", "proyecto-bigdata-utec-lichess/1.0")
LICHESS_TOKEN = os.getenv("LICHESS_TOKEN", "")  # opcional: sube el límite de 20 a 30 partidas/s

# --- Rutas de datos ---
DIR_DATOS = Path(os.getenv("DIR_DATOS", RAIZ_PROYECTO / "datos"))
DIR_MUESTRA = DIR_DATOS / "muestra"
DIR_LOTES = DIR_DATOS / "lotes"  # aquí escribe el DAG; está en .gitignore
