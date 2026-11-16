"""Descarga inicial: ~1,500 partidas de cada jugador de JUGADORES (≈ 60,000).

Responsable: Integrante 1. Se corre una sola vez, fuera del DAG. Solo descarga; la
limpieza y la carga en las bases las hace después el Coordinador.

    python -m extraccion.carga_inicial                      # los 40 jugadores
    python -m extraccion.carga_inicial --desde 0 --hasta 20 --salida crudo_parte1.jsonl

Cada jugador se guarda primero en datos/lotes/inicial/<usuario>.jsonl. Si la descarga se
corta, al volver a correrla se saltan los jugadores ya completos. Al final se unen todos
en datos/lotes/<salida> (por defecto crudo_inicial.jsonl).
"""

import argparse
import time

from comun import configuracion as cfg
from extraccion.extraer import JUGADORES, descargar_jugador

MAXIMO_POR_JUGADOR = 1500


def main() -> None:
    parser = argparse.ArgumentParser(description="Descarga inicial de partidas de Lichess")
    parser.add_argument("--desde", type=int, default=0, help="índice del primer jugador (incluido)")
    parser.add_argument("--hasta", type=int, default=len(JUGADORES), help="índice del último jugador (excluido)")
    parser.add_argument("--maximo", type=int, default=MAXIMO_POR_JUGADOR, help="partidas por jugador")
    parser.add_argument("--salida", default="crudo_inicial.jsonl", help="archivo final en datos/lotes/")
    args = parser.parse_args()

    jugadores = JUGADORES[args.desde:args.hasta]
    carpeta = cfg.DIR_LOTES / "inicial"
    carpeta.mkdir(parents=True, exist_ok=True)
    inicio = time.time()

    for i, usuario in enumerate(jugadores, 1):
        completo = carpeta / f"{usuario}.jsonl"
        if completo.exists():
            print(f"[{i}/{len(jugadores)}] {usuario}: ya estaba, se salta")
            continue
        parcial = carpeta / f"{usuario}.jsonl.parcial"
        with open(parcial, "w", encoding="utf-8") as salida:
            n = descargar_jugador(usuario, salida, maximo=args.maximo)
        parcial.replace(completo)
        minutos = (time.time() - inicio) / 60
        print(f"[{i}/{len(jugadores)}] {usuario}: {n} partidas ({minutos:.1f} min)", flush=True)

    ruta_final = cfg.DIR_LOTES / args.salida
    total = 0
    with open(ruta_final, "w", encoding="utf-8") as final:
        for usuario in jugadores:
            with open(carpeta / f"{usuario}.jsonl", encoding="utf-8") as parte:
                for linea in parte:
                    final.write(linea)
                    total += 1
    print(f"Listo: {total} partidas en {ruta_final}")


if __name__ == "__main__":
    main()
