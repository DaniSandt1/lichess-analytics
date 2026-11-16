"""Extracción desde la API de Lichess.

Responsable: Integrante 1.
Estado: PLANTILLA. Hoy devuelve la muestra para que el DAG corra de punta a punta.

Qué tiene que hacer (detalles en CONTRATO.md, sección 5):
- Pedir la lista de jugadores a https://lichess.org/api/player/top/50/blitz
  (o usar una lista fija en este archivo, por ejemplo 40 jugadores).
- Para cada jugador, GET https://lichess.org/api/games/user/{usuario} con:
    cabeceras: Accept: application/x-ndjson y User-Agent: cfg.LICHESS_USER_AGENT
               (sin User-Agent Lichess responde 404; con LICHESS_TOKEN agreguen Authorization: Bearer ...)
    parámetros: since y until en MILISEGUNDOS, rated=true, opening=true, moves=true,
                perfType=bullet,blitz,rapid,classical, clocks=false, evals=false
- Bajar los jugadores de uno en uno (no en paralelo). Si responde 429, esperar 60 s y reintentar.
- Escribir todo en datos/lotes/crudo_<desde>.jsonl, una partida por línea, tal cual llega.
- Carga inicial (una sola vez, fuera del DAG): mismo código con desde=None y max=1500
  por jugador, para llegar a ~60,000 partidas.
"""

from datetime import datetime

from comun import configuracion as cfg


def extraer_partidas(desde: datetime | None, hasta: datetime | None) -> str:
    """FUNCIÓN DEL CONTRATO.

    Descarga las partidas jugadas entre `desde` y `hasta` (UTC) y devuelve la ruta
    del archivo JSONL crudo que escribió.
    """
    print(f"[PENDIENTE - Integrante 1] extraer_partidas(desde={desde}, hasta={hasta})")
    print("[PENDIENTE - Integrante 1] devolviendo la muestra mientras tanto")
    return str(cfg.DIR_MUESTRA / "partidas_crudas.jsonl")
