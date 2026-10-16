"""Figuras do projeto. Uma função por figura; cada uma lê só data/processed.

Uso: python -m src.graficos            (gera todas)
     python -m src.graficos 1 2 5      (gera só as indicadas)
     python -m src.auditoria           (gera todas e emite o laudo de layout)

Cada figura sai em dois formatos:
- 'wide'  : 16:9, 3840x2160 px (PNG) + SVG, para projetor;
- 'insta' : 4:5, 1080x1350 px (PNG), para o feed do Instagram. Tipografia maior,
  subtítulo e rodapé mais curtos, painéis empilhados.

O layout é medido, não estimado: títulos são quebrados pela largura real do
texto, os eixos são encaixados na área livre (tight_layout) e os limites dos
eixos são alargados até os rótulos caberem. Ao salvar, `auditoria.auditar`
confere se sobrou algum texto cortado ou sobreposto.
"""
from __future__ import annotations

import sys
import time
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as efeitos
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.path import Path as Caminho
from matplotlib.ticker import MaxNLocator
from matplotlib.transforms import Bbox

from . import auditoria
from . import config as c
from .auditoria import caixa_texto

# --- Estilo -------------------------------------------------------------------
SUPERFICIE = "#fcfcfb"
TINTA, TINTA2, TINTA3 = "#0b0b0b", "#52514e", "#6b6a66"
GRADE = "#e4e3df"
NEUTRO = "#b9b8b2"
# Paleta categórica em ordem fixa (validada para daltonismo em pares adjacentes).
AZUL, LARANJA, AGUA, AMARELO, MAGENTA, VERDE, VIOLETA, VERMELHO = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948")
AZUL_CLARO = "#9ec5f4"

# Tamanhos em pontos. No 'insta' (150 dpi), 13 pt = 27 px numa imagem de 1080 px.
FORMATOS = {
    "wide": dict(figsize=(12.8, 7.2), dpi=300, base=13, titulo=21, sub=14, rodape=10.5, mx=0.04, my=0.04),
    "insta": dict(figsize=(7.2, 9.0), dpi=150, base=13, titulo=21, sub=14, rodape=10, mx=0.05, my=0.04),
}

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"],
    "figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE, "savefig.facecolor": SUPERFICIE,
    "axes.edgecolor": GRADE, "axes.linewidth": 0.8, "axes.grid": True, "axes.axisbelow": True,
    "grid.color": GRADE, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "xtick.color": TINTA2, "ytick.color": TINTA2, "xtick.major.size": 0, "ytick.major.size": 0,
    "xtick.major.pad": 7, "ytick.major.pad": 5,
    "axes.labelcolor": TINTA2, "text.color": TINTA, "legend.frameon": False,
    "svg.fonttype": "none",
})

NOTA_TIV = "TIV (trend-indicator value) mede volume de capacidade militar transferida; não é valor monetário."
NOTA_TIV_CURTA = "TIV mede volume de armas transferidas; não é valor monetário."


def num(x: float, casas: int = 0) -> str:
    """Número no padrão brasileiro (1.234,5)."""
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _sujeito(iso3: str, singular: str, plural: str) -> str:
    """'EUA vendem' / 'França vende': nome do país já com o verbo concordando."""
    return f"EUA {plural}" if iso3 == "USA" else f"{c.nome_pt(iso3)} {singular}"


def _por_formato(valor, fmt: str) -> str:
    """Aceita um texto único ou {'wide': ..., 'insta': ...}."""
    return valor[fmt] if isinstance(valor, dict) else valor


def _ler(nome: str) -> pd.DataFrame:
    return pd.read_csv(c.PROCESSED / nome)


# --- Layout medido ------------------------------------------------------------
def _quebrar(fig, texto: str, largura_px: float, **estilo) -> str:
    """Quebra o texto pela largura real em pixels e evita última linha órfã."""
    r = fig.canvas.get_renderer()
    sonda = fig.text(0, 0, "", **estilo)

    def largura(s: str) -> float:
        sonda.set_text(s)
        return sonda.get_window_extent(r).width

    def quebrar(limite: float) -> list[str]:
        linhas, atual = [], ""
        for palavra in texto.split():
            tentativa = f"{atual} {palavra}".strip()
            if atual and largura(tentativa) > limite:
                linhas.append(atual)
                atual = palavra
            else:
                atual = tentativa
        return linhas + [atual]

    linhas = quebrar(largura_px)
    for fator in (0.92, 0.84, 0.76):          # reequilibra sem aumentar o número de linhas
        if len(linhas) < 2 or largura(linhas[-1]) >= 0.4 * max(largura(l) for l in linhas):
            break
        tentativa = quebrar(largura_px * fator)
        if len(tentativa) == len(linhas):
            linhas = tentativa
    sonda.remove()
    return "\n".join(linhas)


def nova_figura(fmt: str, titulo: str, subtitulo, fonte, nlin: int = 1, ncol: int = 1,
                empilhar_no_insta: bool = True, **kw):
    """Cria a figura com título, subtítulo e rodapé; devolve (fig, eixos).

    `subtitulo` e `fonte` aceitam um texto ou um dicionário por formato. A área
    livre para os eixos fica guardada em fig._y_topo e fig._y_base.
    """
    f = FORMATOS[fmt]
    plt.rcParams["font.size"] = f["base"]
    if fmt == "insta" and empilhar_no_insta and ncol > 1:
        nlin, ncol = nlin * ncol, 1
    fig, eixos = plt.subplots(nlin, ncol, figsize=f["figsize"], dpi=f["dpi"], squeeze=False, **kw)
    fig._fmt = fmt
    r = fig.canvas.get_renderer()
    alt = fig.bbox.height
    largura = fig.bbox.width * (1 - 2 * f["mx"])

    y = 1 - f["my"]
    for texto, estilo, folga in [
            (titulo, dict(fontsize=f["titulo"], fontweight="bold", color=TINTA, linespacing=1.12), 0.012),
            (_por_formato(subtitulo, fmt), dict(fontsize=f["sub"], color=TINTA2, linespacing=1.28), 0.0)]:
        t = fig.text(f["mx"], y, _quebrar(fig, texto, largura, **estilo), va="top", ha="left", **estilo)
        y -= t.get_window_extent(r).height / alt + folga
    fig._y_topo = y - 0.02

    estilo = dict(fontsize=f["rodape"], color=TINTA3, linespacing=1.3)
    y0 = f["my"] * 0.75
    t = fig.text(f["mx"], y0, _quebrar(fig, "Fonte: " + _por_formato(fonte, fmt), largura, **estilo),
                 va="bottom", ha="left", **estilo)
    fig._y_base = y0 + t.get_window_extent(r).height / alt + 0.022
    return fig, eixos.ravel()


def legenda_topo(fig, itens: list, ncol: int | None = None) -> None:
    """Legenda entre o subtítulo e o gráfico; reduz colunas até caber na largura.

    `itens` é uma lista de artistas com rótulo (Patch ou Line2D).
    """
    f = FORMATOS[fig._fmt]
    r = fig.canvas.get_renderer()
    largura = fig.bbox.width * (1 - 2 * f["mx"])
    ncol = ncol or len(itens)
    while True:
        leg = fig.legend(handles=itens, loc="upper left", bbox_to_anchor=(f["mx"], fig._y_topo), ncol=ncol,
                         fontsize=f["base"] - 1.5, handlelength=1.4, handleheight=0.9, handletextpad=0.5,
                         columnspacing=1.6, labelspacing=0.35, borderpad=0, borderaxespad=0)
        if leg.get_window_extent(r).width <= largura or ncol == 1:
            break
        leg.remove()
        ncol -= 1
    fig._y_topo -= leg.get_window_extent(r).height / fig.bbox.height + 0.02


