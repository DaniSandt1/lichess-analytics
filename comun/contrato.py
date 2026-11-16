"""El CONTRATO.md convertido en código.

Todos los nombres que comparten los integrantes (colecciones, tablas, etiquetas)
salen de aquí. Si algo cambia, se cambia aquí y en CONTRATO.md, y se avisa al grupo.

Además trae validar_registro(), para que cada uno compruebe en sus pruebas que el
registro limpio que recibe o produce cumple el contrato.
"""

# --- MongoDB ---
COLECCION_PARTIDAS = "partidas"
COLECCION_JUGADORES = "jugadores"

# --- Cassandra ---
TABLA_PARTIDAS_POR_FECHA = "partidas_por_fecha"
TABLA_PARTIDAS_POR_DIA = "partidas_por_dia"
TABLA_RESUMEN_DIARIO = "resumen_diario"
TABLA_RESULTADOS_POR_APERTURA = "resultados_por_apertura"
TABLA_ACTIVIDAD_POR_JUGADOR = "actividad_por_jugador"
TABLA_KPIS_POR_FECHA = "kpis_por_fecha"

# --- Neo4j ---
NODO_JUGADOR = "Jugador"
NODO_PARTIDA = "Partida"
NODO_APERTURA = "Apertura"
REL_JUEGA_BLANCAS = "JUEGA_BLANCAS"
REL_JUEGA_NEGRAS = "JUEGA_NEGRAS"
REL_USA_APERTURA = "USA_APERTURA"
REL_ENFRENTO = "ENFRENTO"

# --- Valores permitidos ---
RITMOS = ("bullet", "blitz", "rapid", "classical")
GANADORES = ("blancas", "negras", "tablas")

# --- Registro limpio: campo -> (tipos permitidos) ---
CAMPOS_REGISTRO_LIMPIO = {
    "id_partida": (str,),
    "fecha": (str,),               # "YYYY-MM-DD", en UTC
    "fecha_hora": (str,),          # "YYYY-MM-DDTHH:MM:SSZ", en UTC
    "ritmo": (str,),               # uno de RITMOS
    "tiempo_inicial_seg": (int,),
    "incremento_seg": (int,),
    "origen": (str,),              # pool, arena, lobby, friend, swiss...
    "jugador_blancas": (str,),     # id de Lichess, en minúsculas
    "nombre_blancas": (str,),
    "titulo_blancas": (str, type(None)),
    "rating_blancas": (int,),
    "dif_rating_blancas": (int, type(None)),
    "jugador_negras": (str,),
    "nombre_negras": (str,),
    "titulo_negras": (str, type(None)),
    "rating_negras": (int,),
    "dif_rating_negras": (int, type(None)),
    "ganador": (str,),             # uno de GANADORES
    "estado": (str,),              # mate, resign, outoftime, draw, stalemate...
    "codigo_eco": (str,),          # ej. "B90"
    "nombre_apertura": (str,),     # ej. "Sicilian Defense: Najdorf Variation"
    "familia_apertura": (str,),    # ej. "Sicilian Defense"
    "cantidad_movimientos": (int,),  # jugadas completas = ceil(medias jugadas / 2)
}


def validar_registro(registro: dict) -> None:
    """Lanza ValueError si el registro no cumple el contrato. No devuelve nada si está bien."""
    faltan = set(CAMPOS_REGISTRO_LIMPIO) - set(registro)
    sobran = set(registro) - set(CAMPOS_REGISTRO_LIMPIO)
    if faltan or sobran:
        raise ValueError(f"Campos que faltan: {sorted(faltan)}; campos que sobran: {sorted(sobran)}")
    for campo, tipos in CAMPOS_REGISTRO_LIMPIO.items():
        valor = registro[campo]
        # bool es subclase de int en Python; no lo aceptamos como entero
        if isinstance(valor, bool) or not isinstance(valor, tipos):
            raise ValueError(f"{campo}={valor!r} debería ser {[t.__name__ for t in tipos]}")
    if registro["ritmo"] not in RITMOS:
        raise ValueError(f"ritmo inválido: {registro['ritmo']}")
    if registro["ganador"] not in GANADORES:
        raise ValueError(f"ganador inválido: {registro['ganador']}")
    if len(registro["fecha"]) != 10 or not registro["fecha_hora"].endswith("Z"):
        raise ValueError("fecha debe ser YYYY-MM-DD y fecha_hora ISO en UTC terminada en Z")
