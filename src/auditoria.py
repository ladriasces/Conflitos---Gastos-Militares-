"""Auditoria de layout das figuras: nada cortado, nada sobreposto, nada ilegível.

Uso: python -m src.auditoria        (regera todas as figuras e imprime o laudo)

`auditar(fig, nome, fmt)` é chamada por `graficos.salvar` em toda figura, nos
dois formatos. Ela mede, em pixels finais, a caixa de cada texto e verifica:

1. margem de segurança: nenhum texto ou legenda encosta na borda da imagem;
2. texto x texto: nenhuma sobreposição entre rótulos, títulos, eixos e legendas;
3. texto x barra: um rótulo ou está inteiro dentro da barra ou inteiro fora;
4. texto x linha de dados: rótulo não cruza nem encobre linha de série;
5. texto x ponto: rótulo não cobre marcador;
6. tamanho mínimo de fonte no formato Instagram (legibilidade no celular);
7. layout: o matplotlib conseguiu encaixar os eixos na área disponível;
8. arquivo: o PNG tem exatamente as dimensões esperadas.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

import numpy as np
from matplotlib.collections import PathCollection
from matplotlib.patches import Rectangle
from matplotlib.path import Path as Caminho
from matplotlib.text import Annotation, Text
from matplotlib.transforms import Bbox

PROBLEMAS: list[str] = []
FONTE_MINIMA_PX = {"insta": 20}       # altura nominal da fonte na imagem final de 1080 px
MARGEM = {"insta": (0.030, 0.020), "wide": (0.020, 0.018)}   # fração da largura / da altura


def caixa_texto(t: Text, r) -> Bbox:
    """Caixa só do texto (em anotações, sem a linha-guia)."""
    if isinstance(t, Annotation):
        t.update_positions(r)
        return Text.get_window_extent(t, r)
    return t.get_window_extent(r)


def _encolher(b: Bbox, d: float) -> Bbox:
    return Bbox.from_extents(b.x0 + d, b.y0 + d, max(b.x1 - d, b.x0 + d), max(b.y1 - d, b.y0 + d))


def _rotulos_eixo(eixo) -> list[Text]:
    lo, hi = sorted(eixo.get_view_interval())
    tol = (hi - lo) * 1e-9
    return [rot for tick in eixo.get_major_ticks() for rot in (tick.label1, tick.label2)
            if lo - tol <= tick.get_loc() <= hi + tol and rot.get_visible() and rot.get_text().strip()]


def _textos(fig) -> list[Text]:
    achados = list(fig.texts)
    for leg in fig.legends:
        achados += leg.get_texts()
    for ax in fig.axes:
        achados += list(ax.texts) + [ax.title, ax._left_title, ax._right_title, ax.xaxis.label, ax.yaxis.label]
        achados += _rotulos_eixo(ax.xaxis) + _rotulos_eixo(ax.yaxis)
        if ax.get_legend() is not None:
            achados += ax.get_legend().get_texts()
    return [t for t in achados if t.get_visible() and t.get_text().strip()]


def _trechos(linha) -> list[np.ndarray]:
    """Pontos da linha em pixels, separados onde há lacuna (NaN) nos dados."""
    xy = linha.get_transform().transform(np.column_stack(linha.get_data()).astype(float))
    validos = np.isfinite(xy).all(axis=1)
    trechos, atual = [], []
    for ponto, ok in zip(xy, validos):
        if ok:
            atual.append(ponto)
        elif atual:
            trechos.append(np.array(atual)); atual = []
    if atual:
        trechos.append(np.array(atual))
    return trechos


def _pontos(ax, dpi: float) -> list[Bbox]:
    """Caixas dos marcadores (dispersão e linhas com marcador)."""
    caixas = []
    for col in ax.collections:
        if isinstance(col, PathCollection) and len(col.get_offsets()):
            xy = col.get_offset_transform().transform(col.get_offsets())
            raio = np.sqrt(np.resize(col.get_sizes(), len(xy))) / 2 * dpi / 72
            caixas += [Bbox.from_extents(x - q, y - q, x + q, y + q) for (x, y), q in zip(xy, raio * 0.8)]
    for linha in ax.lines:
        if linha.get_marker() not in (None, "None", "", " ") and linha.get_visible():
            q = linha.get_markersize() / 2 * dpi / 72 * 0.8
            for trecho in _trechos(linha):
                caixas += [Bbox.from_extents(x - q, y - q, x + q, y + q) for x, y in trecho]
    return caixas


def auditar(fig, nome: str, fmt: str) -> list[str]:
    fig.draw_without_rendering()
    r = fig.canvas.get_renderer()
    larg, alt, dpi = fig.bbox.width, fig.bbox.height, fig.dpi
    u = dpi / 150                                    # 1 px no formato Instagram
    mx, my = MARGEM[fmt][0] * larg, MARGEM[fmt][1] * alt
    achados: list[str] = []
    rotulo = lambda t: repr(t.get_text().replace("\n", " ")[:38])

    textos = _textos(fig)
    caixas = [caixa_texto(t, r) for t in textos]

    for aviso in getattr(fig, "_avisos_layout", []):
        achados.append(f"layout: {aviso}")

    for t, b in zip(textos, caixas):
        if b.x0 < mx or b.x1 > larg - mx or b.y0 < my or b.y1 > alt - my:
            achados.append(f"fora da margem de segurança: {rotulo(t)}")
        px = t.get_fontsize() * dpi / 72
        if px < FONTE_MINIMA_PX.get(fmt, 0):
            achados.append(f"fonte pequena ({px:.0f}px): {rotulo(t)}")
    for leg in list(fig.legends) + [ax.get_legend() for ax in fig.axes if ax.get_legend() is not None]:
        b = leg.get_window_extent(r)
        if b.x0 < mx or b.x1 > larg - mx or b.y0 < my or b.y1 > alt - my:
            achados.append("legenda fora da margem de segurança")

    justas = [_encolher(b, 1.5 * u) for b in caixas]
    for i in range(len(textos)):
        for j in range(i + 1, len(textos)):
            if textos[i] is not textos[j] and justas[i].overlaps(justas[j]):
                achados.append(f"textos sobrepostos: {rotulo(textos[i])} x {rotulo(textos[j])}")

    for ax in fig.axes:
        area = ax.get_window_extent(r)
        barras = []
        for p in ax.patches:
            if isinstance(p, Rectangle) and p.get_visible() and (p.get_alpha() is None or p.get_alpha() >= 0.5):
                b = Bbox.intersection(p.get_window_extent(r), area)
                if b is not None and b.width > 1 and b.height > 1:
                    barras.append(b)
        linhas = [l for l in ax.lines if l.get_visible() and l.get_linewidth() >= 1.5 and len(l.get_xdata()) > 1]
        marcadores = _pontos(ax, dpi)
        for t, b in zip(textos, justas):
            for barra in barras:
                dentro = barra.x0 <= b.x0 and b.x1 <= barra.x1 and barra.y0 <= b.y0 and b.y1 <= barra.y1
                if b.overlaps(barra) and not dentro:
                    achados.append(f"texto sobre barra: {rotulo(t)}"); break
            for linha in linhas:
                if any(len(tr) > 1 and Caminho(tr).intersects_bbox(b, filled=False) for tr in _trechos(linha)):
                    achados.append(f"texto sobre linha de dados: {rotulo(t)}"); break
            if any(b.overlaps(m) for m in marcadores):
                achados.append(f"texto sobre marcador: {rotulo(t)}")

    achados = list(dict.fromkeys(achados))
    PROBLEMAS.extend(f"{nome} [{fmt}] {a}" for a in achados)
    return achados


def conferir_arquivo(arquivo: Path, largura: int, altura: int, nome: str, fmt: str) -> None:
    with open(arquivo, "rb") as f:
        cabecalho = f.read(24)
    w, h = struct.unpack(">II", cabecalho[16:24])
    if (w, h) != (largura, altura):
        PROBLEMAS.append(f"{nome} [{fmt}] arquivo com {w}x{h}px; esperado {largura}x{altura}px")


def main() -> int:
    # Executado com `python -m`, este arquivo vira o módulo __main__; os achados
    # ficam na cópia importada por graficos (src.auditoria), e é ela que se lê aqui.
    from . import auditoria as registro
    from . import graficos

    registro.PROBLEMAS.clear()
    geradas = graficos.main()
    print(f"\n=== Auditoria de layout: {len(geradas)} figuras x {len(graficos.FORMATOS)} formatos ===")
    if registro.PROBLEMAS:
        for p in registro.PROBLEMAS:
            print("  [X]", p)
        print(f"{len(registro.PROBLEMAS)} problema(s) encontrado(s).")
        return 1
    print("Nenhum texto cortado, sobreposto ou abaixo do tamanho mínimo. Dimensões dos arquivos conferidas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