def ajustar(fig) -> None:
    """Encaixa os eixos (com rótulos e títulos de painel) na área livre da figura."""
    f = FORMATOS[fig._fmt]
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always")
        fig.tight_layout(rect=(f["mx"], fig._y_base, 1 - f["mx"], fig._y_topo), pad=0.15, h_pad=1.5, w_pad=1.8)
    fig._avisos_layout = [str(a.message) for a in avisos]


def _alargar(eixo, ler, definir, antes_px: float, depois_px: float, tamanho_px: float) -> None:
    if antes_px <= 0 and depois_px <= 0:
        return
    tr = eixo.get_transform()                     # respeita escala logarítmica
    s = tr.transform(np.array(ler(), dtype=float))
    por_px = (s[1] - s[0]) / tamanho_px
    novo = np.array([s[0] - max(antes_px, 0) * por_px * 1.15, s[1] + max(depois_px, 0) * por_px * 1.15])
    definir(*tr.inverted().transform(novo))


def caber(ax) -> None:
    """Alarga os limites do eixo até todos os rótulos internos ficarem dentro dele."""
    fig = ax.figure
    folga = 3 * fig.dpi / 150
    for _ in range(8):
        fig.draw_without_rendering()
        r = fig.canvas.get_renderer()
        area = ax.get_window_extent(r)
        caixas = [caixa_texto(t, r) for t in ax.texts
                  if t.get_visible() and t.get_text().strip() and not getattr(t, "_livre", False)]
        if not caixas:
            return
        esq = area.x0 - min(b.x0 for b in caixas) + folga
        dire = max(b.x1 for b in caixas) - area.x1 + folga
        baixo = area.y0 - min(b.y0 for b in caixas) + folga
        cima = max(b.y1 for b in caixas) - area.y1 + folga
        if max(esq, dire, baixo, cima) <= 0:
            return
        _alargar(ax.xaxis, ax.get_xlim, ax.set_xlim, esq, dire, area.width)
        _alargar(ax.yaxis, ax.get_ylim, ax.set_ylim, baixo, cima, area.height)


def _halo(t):
    """Contorno na cor do fundo: mantém o rótulo legível sobre grade e linhas finas."""
    t.set_path_effects([efeitos.withStroke(linewidth=3, foreground=SUPERFICIE)])
    return t


def _chip(t):
    """Fundo opaco: o rótulo é desenhado por cima das linhas, de propósito."""
    t.set_bbox(dict(facecolor=SUPERFICIE, edgecolor="none", pad=1.5, alpha=0.92))
    t.set_zorder(6)
    return t


def _espalhar(ax, valores: list[float], fonte: float) -> list[float]:
    """Posições verticais para rótulos de fim de linha, sem sobreposição (valores em ordem crescente)."""
    y0, y1 = ax.get_ylim()
    minimo = 1.5 * (fonte / 72 * ax.figure.dpi) / ax.get_window_extent().height * (y1 - y0)
    ys: list[float] = []
    for v in valores:
        ys.append(max(v, ys[-1] + minimo) if ys else v)
    desvio = (sum(ys) - sum(valores)) / len(ys)       # recentra o bloco em torno dos valores
    ys = [y - desvio for y in ys]
    desvio = max(0.0, y0 + minimo / 2 - ys[0]) - max(0.0, ys[-1] - (y1 - minimo / 2))
    return [y + desvio for y in ys]


def rotulos_fim(ax, itens: list[tuple[float, str, str]], x_fim: float) -> None:
    """Rótulos no fim das linhas, com guia, abrindo à direita só o espaço necessário.

    `itens` = [(valor, texto, cor da série)].
    """
    fig = ax.figure
    tam = plt.rcParams["font.size"] - 1.5
    itens = sorted(itens)
    feitos: list = []
    for _ in range(6):
        for a in feitos:
            a.remove()
        fig.draw_without_rendering()
        r = fig.canvas.get_renderer()
        area = ax.get_window_extent(r)
        x0, x1 = ax.get_xlim()
        por_px = (x1 - x0) / area.width
        ys = _espalhar(ax, [v for v, _, _ in itens], tam)
        feitos = [_halo(ax.annotate(texto, xy=(x_fim, v), xytext=(x_fim + 20 * fig.dpi / 150 * por_px, y),
                                    va="center", ha="left", fontsize=tam, fontweight="bold", color=TINTA,
                                    arrowprops=dict(arrowstyle="-", color=cor, lw=1.2, shrinkA=3, shrinkB=3)))
                  for (v, texto, cor), y in zip(itens, ys)]
        sobra = max(caixa_texto(a, r).x1 for a in feitos) - area.x1 + 4 * fig.dpi / 150
        if sobra <= 0:
            break
        ax.set_xlim(x0, x1 + sobra * por_px * 1.1)


def rotular_referencia(ax, y: float, texto: str) -> None:
    """Rótulo de uma linha horizontal de referência, no primeiro trecho que não encobre séries em destaque."""
    fig = ax.figure
    tam = plt.rcParams["font.size"] - 2
    fig.draw_without_rendering()
    r = fig.canvas.get_renderer()
    folga = 4 * fig.dpi / 150
    series = [Caminho(tr) for l in ax.lines if l.get_visible() and l.get_linewidth() >= 1.5
              for tr in auditoria._trechos(l) if len(tr) > 1]
    vizinhos = [caixa_texto(t, r) for t in ax.texts if t.get_visible() and t.get_text().strip()]
    opcoes = [(fx, dy, va) for dy, va in ((4, "bottom"), (-4, "top")) for fx in np.arange(0.01, 0.8, 0.02)]
    for fx, dy, va in opcoes + [(0.01, 4, "bottom")]:      # última opção: canto esquerdo, mesmo sem espaço livre
        a = ax.annotate(texto, (fx, y), xycoords=ax.get_yaxis_transform(), xytext=(0, dy),
                        textcoords="offset points", ha="left", va=va, color=TINTA2, fontsize=tam)
        b = caixa_texto(a, r)
        b = Bbox.from_extents(b.x0 - folga, b.y0 - folga, b.x1 + folga, b.y1 + folga)
        if not any(s.intersects_bbox(b, filled=False) for s in series) and not any(b.overlaps(v) for v in vizinhos):
            break
        a.remove()
    else:
        a = ax.annotate(texto, (0.01, y), xycoords=ax.get_yaxis_transform(), xytext=(0, 4),
                        textcoords="offset points", ha="left", va="bottom", color=TINTA2, fontsize=tam)
    _chip(a)


def rotular_pontos(ax, itens: list[tuple[float, float, str]], ocupadas: list | None = None) -> list:
    """Rótulos de pontos de dispersão na primeira posição livre ao redor de cada ponto."""
    fig = ax.figure
    tam = plt.rcParams["font.size"] - 1.5
    fig.draw_without_rendering()
    r = fig.canvas.get_renderer()
    area = ax.get_window_extent(r)
    ocupadas = list(ocupadas or []) + auditoria._pontos(ax, fig.dpi)
    opcoes = [(6, 4, "left", "bottom"), (6, -4, "left", "top"), (-6, 4, "right", "bottom"),
              (-6, -4, "right", "top"), (0, 8, "center", "bottom"), (0, -8, "center", "top")]
    for x, y, texto in itens:
        for dx, dy, ha, va in opcoes:
            a = ax.annotate(texto, (x, y), xytext=(dx, dy), textcoords="offset points", ha=ha, va=va, fontsize=tam)
            b = caixa_texto(a, r)
            if (area.x0 <= b.x0 and b.x1 <= area.x1 and area.y0 <= b.y0 and b.y1 <= area.y1
                    and not any(b.overlaps(o) for o in ocupadas)):
                ocupadas.append(b)
                _halo(a)
                break
            a.remove()
        else:
            print(f"   [aviso] sem posição livre para o rótulo '{texto}'; ponto fica sem nome")
    return ocupadas


