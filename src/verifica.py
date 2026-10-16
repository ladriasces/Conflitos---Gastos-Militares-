"""Imprime, a partir de data/processed, os números citados no roteiro e no rascunho.

Uso: python -m src.verifica

Serve de conferência: toda afirmação numérica dos textos em outputs/texto deve
aparecer aqui. Também cruza Banco Mundial x planilha do SIPRI.
"""
from __future__ import annotations

import pandas as pd

from . import config as c
from . import graficos as g


def _ler(nome: str) -> pd.DataFrame:
    return pd.read_csv(c.PROCESSED / nome)


def main() -> None:
    pd.set_option("display.width", 200)
    wb, reg, sp = _ler("gasto_banco_mundial.csv"), _ler("gasto_sipri_regioes.csv"), _ler("gasto_sipri_paises.csv")

    print("== 1. Gasto mundial ==")
    m = reg[reg.regiao == "World"].set_index("ano").usd_bi_const2024
    ult = int(m.index.max())
    print(f"SIPRI, US$ bi constantes de 2024: 2014={m[2014]:.0f}  2021={m[2021]:.0f}  {ult}={m[ult]:.0f}")
    print(f"variação {ult}/2014 = {(m[ult] / m[2014] - 1) * 100:.1f}%   {ult}/2021 = {(m[ult] / m[2021] - 1) * 100:.1f}%"
          f"   recorde da série em {int(m.idxmax())}")
    w = wb[wb.iso3 == "WLD"].set_index("ano")
    print(f"Banco Mundial, mundo {ult}: US$ {w.gasto_usd_corrente[ult] / 1e9:.0f} bi correntes; "
          f"% PIB 1960={w.gasto_pct_pib[1960]:.2f}  2014={w.gasto_pct_pib[2014]:.2f}  {ult}={w.gasto_pct_pib[ult]:.2f}")
    eur = reg[reg.regiao == "Europe"].set_index("ano").usd_bi_const2024
    print(f"Europa (SIPRI): 2014={eur[2014]:.0f}  2021={eur[2021]:.0f}  {ult}={eur[ult]:.0f}  "
          f"var. desde 2021 = {(eur[ult] / eur[2021] - 1) * 100:.0f}%")

    print("\n== Cruzamento Banco Mundial x SIPRI (% do PIB, último ano) ==")
    x = sp[sp.ano == ult].merge(wb[wb.ano == ult], on="iso3")[["iso3", "pct_pib", "gasto_pct_pib"]].dropna()
    x["dif"] = (x.pct_pib - x.gasto_pct_pib).abs()
    print(f"{len(x)} países comparados; maior diferença absoluta = {x.dif.max():.4f} p.p.")

    print("\n== 2. OTAN Europa e Brasil (% do PIB, Banco Mundial) ==")
    o = wb[wb.iso3.isin(c.OTAN_EUROPA)].pivot(index="ano", columns="iso3", values="gasto_pct_pib")
    for ano in (2014, 2021, ult):
        print(f"{ano}: mediana={o.loc[ano].median():.2f}  >=2%: {(o.loc[ano] >= 2).sum()} de {o.loc[ano].notna().sum()}"
              f"  >=3,5%: {(o.loc[ano] >= 3.5).sum()}")
    print("acima de 3,5% em", ult, ":", ", ".join(f"{c.nome_pt(i)} {v:.2f}" for i, v in o.loc[ult][o.loc[ult] >= 3.5].items()))
    print("abaixo de 2% em", ult, ":", ", ".join(f"{c.nome_pt(i)} {v:.2f}" for i, v in o.loc[ult][o.loc[ult] < 2].items()))
    b = wb[wb.iso3 == "BRA"].set_index("ano").gasto_pct_pib
    print(f"Brasil: 2014={b[2014]:.2f}  2021={b[2021]:.2f}  {ult}={b[ult]:.2f}")
    print("destaques", ult, ":", {i: round(float(o.loc[ult, i]), 2) for i in c.OTAN_DESTAQUES})

    print("\n== 3. Ranking (SIPRI, US$ constantes de 2024) ==")
    t = sp.dropna(subset=["usd_mi_const2024"]).pivot_table(index=["pais", "iso3"], columns="ano", values="usd_mi_const2024")
    t = t.dropna(subset=[ult]).sort_values(ult, ascending=False).reset_index()
    t["pos"], t["var10"] = t.index + 1, (t[ult] / t[ult - 10] - 1) * 100
    print(t[(t.pos <= 15) | (t.iso3 == "BRA")][["pos", "pais", ult, "var10"]].round(1).to_string(index=False))
    print(f"EUA / mundo = {t[ult].iloc[0] / 1000 / m[ult] * 100:.1f}%   5 maiores / mundo = {t[ult].head(5).sum() / 1000 / m[ult] * 100:.1f}%")

    if (c.PROCESSED / "armas_tiv.csv").exists():
        print("\n== 4/7/8. Transferências de armas (TIV, não monetário) ==")
        for papel in ("exportador", "importador"):
            tab, t1, t2 = g._janelas_tiv(papel)
            tab = tab.assign(part=tab.p2 / t2 * 100, var=(tab.p2 / tab.p1 - 1) * 100)
            print(f"{papel}: total 2016-20={t1:.0f}  2021-25={t2:.0f}  var={(t2 / t1 - 1) * 100:.1f}%")
            print(tab.head(10)[["pais", "p1", "p2", "part", "var"]].round(1).to_string(index=False))
            if papel == "importador":
                print(tab[tab.iso3 == "BRA"][["pais", "p1", "p2", "part"]].round(2).to_string(index=False),
                      " posição do Brasil:", int((tab.p2 > tab[tab.iso3 == "BRA"].p2.iloc[0]).sum()) + 1)
        conf = _ler("conflitos_por_pais.csv")
        ativos = conf[conf.ano.between(2021, 2025)].groupby("iso3").agg(anos=("ano", "nunique"), mortes=("mortes", "sum"))
        for papel in ("importador", "exportador"):
            tab, _, t2 = g._janelas_tiv(papel)
            top = tab.head(15).merge(ativos, left_on="iso3", right_index=True, how="left")
            print(f"15 maiores {papel}es e conflito 2021-25 (anos como parte primária):")
            print(top[["pais", "p2", "anos", "mortes"]].fillna({"anos": 0}).to_string(index=False))

    print("\n== 5. Conflitos por tipo (UCDP) ==")
    ct = _ler("conflitos_por_tipo.csv").pivot(index="ano", columns="tipo", values="n_conflitos").fillna(0).astype(int)
    ct["total"] = ct.sum(axis=1)
    print(ct.loc[[2010, 2014, 2021, 2024, 2025]].to_string())
    print("recorde:", int(ct.total.idxmax()), int(ct.total.max()))

    print("\n== 6. Mortes em batalha (UCDP) ==")
    mr = _ler("mortes_por_regiao.csv")
    print(mr.pivot(index="ano", columns="regiao", values="mortes").fillna(0).astype(int)
          .assign(total=lambda d: d.sum(axis=1)).loc[2014:].to_string())
    mc = _ler("mortes_por_conflito.csv")
    for ano in (2022, 2025):
        print(f"maiores conflitos em {ano}:")
        print(mc[mc.ano == ano].groupby("local").mortes.sum().nlargest(8).to_string())
    f = mr[mr.ano == 2025][["mortes_min", "mortes", "mortes_max"]].sum()
    print(f"2025: baixa={f.mortes_min:.0f}  melhor={f.mortes:.0f}  alta={f.mortes_max:.0f}")

    print("\n== 9. Gasto x mortes ==")
    d, sem = g.dados_fig09()
    mundo = wb[(wb.iso3 == "WLD") & wb.ano.between(2021, 2025)].gasto_pct_pib.mean()
    print(f"{len(d)} países; Spearman={d[['mortes', 'pct_pib']].corr(method='spearman').iloc[0, 1]:.2f}; "
          f"abaixo da média mundial ({mundo:.2f}%): {(d.pct_pib < mundo).sum()}; sem dado: {sem}")
    print(d.nlargest(8, "mortes").round(2).to_string(index=False))

    b10 = g.dados_fig10()
    if b10 is not None:
        print("\n== 10. Brasil (Sinesp/MJSP) ==")
        print(b10.round(1).to_string())
        ev = _ler("brasil_sinesp_eventos.csv")
        cob = ev[ev.evento.isin(g.EVENTOS_MVI)].groupby("ano").n_ufs.min()
        print("menor nº de UFs com registro entre as categorias usadas, por ano:", cob.to_dict())


if __name__ == "__main__":
    main()
