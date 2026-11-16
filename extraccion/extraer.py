"""Extracción desde la API de Lichess.

Responsable: Integrante 1.

- extraer_partidas(desde, hasta): función del contrato que usa el DAG para la carga diaria.
- descargar_jugador(...): baja las partidas de un jugador; la reusa carga_inicial.py.

Detalles de la API en CONTRATO.md, sección 5. Los jugadores se bajan de uno en uno
(no en paralelo) y si Lichess responde 429 se espera 60 s y se reintenta.
"""

import time
from datetime import datetime
from pathlib import Path

import requests

from comun import configuracion as cfg

URL_PARTIDAS = "https://lichess.org/api/games/user/{usuario}"
URL_TOP = "https://lichess.org/api/player/top/{n}/blitz"

# Top 40 de blitz en Lichess al 16/11/2026 (de https://lichess.org/api/player/top/50/blitz).
# Lista fija para que la carga inicial y las cargas diarias sigan a los mismos jugadores.
JUGADORES = [
    "aworldidontknow", "realdavidnavara", "dr_tiger", "onepoundrook", "mlchael",
    "cutemouse83", "higuruma_j", "vladimirovich9000", "jumpingknight20", "athena-pallada",
    "elconceto", "tsoi_dima", "vistagusta", "angelitort", "frederickdermate",
    "abik02", "svodmevko", "kontrajako", "fabsid", "jakebr8",
    "kostik_mostik", "kayra_kamer", "affa19", "epichess95", "niksss2023",
    "andrey11976", "kenkons", "coach_kharun", "papus1234", "feeglood",
    "ciderdrinker", "sillymaster", "targetgm", "duomi_0609", "roshka_yevgeniy",
    "yyoochess", "littleplotkin", "baidetskyi_valentin", "alextriapishko", "timofeevar",
]

ESPERA_429_SEG = 60
REINTENTOS = 5


def _cabeceras() -> dict:
    cabeceras = {"Accept": "application/x-ndjson", "User-Agent": cfg.LICHESS_USER_AGENT}
    if cfg.LICHESS_TOKEN:
        cabeceras["Authorization"] = f"Bearer {cfg.LICHESS_TOKEN}"
    return cabeceras


def _a_ms(momento: datetime | None) -> int | None:
    return int(momento.timestamp() * 1000) if momento else None


def descargar_jugador(usuario: str, salida, desde_ms: int | None = None,
                      hasta_ms: int | None = None, maximo: int | None = None) -> int:
    """Escribe en `salida` (archivo abierto) las partidas crudas de `usuario`, una por línea.

    Devuelve cuántas partidas escribió. Reintenta ante 429 o errores de red.
    """
    parametros = {
        "rated": "true", "opening": "true", "moves": "true", "clocks": "false", "evals": "false",
        "perfType": "bullet,blitz,rapid,classical",
    }
    if desde_ms is not None:
        parametros["since"] = desde_ms
    if hasta_ms is not None:
        parametros["until"] = hasta_ms
    if maximo is not None:
        parametros["max"] = maximo

    for intento in range(1, REINTENTOS + 1):
        lineas = []
        try:
            with requests.get(URL_PARTIDAS.format(usuario=usuario), params=parametros,
                              headers=_cabeceras(), stream=True, timeout=60) as respuesta:
                if respuesta.status_code == 429:
                    print(f"  {usuario}: 429, esperando {ESPERA_429_SEG} s")
                    time.sleep(ESPERA_429_SEG)
                    continue
                respuesta.raise_for_status()
                for linea in respuesta.iter_lines(decode_unicode=True):
                    if linea:
                        lineas.append(linea)
        except requests.RequestException as error:
            print(f"  {usuario}: error ({error}), intento {intento}/{REINTENTOS}")
            time.sleep(10 * intento)
            continue
        # Se escribe solo al terminar, así un corte a mitad no deja partidas a medias
        for linea in lineas:
            salida.write(linea + "\n")
        return len(lineas)

    raise RuntimeError(f"No se pudo descargar {usuario} tras {REINTENTOS} intentos")


def extraer_partidas(desde: datetime | None, hasta: datetime | None) -> str:
    """FUNCIÓN DEL CONTRATO.

    Descarga las partidas jugadas entre `desde` y `hasta` (UTC) por los jugadores de
    JUGADORES y devuelve la ruta del archivo JSONL crudo que escribió.
    """
    cfg.DIR_LOTES.mkdir(parents=True, exist_ok=True)
    nombre = f"crudo_{desde:%Y%m%d_%H%M}.jsonl" if desde else "crudo_inicial.jsonl"
    ruta = cfg.DIR_LOTES / nombre
    temporal = ruta.with_suffix(".jsonl.parcial")

    total = 0
    with open(temporal, "w", encoding="utf-8") as salida:
        for usuario in JUGADORES:
            n = descargar_jugador(usuario, salida, _a_ms(desde), _a_ms(hasta))
            total += n
            print(f"  {usuario}: {n} partidas")
    Path(temporal).replace(ruta)  # reejecutar sobrescribe el lote, no lo duplica

    print(f"Extracción: {total} partidas de {len(JUGADORES)} jugadores en {ruta}")
    return str(ruta)