def salvar(fig, nome: str, fmt: str) -> None:
    f = FORMATOS[fmt]
    ajustar(fig)
    for achado in auditoria.auditar(fig, nome, fmt):
        print(f"   [auditoria] {nome} [{fmt}] {achado}")
    sufixo = "" if fmt == "wide" else "_instagram"
    png = c.FIGURAS / f"{nome}{sufixo}.png"
    for arq in [png] + ([c.FIGURAS / f"{nome}.svg"] if fmt == "wide" else []):
        # Em pasta sincronizada (OneDrive), o arquivo pode estar travado por alguns
        # segundos enquanto a versão anterior sobe; tenta de novo antes de desistir.
        for tentativa in range(8):
            try:
                fig.savefig(arq)
                break
            except OSError:
                if tentativa == 7:
                    raise
                time.sleep(2)
    auditoria.conferir_arquivo(png, round(f["figsize"][0] * f["dpi"]), round(f["figsize"][1] * f["dpi"]), nome, fmt)
    plt.close(fig)


def _faixas_periodo(ax, fim: int, rotulos: bool = True) -> None:
    """Destaca pós-2014 (anexação da Crimeia) e pós-2022 (invasão em larga escala)."""
    ax.axvspan(c.ANO_INICIO_FOCO, c.ANO_INVASAO, color=AZUL, alpha=0.07, lw=0, zorder=0)
    ax.axvspan(c.ANO_INVASAO, fim + 0.5, color=AZUL, alpha=0.16, lw=0, zorder=0)
    if not rotulos:
        return
    fig = ax.figure
    ajustar(fig)
    fig.draw_without_rendering()
    r = fig.canvas.get_renderer()
    area = ax.get_window_extent(r)
    estilo = dict(transform=ax.get_xaxis_transform(), color=TINTA2, va="bottom",
                  fontsize=plt.rcParams["font.size"] - 2.5)
    px = lambda ano: ax.transData.transform((ano, 0))[0]
    primeiro = ax.text(c.ANO_INICIO_FOCO, 1.012, f"pós-{c.ANO_INICIO_FOCO}", ha="left", **estilo)
    curto = primeiro.get_window_extent(r).width * 1.15 > px(c.ANO_INVASAO) - px(c.ANO_INICIO_FOCO)
    if curto:                                   # série longa: só o ano cabe sobre a faixa
        primeiro.set_text(str(c.ANO_INICIO_FOCO))
    segundo = ax.text(c.ANO_INVASAO, 1.012, str(c.ANO_INVASAO) if curto else f"pós-{c.ANO_INVASAO}", ha="left", **estilo)
    if px(c.ANO_INVASAO) + segundo.get_window_extent(r).width > area.x1:
        segundo.set_ha("right")                 # encosta na borda direita do eixo em vez de vazar
        segundo.set_x(ax.get_xlim()[1])
    primeiro._livre = segundo._livre = True     # ficam acima do eixo de propósito


def _titulo_painel(ax, texto: str, sobre_faixas: bool = False) -> None:
    p = plt.rcParams["font.size"]
    ax.set_title(texto, loc="left", fontsize=p, color=TINTA2, pad=p + 9 if sobre_faixas else 6)


# --- Figura 1 -----------------------------------------------------------------
def fig01_gasto_mundial(fmt: str):
    reg = _ler("gasto_sipri_regioes.csv")
    mundo = reg[reg["regiao"] == "World"].set_index("ano")["usd_bi_const2024"]
    mundo = mundo.reindex(range(mundo.index.min(), mundo.index.max() + 1))  # lacunas ficam visíveis
    wb = _ler("gasto_banco_mundial.csv")
    pib = wb[wb["iso3"] == "WLD"].set_index("ano")["gasto_pct_pib"].dropna()
    ult = int(mundo.dropna().index.max())
    var14 = (mundo[ult] / mundo[2014] - 1) * 100
    var21 = (mundo[ult] / mundo[2021] - 1) * 100
    sem_dado = [int(a) for a in mundo.index[mundo.isna()]]
    lacuna = f" (sem total mundial em {', '.join(map(str, sem_dado))})" if sem_dado else ""

    fig, (a1, a2) = nova_figura(
        fmt, f"Gasto militar mundial chega a US$ {num(mundo[ult] / 1000, 2)} trilhões em {ult}"
             + (", recorde da série" if mundo.idxmax() == ult else ""),
        {"wide": f"Gasto militar mundial em termos reais cresceu {num(var14)}% desde 2014 e {num(var21)}% desde 2021. "
                 "Como parcela do PIB, porém, segue abaixo dos níveis da Guerra Fria.",
         "insta": f"Alta real de {num(var14)}% desde 2014 e de {num(var21)}% desde 2021. Como parcela do PIB, "
                  "segue abaixo dos níveis da Guerra Fria."},
        {"wide": f"SIPRI Military Expenditure Database (abr. 2026), US$ constantes de 2024, 1988–{ult}{lacuna}; "
                 f"Banco Mundial/WDI, MS.MIL.XPND.GD.ZS (dados do SIPRI), {pib.index.min()}–{pib.index.max()}.",
         "insta": f"SIPRI Military Expenditure Database (2026), US$ constantes de 2024, 1988–{ult}{lacuna}; "
                  f"Banco Mundial/WDI, {pib.index.min()}–{pib.index.max()}."},
        nlin=2, gridspec_kw={"height_ratios": [1.5, 1]})

    a1.plot(mundo.index, mundo.values, color=AZUL, lw=2.4)
    a1.set_ylim(0, mundo.max() * 1.1)
    a1.set_xlim(1987, ult + 0.6)
    a1.yaxis.set_major_formatter(lambda v, _: num(v))
    _titulo_painel(a1, "US$ bilhões, preços constantes de 2024", sobre_faixas=True)
    _faixas_periodo(a1, ult)
    for ano, (dx, ha) in {2014: (0, "center"), 2021: (0, "right"), ult: (3, "right")}.items():
        a1.plot(ano, mundo[ano], "o", color=AZUL, ms=7, mec=SUPERFICIE, mew=1.5)
        _halo(a1.annotate(num(mundo[ano]), (ano, mundo[ano]), xytext=(dx, 10), textcoords="offset points",
                          ha=ha, va="bottom", fontweight="bold"))

    a2.plot(pib.index, pib.values, color=TINTA2, lw=2)
    a2.set_ylim(0, pib.max() * 1.1)
    a2.set_xlim(pib.index.min() - 1.5, ult + 1.5)
    a2.yaxis.set_major_formatter(lambda v, _: num(v, 0) + "%")
    _titulo_painel(a2, "Gasto militar mundial, % do PIB mundial")
    _faixas_periodo(a2, ult, rotulos=False)
    for ano, ha in {int(pib.index.min()): "left", int(pib.index.max()): "right"}.items():
        _halo(a2.annotate(num(pib[ano], 1) + "%", (ano, pib[ano]), xytext=(0, 9), textcoords="offset points",
                          ha=ha, va="bottom", fontweight="bold"))
    ajustar(fig)
    caber(a1)
    caber(a2)
    salvar(fig, "fig01_gasto_mundial", fmt)


