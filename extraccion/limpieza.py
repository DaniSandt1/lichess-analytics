"""Validación y limpieza: partida cruda de la API de Lichess -> registro limpio del contrato.

Responsable: Integrante 1. La versión inicial ya funciona (la usó el coordinador para
generar datos/muestra/partidas_limpias.jsonl). Integrante 1 puede mejorarla, pero el
formato de salida es el de CONTRATO.md y no se cambia sin avisar.

Uso manual:
    python -m extraccion.limpieza datos/muestra/partidas_crudas.jsonl datos/muestra/partidas_limpias.jsonl
"""

import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from comun import configuracion as cfg
from comun.contrato import RITMOS, validar_registro

# Estados en los que una partida sin "winner" terminó en tablas.
ESTADOS_TABLAS = {"draw", "stalemate", "outoftime", "timeout", "insufficientMaterialClaim"}


def limpiar_partida(cruda: dict) -> tuple[dict | None, str | None]:
    """Convierte una partida cruda en un registro limpio.

    Devuelve (registro, None) si es válida, o (None, motivo_de_descarte) si no.
    """
    if cruda.get("variant") != "standard":
        return None, "variante_no_standard"  # chess960, horde... no traen apertura
    if not cruda.get("rated"):
        return None, "no_rankeada"
    ritmo = cruda.get("speed")
    if ritmo not in RITMOS:
        return None, "ritmo_no_soportado"

    blancas = cruda.get("players", {}).get("white", {})
    negras = cruda.get("players", {}).get("black", {})
    if "user" not in blancas or "user" not in negras:
        return None, "jugador_anonimo_o_ia"
    if "rating" not in blancas or "rating" not in negras:
        return None, "sin_rating"

    apertura = cruda.get("opening")
    if not apertura or not apertura.get("eco"):
        return None, "sin_apertura"

    ganador_api = cruda.get("winner")
    estado = cruda.get("status", "")
    if ganador_api == "white":
        ganador = "blancas"
    elif ganador_api == "black":
        ganador = "negras"
    elif estado in ESTADOS_TABLAS:
        ganador = "tablas"
    else:
        return None, "sin_resultado"  # abortada, en curso, trampa...

    medias_jugadas = len(cruda.get("moves", "").split())
    if medias_jugadas < 2:
        return None, "sin_jugadas"

    inicio = datetime.fromtimestamp(cruda["createdAt"] / 1000, tz=timezone.utc)
    reloj = cruda.get("clock", {})
    nombre_apertura = apertura.get("name", "Desconocida")

    registro = {
        "id_partida": cruda["id"],
        "fecha": inicio.strftime("%Y-%m-%d"),
        "fecha_hora": inicio.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ritmo": ritmo,
        "tiempo_inicial_seg": int(reloj.get("initial", 0)),
        "incremento_seg": int(reloj.get("increment", 0)),
        "origen": cruda.get("source", "desconocido"),
        "jugador_blancas": blancas["user"]["id"],
        "nombre_blancas": blancas["user"].get("name", blancas["user"]["id"]),
        "titulo_blancas": blancas["user"].get("title"),
        "rating_blancas": int(blancas["rating"]),
        "dif_rating_blancas": blancas.get("ratingDiff"),
        "jugador_negras": negras["user"]["id"],
        "nombre_negras": negras["user"].get("name", negras["user"]["id"]),
        "titulo_negras": negras["user"].get("title"),
        "rating_negras": int(negras["rating"]),
        "dif_rating_negras": negras.get("ratingDiff"),
        "ganador": ganador,
        "estado": estado,
        "codigo_eco": apertura["eco"],
        "nombre_apertura": nombre_apertura,
        "familia_apertura": nombre_apertura.split(":")[0].strip(),
        "cantidad_movimientos": math.ceil(medias_jugadas / 2),
    }
    validar_registro(registro)
    return registro, None


def validar_y_limpiar(ruta_cruda: str, ruta_salida: str | None = None) -> str:
    """FUNCIÓN DEL CONTRATO. Lee un JSONL crudo y escribe el JSONL limpio.

    - Descarta las partidas que no cumplen las reglas de CONTRATO.md.
    - Elimina duplicados por id_partida.
    - Imprime cuántas se descartaron y por qué (sale en el log de Airflow).

    Devuelve la ruta del archivo limpio.
    """
    ruta_cruda = Path(ruta_cruda)
    if ruta_salida is None:
        cfg.DIR_LOTES.mkdir(parents=True, exist_ok=True)
        nombre = ruta_cruda.name.replace("crudo", "limpio")
        if nombre == ruta_cruda.name:
            nombre = "limpio_" + nombre
        ruta_salida = cfg.DIR_LOTES / nombre
    ruta_salida = Path(ruta_salida)

    vistos: set[str] = set()
    descartes: Counter = Counter()
    validas = 0
    with ruta_cruda.open(encoding="utf-8") as entrada, ruta_salida.open("w", encoding="utf-8") as salida:
        for linea in entrada:
            if not linea.strip():
                continue
            try:
                cruda = json.loads(linea)
            except json.JSONDecodeError:
                descartes["json_invalido"] += 1
                continue
            registro, motivo = limpiar_partida(cruda)
            if registro is None:
                descartes[motivo] += 1
                continue
            if registro["id_partida"] in vistos:
                descartes["duplicada"] += 1
                continue
            vistos.add(registro["id_partida"])
            salida.write(json.dumps(registro, ensure_ascii=False) + "\n")
            validas += 1

    print(f"[validar_y_limpiar] válidas: {validas}; descartadas: {sum(descartes.values())} {dict(descartes)}")
    print(f"[validar_y_limpiar] archivo limpio: {ruta_salida}")
    return str(ruta_salida)


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        sys.exit("Uso: python -m extraccion.limpieza <crudo.jsonl> [limpio.jsonl]")
    validar_y_limpiar(*sys.argv[1:])
