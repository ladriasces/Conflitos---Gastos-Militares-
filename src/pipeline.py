"""Roda o projeto inteiro: download -> limpeza -> figuras -> conferência.

Uso: python -m src.pipeline [--forcar]

Sem --forcar, arquivos já presentes em data/raw não são baixados de novo e os
anos do Sinesp já agregados não são reprocessados.
"""
from __future__ import annotations

import sys

from . import download, graficos, limpeza, verifica


def main(forcar: bool = False) -> None:
    print("--- 1/4 download ---")
    fontes = download.main(forcar)
    print("--- 2/4 limpeza ---")
    limpeza.main()
    print("--- 3/4 figuras ---")
    geradas = graficos.main()
    print("--- 4/4 conferência dos números ---")
    verifica.main()
    print("\nFontes baixadas:", fontes)
    print("Figuras geradas:", geradas, "| puladas:", sorted(set(graficos.FIGURAS) - set(geradas)))


if __name__ == "__main__":
    main(forcar="--forcar" in sys.argv)