# --- Figura 2 -----------------------------------------------------------------
def fig02_otan_pib(fmt: str):
    wb = _ler("gasto_banco_mundial.csv")
    d = wb[wb["iso3"].isin(c.OTAN_EUROPA + ["BRA"]) & (wb["ano"] >= 2005)]
    tab = d.pivot(index="ano", columns="iso3", values="gasto_pct_pib")
    otan = tab[[p for p in c.OTAN_EUROPA if p in tab.columns]]
    sem_dado = [c.nome_pt(p) for p in c.OTAN_EUROPA if p not in tab.columns or tab[p].isna().all()]
    ult = int(otan.dropna(how="all").index.max())
    n14 = int((otan.loc[2014] >= c.META_GALES).sum())
    n_ult = int((otan.loc[ult] >= c.META_GALES).sum())
    n35 = int((otan.loc[ult] >= c.META_HAIA_NUCLEO).sum())
    n_com_dado = int(otan.loc[ult].notna().sum())
    faltam = f"Sem dado: {', '.join(sem_dado)}. " if sem_dado else ""

    fig, (ax,) = nova_figura(
        fmt, f"Rearmamento europeu: de {n14} para {n_ult} aliados acima de 2% do PIB desde 2014",
        {"wide": f"Gasto militar como % do PIB (critério SIPRI), membros europeus da OTAN e Brasil. Em {ult}, {n35} de "
                 f"{n_com_dado} já superavam 3,5%, a parcela de defesa da nova meta de 5% até {c.META_HAIA_ANO} (Haia, 2025).",
         "insta": f"Gasto militar em % do PIB, OTAN europeia e Brasil. Em {ult}, só {n35} de {n_com_dado} aliados "
                  f"superavam 3,5%, a parcela de defesa da nova meta."},
        {"wide": f"Banco Mundial/WDI, MS.MIL.XPND.GD.ZS (dados do SIPRI), 2005–{ult}. A definição de gasto do SIPRI "
                 f"difere da usada pela OTAN, então os valores não coincidem com os relatórios da aliança. {faltam}"
                 "Islândia (sem forças armadas) não incluída; Finlândia e Suécia aparecem em toda a série, embora "
                 "tenham aderido em 2023 e 2024.",
         "insta": f"Banco Mundial/WDI (dados do SIPRI), 2005–{ult}. Critério SIPRI, diferente do usado pela OTAN. "
                  f"{faltam}Sem Islândia. Linhas tracejadas: metas da OTAN de Gales (2014) e Haia (2025)."})
    p = plt.rcParams["font.size"]

    for pais in otan.columns:
        ax.plot(otan.index, otan[pais], color=NEUTRO, lw=0.9, alpha=0.75, zorder=1)
    destaques = [("POL", AZUL), ("DEU", LARANJA), ("FRA", AGUA), ("BRA", VIOLETA)]
    mediana = otan.median(axis=1)
    ax.plot(mediana.index, mediana, color=TINTA, lw=2.6, zorder=4)
    for pais, cor in destaques:
        ax.plot(tab.index, tab[pais], color=cor, lw=2.4, zorder=3, ls="--" if pais == "BRA" else "-")
    legenda_topo(fig, [Line2D([], [], color=TINTA, lw=2.6, label="Mediana da OTAN europeia")]
                 + [Line2D([], [], color=cor, lw=2.4, ls="--" if pais == "BRA" else "-", label=c.nome_pt(pais))
                    for pais, cor in destaques]
                 + [Line2D([], [], color=NEUTRO, lw=0.9, label="Demais membros europeus")])

    ax.set_xlim(2004.6, ult + 0.6)
    ax.set_ylim(0, max(5.45, float(np.nanmax(otan.values)) * 1.05))
    ax.set_xticks(range(2005, ult + 1, 5))
    ax.tick_params(axis="x", pad=7)
    ax.yaxis.set_major_formatter(lambda v, _: num(v, 0) + "%")
    metas = [(c.META_GALES, "2% (Gales, 2014)" if fmt == "wide" else "2% (2014)"),
             (c.META_HAIA_NUCLEO, f"3,5% em defesa, até {c.META_HAIA_ANO}" if fmt == "wide" else f"3,5% (até {c.META_HAIA_ANO})"),
             (c.META_HAIA_TOTAL, f"5% no total, até {c.META_HAIA_ANO}" if fmt == "wide" else f"5% (até {c.META_HAIA_ANO})")]
    ax.hlines([m for m, _ in metas], 2004.6, ult, color=TINTA2, lw=1.1, ls=(0, (4, 3)), zorder=2)
    ax.axvline(c.ANO_INVASAO, color=TINTA3, lw=1, ls=":")
    _chip(ax.annotate("invasão da Ucrânia", (c.ANO_INVASAO, 0), xycoords=ax.get_xaxis_transform(),
                      xytext=(-5, 5), textcoords="offset points", ha="right", va="bottom", color=TINTA2, fontsize=p - 2))

    ajustar(fig)
    rotulos_fim(ax, [(float(mediana[ult]), f"Mediana {num(mediana[ult], 1)}%", TINTA)]
                + [(float(tab[pais].dropna().iloc[-1]), f"{c.nome_pt(pais)} {num(tab[pais].dropna().iloc[-1], 1)}%", cor)
                   for pais, cor in destaques], ult)
    for meta, rot in metas:
        rotular_referencia(ax, meta, rot)
    salvar(fig, "fig02_otan_pib", fmt)


# --- Figura 3 -----------------------------------------------------------------
def fig03_ranking(fmt: str, n: int = 15):
    s = _ler("gasto_sipri_paises.csv").dropna(subset=["usd_mi_const2024"])
    ult = int(s["ano"].max())
    base = ult - 10
    tab = s.pivot_table(index=["pais", "iso3"], columns="ano", values="usd_mi_const2024").reset_index()
    tab = tab.dropna(subset=[ult]).sort_values(ult, ascending=False).reset_index(drop=True)
    tab["posicao"] = tab.index + 1
    topo = tab.head(n)
    if "BRA" not in set(topo["iso3"]):
        topo = pd.concat([topo, tab[tab["iso3"] == "BRA"]])
    topo = topo.assign(var=(topo[ult] / topo[base] - 1) * 100, bi=topo[ult] / 1000,
                       nome=[f"{pos}. {c.nome_pt(i, pz)}" for pos, i, pz in zip(topo["posicao"], topo["iso3"], topo["pais"])])
    topo = topo.iloc[::-1]
    lider = topo.iloc[-1]
    total = _ler("gasto_sipri_regioes.csv").query("regiao == 'World' and ano == @ult")["usd_bi_const2024"].iloc[0]
    maior_var = topo.sort_values("var").iloc[-1]
    var_bra = num(topo.set_index("iso3")["var"]["BRA"]).replace("-", "−")
    teto = 250.0  # acima disso a barra é cortada e marcada, para não achatar as demais
    cortadas = topo[topo["var"] > teto]
    nota_corte = ("Barra cortada: " + ", ".join(f"{c.nome_pt(i)} (+{num(v)}%)" for i, v in zip(cortadas["iso3"], cortadas["var"]))
                  + ".") if len(cortadas) else ""

    fig, (a1, a2) = nova_figura(
        fmt, f"Quem mais gasta: {_sujeito(lider['iso3'], 'responde', 'respondem')} por "
             f"{num(lider['bi'] / total * 100)}% do total mundial",
        {"wide": f"Os {n} maiores orçamentos militares em {ult} (mais o Brasil) e a variação real em dez anos. "
                 f"{c.nome_pt(maior_var['iso3'])} teve o maior salto: {num(maior_var['var'])}%; o Brasil variou {var_bra}%.",
         "insta": f"Os {n} maiores orçamentos militares de {ult}, mais o Brasil, e a variação real desde {base}."},
        {"wide": f"SIPRI Military Expenditure Database (abr. 2026), US$ constantes de 2024, {base} e {ult}. Valores de "
                 f"China, Rússia e outros são estimativas do SIPRI. Ranking apenas entre países com dado no último ano. {nota_corte}",
         "insta": f"SIPRI Military Expenditure Database (2026), US$ constantes de 2024, {base} e {ult}. {nota_corte}"},
        ncol=2, empilhar_no_insta=False, gridspec_kw={"width_ratios": [1.5, 1]}, sharey=True)
    p = plt.rcParams["font.size"]
    pos = np.arange(len(topo))

    a1.barh(pos, topo["bi"], color=[VIOLETA if i == "BRA" else AZUL for i in topo["iso3"]], height=0.68)
    for y, v in zip(pos, topo["bi"]):
        a1.text(v, y, " " + num(v), va="center", ha="left", fontsize=p - 1.5)
    a1.set_yticks(pos, topo["nome"])
    a1.tick_params(axis="y", labelcolor=TINTA, labelsize=p - (1.5 if fmt == "insta" else 0))
    a1.set_xlim(0, topo["bi"].max())
    a1.set_ylim(-0.7, len(topo) - 0.3)
    a1.xaxis.set_major_locator(MaxNLocator(nbins=4))
    a1.xaxis.set_major_formatter(lambda v, _: num(v))
    a1.grid(axis="y", visible=False)
    _titulo_painel(a1, f"Gasto em {ult}, US$ bilhões" if fmt == "insta" else f"Gasto em {ult}, US$ bilhões (preços de 2024)")

    a2.barh(pos, topo["var"].clip(upper=teto), color=[AZUL if v >= 0 else LARANJA for v in topo["var"]], height=0.68)
    for y, v in zip(pos, topo["var"]):
        if np.isnan(v):
            a2.text(0, y, " sem dado", va="center", ha="left", color=TINTA3, fontsize=p - 1.5)
        elif v > teto:                          # marca de quebra + valor dentro da barra
            for x in (0.88, 0.92):
                a2.plot([teto * x, teto * (x + 0.025)], [y - 0.36, y + 0.36], color=SUPERFICIE, lw=2.2,
                        solid_capstyle="butt")
            a2.text(teto * 0.85, y, f"+{num(v)}%", va="center", ha="right", color="white", fontweight="bold",
                    fontsize=p - 1.5)
        else:                                   # negativos: rótulo à direita do zero, onde há espaço
            a2.text(max(v, 0), y, f" +{num(v)}%" if v >= 0 else f" −{num(abs(v))}%", va="center", ha="left",
                    fontsize=p - 1.5)
    a2.axvline(0, color=TINTA2, lw=1)
    a2.set_xlim(min(0.0, float(topo["var"].min())) - teto * 0.04, teto)
    a2.set_xticks([0, 100, 200])
    a2.xaxis.set_major_formatter(lambda v, _: num(v) + "%")
    a2.grid(axis="y", visible=False)
    _titulo_painel(a2, f"Variação real, {base}–{str(ult)[2:]}")
    ajustar(fig)
    caber(a1)
    caber(a2)
    salvar(fig, "fig03_ranking_gasto", fmt)


# --- Figura 4 -----------------------------------------------------------------
def _janelas_tiv(papel: str, p1=(2016, 2020), p2=(2021, 2025)) -> tuple[pd.DataFrame, float, float]:
    t = _ler("armas_tiv.csv").query("papel == @papel")
    soma = lambda a, b: t[t["ano"].between(a, b)].groupby(["pais", "iso3", "total_mundial"], dropna=False)["tiv_milhoes"].sum()
    tab = pd.concat([soma(*p1).rename("p1"), soma(*p2).rename("p2")], axis=1).fillna(0).reset_index()
    tot = tab[tab["total_mundial"]].iloc[0]
    return tab[~tab["total_mundial"]].sort_values("p2", ascending=False), float(tot["p1"]), float(tot["p2"])


def _nome_tiv(iso3, pais: str) -> str:
    return c.nome_pt(iso3, pais) if isinstance(iso3, str) else pais


def fig04_exportadores_importadores(fmt: str, n: int = 10):
    exp, te1, te2 = _janelas_tiv("exportador")
    imp, ti1, ti2 = _janelas_tiv("importador")
    lider_e, lider_i = exp.iloc[0], imp.iloc[0]
    variou = f"{'cresceu' if te2 >= te1 else 'caiu'} {num(abs(te2 / te1 - 1) * 100, 1)}%"
    fig, eixos = nova_figura(
        fmt, f"{_sujeito(lider_e['iso3'], 'vende', 'vendem')} {num(lider_e['p2'] / te2 * 100)}% das armas do mundo; "
             f"{c.nome_pt(lider_i['iso3'])} é quem mais compra",
        {"wide": f"Dez maiores exportadores e importadores de grandes armas, 2016–20 e 2021–25. O volume mundial "
                 f"{variou} entre os dois períodos.",
         "insta": f"Dez maiores exportadores e importadores de grandes armas. O volume mundial {variou} entre os "
                  "dois períodos."},
        {"wide": f"SIPRI Arms Transfers Database (consulta em out. 2026), somas de 5 anos em milhões de TIV. {NOTA_TIV} "
                 "Percentual ao lado do nome = participação no total mundial em 2021–25.",
         "insta": f"SIPRI Arms Transfers Database (2026), somas de 5 anos. {NOTA_TIV_CURTA} "
                  "Percentual = participação mundial em 2021–25."},
        ncol=2)
    p = plt.rcParams["font.size"]
    legenda_topo(fig, [Patch(color=AZUL_CLARO, label="2016–20"), Patch(color=AZUL, label="2021–25")])
    for ax, tab, tot, titulo in [(eixos[0], exp, te2, "Exportadores"), (eixos[1], imp, ti2, "Importadores")]:
        d = tab.head(n).iloc[::-1]
        pos = np.arange(len(d))
        ax.barh(pos + 0.2, d["p1"], height=0.36, color=AZUL_CLARO)
        ax.barh(pos - 0.2, d["p2"], height=0.36, color=AZUL)
        ax.set_yticks(pos, [f"{_nome_tiv(i, pz)}  {num(v / tot * 100)}%" for i, pz, v in zip(d["iso3"], d["pais"], d["p2"])])
        ax.tick_params(axis="y", labelcolor=TINTA, labelsize=p - (1.5 if fmt == "insta" else 0))
        ax.set_xlim(0, d[["p1", "p2"]].max().max() * 1.03)
        ax.set_ylim(-0.7, len(d) - 0.3)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=5 if fmt == "insta" else 6))
        ax.xaxis.set_major_formatter(lambda v, _: num(v))
        ax.grid(axis="y", visible=False)
        _titulo_painel(ax, f"{titulo}, milhões de TIV")
    salvar(fig, "fig04_exportadores_importadores", fmt)


# --- Figura 5 -----------------------------------------------------------------
def fig05_conflitos_tipo(fmt: str):
    t = _ler("conflitos_por_tipo.csv").pivot(index="ano", columns="tipo", values="n_conflitos").fillna(0)
    ordem = [("Intraestatal", AZUL), ("Intraestatal internacionalizado", LARANJA),
             ("Interestatal", AGUA), ("Extrassistêmico", AMARELO)]
    total = t.sum(axis=1)
    ult = int(t.index.max())
    recorde = int(total.idxmax())
    inter, entre = t["Intraestatal internacionalizado"], t["Interestatal"]
    recorde_entre = entre.idxmax() == ult and int((entre == entre.max()).sum()) == 1
    fig, (ax,) = nova_figura(
        fmt, f"{int(total[ult])} conflitos armados ativos em {ult}"
             + (", recorde da série iniciada em 1946" if recorde == ult else f" (recorde: {int(total[recorde])} em {recorde})"),
        {"wide": f"Conflitos de base estatal por tipo. Os interestatais são poucos ({int(entre[ult])} em {ult}); "
                 f"cresce a guerra civil com tropas estrangeiras: de {int(inter[2010])} em 2010 para {int(inter[ult])} em {ult}.",
         "insta": f"Conflitos de base estatal, por tipo. {int(entre[ult])} são guerras entre Estados"
                  + (", também um recorde." if recorde_entre else ".")},
        {"wide": f"UCDP/PRIO Armed Conflict Dataset v26.1, 1946–{ult}. Conflito ativo = ao menos 25 mortes em batalha "
                 "no ano, com um governo entre as partes. Não inclui violência entre grupos não estatais nem contra civis. "
                 "Faixas sombreadas: desde 2014 (anexação da Crimeia) e desde 2022 (invasão da Ucrânia).",
         "insta": f"UCDP/PRIO Armed Conflict Dataset v26.1, 1946–{ult}. Conflitos com um governo entre as partes e "
                  "ao menos 25 mortes em batalha no ano. Faixas sombreadas: desde 2014 e desde 2022."})
    legenda_topo(fig, [Patch(color=cor, label=k) for k, cor in ordem], ncol=2 if fmt == "insta" else None)
    ax.stackplot(t.index, [t[k] for k, _ in ordem], colors=[cor for _, cor in ordem],
                 edgecolor=SUPERFICIE, linewidth=1.2)
    ax.set_xlim(1946, ult + 0.3)
    ax.set_ylim(0, total.max() * 1.05)
    _faixas_periodo(ax, ult)
    _halo(ax.annotate(f"{int(total[ult])}", (ult, total[ult]), xytext=(-2, 7), textcoords="offset points",
                      ha="right", va="bottom", fontweight="bold", fontsize=plt.rcParams["font.size"] + 2))
    ajustar(fig)
    caber(ax)
    salvar(fig, "fig05_conflitos_tipo", fmt)


# --- Figura 6 -----------------------------------------------------------------
CORES_REGIAO = [("Europa", AZUL), ("Oriente Médio", LARANJA), ("Ásia", AGUA), ("África", AMARELO),
                ("Américas", MAGENTA), ("Mais de uma região", NEUTRO)]


def fig06_mortes_regiao(fmt: str):
    r = _ler("mortes_por_regiao.csv")
    t = r.pivot(index="ano", columns="regiao", values="mortes").fillna(0)
    total = t.sum(axis=1)
    faixa = r.groupby("ano")[["mortes_min", "mortes_max"]].sum()
    ult = int(t.index.max())
    pico = int(total.idxmax())
    conf = _ler("mortes_por_conflito.csv")
    maior = conf[conf["ano"] == ult].iloc[0]
    guerra = "a guerra Rússia–Ucrânia" if "Ukraine" in maior["local"] else maior["local"]
    fatia = num(maior["mortes"] / total[ult] * 100)
    fig, (ax,) = nova_figura(
        fmt, f"Mortes em batalha: {num(total[ult] / 1000)} mil em {ult}, {num(total[ult] / total[ult - 5], 1)} vezes "
             f"o nível de {ult - 5}",
        {"wide": f"Melhor estimativa de mortes em combate por região. Pico em {pico} ({num(total[pico] / 1000)} mil). "
                 f"Em {ult}, {guerra} respondeu por {fatia}% do total.",
         "insta": f"Mortes em combate por região. Em {ult}, {guerra} respondeu por {fatia}% do total."},
        {"wide": f"UCDP Battle-Related Deaths Dataset v26.1, 1989–{ult}, melhor estimativa. Só conflitos de base "
                 "estatal: ficam fora massacres de civis e violência entre grupos não estatais. Traço fino = intervalo "
                 "entre a estimativa baixa e a alta.",
         "insta": f"UCDP Battle-Related Deaths Dataset v26.1, 1989–{ult}. Só conflitos de base estatal. Traço fino: "
                  "intervalo entre as estimativas baixa e alta."})
    presentes = [(regiao, cor) for regiao, cor in CORES_REGIAO if regiao in t.columns]
    legenda_topo(fig, [Patch(color=cor, label=regiao) for regiao, cor in presentes],
                 ncol=3 if fmt == "insta" else None)
    base = np.zeros(len(t))
    for regiao, cor in presentes:
        ax.bar(t.index, t[regiao], bottom=base, color=cor, width=0.78, edgecolor=SUPERFICIE, linewidth=0.6)
        base += t[regiao].values
    ax.vlines(faixa.index, faixa["mortes_min"], faixa["mortes_max"], color=TINTA2, lw=0.9)
    ax.set_xlim(1988.3, ult + 0.7)
    ax.set_ylim(0, faixa["mortes_max"].max() * 1.04)
    ax.yaxis.set_major_formatter(lambda v, _: num(v / 1000) + " mil" if v else "0")
    ax.grid(axis="x", visible=False)
    _halo(ax.annotate(f"{pico}: {num(total[pico] / 1000)} mil", (pico - 0.39, total[pico]),
                      xytext=(-12, 16), textcoords="offset points", ha="right", va="bottom", fontweight="bold",
                      arrowprops=dict(arrowstyle="-", color=TINTA2, lw=0.9, shrinkA=1, shrinkB=1)))
    ajustar(fig)
    caber(ax)
    salvar(fig, "fig06_mortes_regiao", fmt)


# --- Figura 7 -----------------------------------------------------------------
def fig07_concentracao(fmt: str, janela: int = 5):
    t = _ler("armas_tiv.csv").query("papel == 'exportador'")
    tab = t[~t["total_mundial"]].pivot_table(index="ano", columns="pais", values="tiv_milhoes", aggfunc="sum").fillna(0)
    mundo = t[t["total_mundial"]].set_index("ano")["tiv_milhoes"]
    mov = tab.rolling(janela).sum().dropna()
    part = mov.div(mundo.rolling(janela).sum().dropna(), axis=0) * 100
    top5 = part.apply(lambda l: l.nlargest(5).sum(), axis=1)
    ult = int(part.index.max())
    series = [("United States", "Estados Unidos", "EUA", AZUL), ("Russia", "Rússia", "Rússia", LARANJA),
              ("France", "França", "França", AGUA)]
    eua, rus = part["United States"], part["Russia"]
    fig, (ax,) = nova_figura(
        fmt, f"EUA ampliam o domínio do mercado de armas: de {num(eua[2015])}% para {num(eua[ult])}% das exportações",
        {"wide": f"Participação nas exportações mundiais de grandes armas, janelas móveis de {janela} anos. "
                 f"A Rússia foi de {num(rus[2015])}% para {num(rus[ult])}%. Os cinco maiores somavam {num(top5[2015])}% "
                 f"em 2011–15 e {num(top5[ult])}% em {ult - janela + 1}–{str(ult)[2:]}.",
         "insta": f"Participação nas exportações mundiais de grandes armas, em janelas de {janela} anos. A Rússia "
                  f"foi de {num(rus[2015])}% para {num(rus[ult])}%."},
        {"wide": f"SIPRI Arms Transfers Database (consulta em out. 2026), {int(tab.index.min())}–{ult}. Cada ponto é a "
                 f"soma dos {janela} anos terminados no ano indicado. {NOTA_TIV} A composição dos 'cinco maiores' muda "
                 "a cada janela.",
         "insta": f"SIPRI Arms Transfers Database (2026), {int(tab.index.min())}–{ult}, somas móveis de {janela} anos. "
                  f"{NOTA_TIV_CURTA}"})
    legenda_topo(fig, [Line2D([], [], color=TINTA, lw=2.6, label="Cinco maiores exportadores")]
                 + [Line2D([], [], color=cor, lw=2.4, label=nome) for _, nome, _, cor in series])
    ax.plot(top5.index, top5, color=TINTA, lw=2.6)
    for col, _, _, cor in series:
        ax.plot(part.index, part[col], color=cor, lw=2.4)
    ax.axvline(c.ANO_INVASAO, color=TINTA3, lw=1, ls=":")
    ax.set_xlim(part.index.min(), ult + 0.6)
    ax.set_ylim(0, 100)
    ax.set_xticks(range(2000, ult + 1, 5))
    ax.yaxis.set_major_formatter(lambda v, _: num(v) + "%")
    ax.set_xlabel(f"último ano de cada janela de {janela} anos")
    ajustar(fig)
    rotulos_fim(ax, [(float(top5[ult]), f"5 maiores {num(top5[ult])}%", TINTA)]
                + [(float(part[col][ult]), f"{curto} {num(part[col][ult])}%", cor) for col, _, curto, cor in series], ult)
    salvar(fig, "fig07_concentracao_mercado", fmt)


# --- Figura 8 -----------------------------------------------------------------
def fig08_conflito_armas(fmt: str, n: int | None = None, p=(2021, 2025)):
    n = n or (15 if fmt == "wide" else 10)
    conf = _ler("conflitos_por_pais.csv")
    em_conflito = set(conf[conf["ano"].between(*p)]["iso3"])
    periodo = f"{p[0]}–{str(p[1])[2:]}"
    fig, eixos = nova_figura(
        fmt, "Quem compra e quem vende armas está em guerra?",
        {"wide": f"{n} maiores importadores e exportadores de grandes armas em {p[0]}–{p[1]}, conforme o governo "
                 "tenha sido parte primária de algum conflito armado ativo no mesmo período.",
         "insta": f"Os {n} maiores importadores e exportadores de grandes armas em {periodo} e a participação "
                  "do governo em conflito armado."},
        {"wide": f"SIPRI Arms Transfers Database (out. 2026), soma {p[0]}–{p[1]} em milhões de TIV; UCDP/PRIO Armed "
                 f"Conflict Dataset v26.1. {NOTA_TIV} Parte primária = governo listado como lado A ou B; apoio com "
                 "tropas a terceiros não conta. Associação, não causalidade.",
         "insta": f"SIPRI Arms Transfers Database (2026), soma {periodo}; UCDP/PRIO v26.1. {NOTA_TIV_CURTA} "
                  "Associação, não causalidade."},
        ncol=2)
    tam = plt.rcParams["font.size"]
    legenda_topo(fig, [Patch(color=LARANJA, label=f"Governo foi parte de conflito ativo em {periodo}"),
                       Patch(color=NEUTRO, label="Não foi parte primária de conflito ativo")])
    resumo = {}
    for ax, papel, titulo in [(eixos[0], "importador", "Importadores"), (eixos[1], "exportador", "Exportadores")]:
        tab, _, tot = _janelas_tiv(papel, p2=p)
        d = tab.head(n).iloc[::-1]
        status = d["iso3"].isin(em_conflito)
        resumo[papel] = (int(status.sum()), float(d.loc[status, "p2"].sum() / tot * 100))
        pos = np.arange(len(d))
        ax.barh(pos, d["p2"], height=0.68, color=[LARANJA if s else NEUTRO for s in status])
        ax.set_yticks(pos, [_nome_tiv(i, pz) for i, pz in zip(d["iso3"], d["pais"])])
        ax.tick_params(axis="y", labelcolor=TINTA, labelsize=tam - (1.5 if fmt == "insta" else 0))
        ax.set_xlim(0, d["p2"].max() * 1.03)
        ax.set_ylim(-0.7, len(d) - 0.3)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=5 if fmt == "insta" else 6))
        ax.xaxis.set_major_formatter(lambda v, _: num(v))
        ax.grid(axis="y", visible=False)
        _titulo_painel(ax, f"{titulo} (milhões de TIV): {resumo[papel][0]} de {n} em conflito")
    salvar(fig, "fig08_conflito_armas", fmt)
    return resumo


# --- Figura 9 -----------------------------------------------------------------
def dados_fig09(p=(2021, 2025)) -> tuple[pd.DataFrame, list[str]]:
    conf = _ler("conflitos_por_pais.csv")
    mortes = conf[conf["ano"].between(*p)].groupby("iso3")["mortes"].sum()
    mortes = mortes[mortes > 0]
    wb = _ler("gasto_banco_mundial.csv")
    g = wb[wb["ano"].between(*p) & ~wb["agregado"]].groupby("iso3")["gasto_pct_pib"].agg(["mean", "count"])
    d = pd.concat([mortes, g], axis=1, join="inner").dropna(subset=["mean"]).rename(columns={"mean": "pct_pib"})
    sem_gasto = sorted(set(mortes.index) - set(d.index))
    return d.reset_index(), sem_gasto


def fig09_gasto_mortes(fmt: str, p=(2021, 2025)):
    d, sem_gasto = dados_fig09(p)
    wb = _ler("gasto_banco_mundial.csv")
    mundo = wb[(wb["iso3"] == "WLD") & wb["ano"].between(*p)]["gasto_pct_pib"].mean()
    rho = d[["mortes", "pct_pib"]].corr(method="spearman").iloc[0, 1]
    abaixo = int((d["pct_pib"] < mundo).sum())
    sem = ", ".join(c.nome_pt(i) for i in sem_gasto) or "nenhum"
    periodo = f"{p[0]}–{str(p[1])[2:]}"
    fig, (ax,) = nova_figura(
        fmt, "Mais mortes em batalha não significam, em geral, orçamento militar maior",
        {"wide": f"Cada ponto é um país cujo governo foi parte de conflito com mortes em batalha em {p[0]}–{p[1]} "
                 f"({len(d)} países). {abaixo} gastaram menos que a média mundial; correlação de postos (Spearman) = {num(rho, 2)}.",
         "insta": f"{len(d)} países com governo em conflito em {periodo}: {abaixo} gastaram menos que a média mundial. "
                  f"Correlação de postos: {num(rho, 2)}."},
        {"wide": f"UCDP Battle-Related Deaths v26.1 (soma {p[0]}–{p[1]}, melhor estimativa; em guerras interestatais as "
                 "mortes contam para os dois governos); Banco Mundial/WDI, MS.MIL.XPND.GD.ZS (média dos anos com dado). "
                 f"Sem dado de gasto e fora do gráfico: {sem}. Associação, não causalidade.",
         "insta": f"UCDP Battle-Related Deaths v26.1; Banco Mundial/WDI (dados do SIPRI), médias e somas de {periodo}. "
                  f"Sem dado de gasto: {sem}. Associação, não causalidade."})
    tam = plt.rcParams["font.size"]
    ax.scatter(d["mortes"], d["pct_pib"], s=62, color=AZUL, edgecolor=SUPERFICIE, linewidth=1.4, zorder=3)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.axhline(mundo, color=TINTA2, lw=1.1, ls=(0, (4, 3)))
    ax.set_xlim(d["mortes"].min() * 0.6, d["mortes"].max() * (6 if fmt == "insta" else 3.5))
    ax.set_ylim(d["pct_pib"].min() * 0.6, d["pct_pib"].max() * 1.6)
    ax.set_yticks([t for t in (0.1, 0.2, 0.5, 1, 2, 5, 10, 20) if d["pct_pib"].min() * 0.6 <= t])
    ax.minorticks_off()
    ax.set_xlabel("mortes em batalha (escala logarítmica)")
    ax.set_ylabel("gasto militar, % do PIB (escala logarítmica)")
    ax.xaxis.set_major_formatter(lambda v, _: num(v))
    ax.yaxis.set_major_formatter(lambda v, _: num(v, 1 if v < 1 else 0) + "%")
    ajustar(fig)

    # Rótulo da linha de referência: primeira posição, ao longo da linha, que não cobre pontos.
    fig.draw_without_rendering()
    r = fig.canvas.get_renderer()
    pontos = auditoria._pontos(ax, fig.dpi)
    area, y_ref, u = ax.get_window_extent(r), ax.transData.transform((1, mundo))[1], fig.dpi / 150
    ocupadas = [Bbox.from_extents(area.x0, y_ref - 5 * u, area.x1, y_ref + 5 * u)]   # nomes não cruzam a linha
    for x, ha, dy, va in [(0.99, "right", 4, "bottom"), (0.01, "left", 4, "bottom"),
                          (0.99, "right", -4, "top"), (0.01, "left", -4, "top")]:
        ref = ax.annotate(f"média mundial: {num(mundo, 1)}% do PIB", (x, mundo), xycoords=ax.get_yaxis_transform(),
                          xytext=(0, dy), textcoords="offset points", ha=ha, va=va, color=TINTA2, fontsize=tam - 2)
        if not any(caixa_texto(ref, r).overlaps(o) for o in pontos):
            ref._livre = True
            ocupadas.append(caixa_texto(ref, r))
            _chip(ref)
            break
        ref.remove()

    rotular = pd.concat([d.nlargest(7, "mortes"), d.nlargest(5, "pct_pib"),
                         d.nsmallest(1, "pct_pib")]).drop_duplicates("iso3")
    rotular_pontos(ax, [(l["mortes"], l["pct_pib"], c.nome_pt(l["iso3"])) for _, l in rotular.iterrows()], ocupadas)
    salvar(fig, "fig09_gasto_mortes", fmt)


# --- Figura 10 ----------------------------------------------------------------
EVENTOS_MVI = ["Homicídio doloso", "Feminicídio", "Roubo seguido de morte (latrocínio)",
               "Lesão corporal seguida de morte",
               "Morte por intervenção de Agente do Estado"]
EVENTO_POLICIA = "Morte por intervenção de Agente do Estado"


def dados_fig10() -> pd.DataFrame | None:
    arq = c.PROCESSED / "brasil_sinesp_eventos.csv"
    if not arq.exists():
        return None
    b = pd.read_csv(arq)
    t = b[b["evento"].isin(EVENTOS_MVI)].pivot_table(index="ano", columns="evento", values="vitimas", aggfunc="sum")
    faltando = [e for e in EVENTOS_MVI if e not in t.columns]
    if faltando:
        raise ValueError(f"Categorias ausentes na base Sinesp: {faltando}")
    out = pd.DataFrame({"policia": t[EVENTO_POLICIA], "demais": t.drop(columns=EVENTO_POLICIA).sum(axis=1)})
    out["total"] = out.sum(axis=1)
    out["pct_policia"] = out["policia"] / out["total"] * 100
    return out


def fig10_brasil(fmt: str):
    d = dados_fig10()
    if d is None:
        print("[pulada] fig10: sem data/processed/brasil_sinesp_eventos.csv")
        return
    ini, ult = int(d.index.min()), int(d.index.max())
    pico = int(d["total"].idxmax())
    ev = _ler("brasil_sinesp_eventos.csv")
    cob = ev[ev["evento"].isin(EVENTOS_MVI)].groupby("ano")["n_ufs"].min()
    incompletos = [int(a) for a in cob.index[cob < 27] if a in d.index]
    nota = (f" * {', '.join(map(str, incompletos))}: alguma UF sem registro em parte das categorias."
            if incompletos else "")
    fig, (a1, a2) = nova_figura(
        fmt, f"Brasil: mortes violentas caem {num((1 - d['total'][ult] / d['total'][pico]) * 100)}% desde {pico}, "
             f"mas cresce a parcela causada por agentes do Estado",
        {"wide": f"Mortes por intervenção de agentes do Estado foram {num(d['pct_policia'][ini], 1)}% das mortes "
                 f"violentas em {ini} e {num(d['pct_policia'][ult], 1)}% em {ult} ({num(d['policia'][ult])} pessoas).",
         "insta": f"Mortes por intervenção de agentes do Estado: {num(d['policia'][ult])} pessoas em {ult}, "
                  f"{num(d['pct_policia'][ult], 1)}% do total."},
        {"wide": f"MJSP, Sinesp VDE (base dos gestores estaduais), {ini}–{ult}, vítimas. Mortes violentas = homicídio "
                 "doloso + feminicídio + latrocínio + lesão corporal seguida de morte + morte por intervenção de agente "
                 "do Estado; aproxima, mas não é idêntica à série de MVI do Fórum Brasileiro de Segurança Pública. A "
                 f"cobertura e o registro variam entre estados e anos.{nota}",
         "insta": f"MJSP, Sinesp VDE, {ini}–{ult}. Mortes violentas: homicídio doloso, feminicídio, latrocínio, lesão "
                  f"seguida de morte e morte por intervenção de agente do Estado.{nota}"},
        nlin=2, gridspec_kw={"height_ratios": [1.6, 1]})
    p = plt.rcParams["font.size"]
    legenda_topo(fig, [Patch(color=AZUL, label="Demais mortes violentas"),
                       Patch(color=LARANJA, label="Mortes por intervenção de agente do Estado")])
    a1.bar(d.index, d["demais"], color=AZUL, width=0.7, edgecolor=SUPERFICIE, linewidth=0.8)
    a1.bar(d.index, d["policia"], bottom=d["demais"], color=LARANJA, width=0.7, edgecolor=SUPERFICIE, linewidth=0.8)
    for ano in d.index:
        a1.annotate(num(d["total"][ano] / 1000, 1) + ("*" if ano in incompletos else ""), (ano, d["total"][ano]),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=p - 2)
    a1.set_ylim(0, d["total"].max())
    a1.yaxis.set_major_locator(MaxNLocator(nbins=4))
    a1.yaxis.set_major_formatter(lambda v, _: num(v / 1000))
    a1.grid(axis="x", visible=False)
    a1.set_xticks(d.index, [str(a) if fmt == "wide" else f"’{str(a)[2:]}" for a in d.index])
    _titulo_painel(a1, "Vítimas por ano, em milhares")

    a2.plot(d.index, d["pct_policia"], color=LARANJA, lw=2.4, marker="o", ms=7, mec=SUPERFICIE, mew=1.5)
    for ano in (ini, ult):
        _halo(a2.annotate(num(d["pct_policia"][ano], 1) + "%", (ano, d["pct_policia"][ano]), xytext=(0, 9),
                          textcoords="offset points", ha="center", va="bottom", fontweight="bold"))
    a2.set_ylim(0, d["pct_policia"].max() * 1.05)
    a2.yaxis.set_major_locator(MaxNLocator(nbins=4))
    a2.yaxis.set_major_formatter(lambda v, _: num(v) + "%")
    a2.set_xticks(d.index, [str(a) if fmt == "wide" else f"’{str(a)[2:]}" for a in d.index])
    a2.set_xlim(a1.get_xlim())
    _titulo_painel(a2, "Parcela causada por agentes do Estado" if fmt == "insta"
                   else "Parcela das mortes violentas causada por agentes do Estado")
    ajustar(fig)
    caber(a1)
    caber(a2)
    salvar(fig, "fig10_brasil_violencia", fmt)


FIGURAS = {1: fig01_gasto_mundial, 2: fig02_otan_pib, 3: fig03_ranking, 4: fig04_exportadores_importadores,
           5: fig05_conflitos_tipo, 6: fig06_mortes_regiao, 7: fig07_concentracao, 8: fig08_conflito_armas,
           9: fig09_gasto_mortes, 10: fig10_brasil}
PRECISA = {4: "armas_tiv.csv", 7: "armas_tiv.csv", 8: "armas_tiv.csv", 10: "brasil_sinesp_eventos.csv"}


def main(quais: list[int] | None = None) -> list[int]:
    geradas = []
    for n in quais or sorted(FIGURAS):
        if n in PRECISA and not (c.PROCESSED / PRECISA[n]).exists():
            print(f"[pulada] figura {n}: falta data/processed/{PRECISA[n]}")
            continue
        for fmt in FORMATOS:
            FIGURAS[n](fmt)
        geradas.append(n)
        print(f"[ok] figura {n}")
    return geradas


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or None)
