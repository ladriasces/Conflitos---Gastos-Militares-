"""Transforma os arquivos de data/raw em tabelas 'tidy' em data/processed.

Uso: python -m src.limpeza

Nenhum valor é imputado: o que falta na fonte fica como NaN (ou fora da tabela)
e os nomes de países sem correspondência ISO3 são listados no terminal.
"""
from __future__ import annotations

import io
import json
import re

import pandas as pd

from . import config as c

# --- Nomes de países -> ISO3 -------------------------------------------------
# Grafias usadas por SIPRI e UCDP que diferem das do Banco Mundial.
APELIDOS = {
    "united states": "USA", "united states of america": "USA", "usa": "USA",
    "russia": "RUS", "ussr": "RUS", "soviet union": "RUS", "south korea": "KOR",
    "korea, south": "KOR", "north korea": "PRK", "korea, north": "PRK", "iran": "IRN",
    "egypt": "EGY", "syria": "SYR", "yemen": "YEM", "turkey": "TUR", "turkiye": "TUR",
    "türkiye": "TUR", "venezuela": "VEN", "vietnam": "VNM", "viet nam": "VNM", "laos": "LAO",
    "dr congo": "COD", "congo, dr": "COD", "congo, democratic republic": "COD",
    "democratic republic of the congo": "COD", "congo": "COG", "congo, republic": "COG",
    "congo, rep.": "COG", "ivory coast": "CIV", "cote d'ivoire": "CIV", "côte d'ivoire": "CIV",
    "taiwan": "TWN", "uae": "ARE", "united arab emirates": "ARE", "united kingdom": "GBR",
    "uk": "GBR", "myanmar": "MMR", "slovakia": "SVK", "czechia": "CZE", "czech republic": "CZE",
    "kyrgyzstan": "KGZ", "gambia": "GMB", "gambia, the": "GMB", "bahamas": "BHS",
    "brunei": "BRN", "cape verde": "CPV", "cabo verde": "CPV", "eswatini": "SWZ",
    "swaziland": "SWZ", "north macedonia": "MKD", "macedonia": "MKD", "palestine": "PSE",
    "bosnia-herzegovina": "BIH", "bosnia and herzegovina": "BIH", "timor-leste": "TLS",
    "east timor": "TLS", "kosovo": "XKX", "micronesia": "FSM", "saint lucia": "LCA",
    "st. lucia": "LCA", "serbia": "SRB", "cambodia": "KHM", "madagascar": "MDG",
    "zimbabwe": "ZWE", "hong kong": "HKG", "macao": "MAC", "sao tome and principe": "STP",
    "dominican republic": "DOM", "trinidad and tobago": "TTO", "south sudan": "SSD",
    "central african republic": "CAF", "equatorial guinea": "GNQ", "guinea-bissau": "GNB",
    "saint kitts and nevis": "KNA", "saint vincent": "VCT", "moldova": "MDA",
    "slovak republic": "SVK", "kyrgyz republic": "KGZ", "somalia": "SOM", "timor leste": "TLS",
}
_wb_nomes: dict[str, str] | None = None
_sem_iso: set[str] = set()


def _limpa_nome(nome: str) -> str:
    nome = re.sub(r"\(.*?\)", "", str(nome))          # "Russia (Soviet Union)" -> "Russia"
    nome = nome.replace("Government of", "").replace("*", "")
    return re.sub(r"\s+", " ", nome).strip().lower()


def iso3(nome: str) -> str | None:
    """ISO3 a partir do nome em inglês; None (e registro em _sem_iso) se não houver."""
    global _wb_nomes
    if _wb_nomes is None:
        paises = json.loads((c.RAW / "wb_paises.json").read_text(encoding="utf-8"))[1]
        _wb_nomes = {p["name"].lower(): p["id"] for p in paises if p["region"]["id"] != "NA"}
    chave = _limpa_nome(nome)
    cod = APELIDOS.get(chave) or _wb_nomes.get(chave)
    if cod is None and chave:
        _sem_iso.add(str(nome))
    return cod


# --- Banco Mundial -----------------------------------------------------------
def limpar_banco_mundial() -> pd.DataFrame:
    paises = json.loads((c.RAW / "wb_paises.json").read_text(encoding="utf-8"))[1]
    agregados = {p["id"] for p in paises if p["region"]["id"] == "NA"}
    tabelas = []
    for indicador, coluna in c.WB_INDICADORES.items():
        dados = json.loads((c.RAW / f"wb_{indicador}.json").read_text(encoding="utf-8"))[1]
        tabelas.append(pd.DataFrame({
            "iso3": [d["countryiso3code"] for d in dados],
            "pais": [d["country"]["value"] for d in dados],
            "ano": [int(d["date"]) for d in dados],
            coluna: [d["value"] for d in dados],
        }))
    df = tabelas[0].merge(tabelas[1], on=["iso3", "pais", "ano"], how="outer")
    df = df[df["iso3"] != ""].dropna(subset=list(c.WB_INDICADORES.values()), how="all")
    df["agregado"] = df["iso3"].isin(agregados)
    df = df.sort_values(["iso3", "ano"]).reset_index(drop=True)
    df.to_csv(c.PROCESSED / "gasto_banco_mundial.csv", index=False)
    return df


# --- SIPRI Milex -------------------------------------------------------------
def _ler_aba_sipri(aba: str, coluna_valor: str) -> pd.DataFrame:
    bruto = pd.read_excel(c.SIPRI_MILEX_ARQ, sheet_name=aba, header=None)
    linha_cab = bruto.index[bruto[0].astype(str).str.strip().isin(["Country", "Region"])][0]
    cab = bruto.loc[linha_cab]
    anos = {i: int(float(v)) for i, v in cab.items()
            if re.fullmatch(r"(19|20)\d\d(\.0)?", str(v).strip())}
    corpo = bruto.loc[linha_cab + 1:, [0, *anos]].rename(columns={0: "pais", **anos})
    longo = corpo.melt(id_vars="pais", var_name="ano", value_name=coluna_valor)
    # "...", ". ." = sem dado; "xxx" = país não existia. Viram NaN, sem imputação.
    longo[coluna_valor] = pd.to_numeric(longo[coluna_valor], errors="coerce")
    longo = longo.dropna(subset=["pais", coluna_valor])
    longo["pais"] = longo["pais"].astype(str).str.strip()
    return longo.astype({"ano": int})


def limpar_sipri_milex() -> tuple[pd.DataFrame, pd.DataFrame]:
    regioes = _ler_aba_sipri("Regional totals", "usd_bi_const2024").rename(columns={"pais": "regiao"})
    regioes.to_csv(c.PROCESSED / "gasto_sipri_regioes.csv", index=False)

    paises = _ler_aba_sipri("Constant (2024) US$", "usd_mi_const2024")
    pib = _ler_aba_sipri("Share of GDP", "pct_pib")
    pib["pct_pib"] *= 100
    paises = paises.merge(pib, on=["pais", "ano"], how="outer")
    paises["iso3"] = paises["pais"].map(iso3)
    paises = paises.sort_values(["pais", "ano"]).reset_index(drop=True)
    paises.to_csv(c.PROCESSED / "gasto_sipri_paises.csv", index=False)
    return regioes, paises


# --- UCDP --------------------------------------------------------------------
TIPOS_CONFLITO = {1: "Extrassistêmico", 2: "Interestatal", 3: "Intraestatal",
                  4: "Intraestatal internacionalizado"}
REGIOES_UCDP = {"1": "Europa", "2": "Oriente Médio", "3": "Ásia", "4": "África", "5": "Américas"}


def _regiao(valor) -> str:
    return REGIOES_UCDP.get(str(valor).strip(), "Mais de uma região")


def _governos(lado: str) -> list[str]:
    """ISO3 dos governos listados em side_a/side_b (grupos não estatais são ignorados)."""
    return [cod for parte in str(lado).split(", ") if parte.startswith("Government of")
            and (cod := iso3(parte))]


def limpar_ucdp() -> dict[str, pd.DataFrame]:
    acd = pd.read_csv(next((c.RAW / "ucdp_acd").glob("*.csv")))
    brd = pd.read_csv(next((c.RAW / "ucdp_brd").glob("*.csv")))

    por_tipo = (acd.assign(tipo=acd["type_of_conflict"].map(TIPOS_CONFLITO))
                .groupby(["year", "tipo"])["conflict_id"].nunique()
                .rename("n_conflitos").reset_index().rename(columns={"year": "ano"}))
    por_tipo.to_csv(c.PROCESSED / "conflitos_por_tipo.csv", index=False)

    por_regiao = (brd.assign(regiao=brd["region"].map(_regiao))
                  .groupby(["year", "regiao"])[["bd_best", "bd_low", "bd_high"]].sum()
                  .reset_index().rename(columns={"year": "ano", "bd_best": "mortes",
                                                 "bd_low": "mortes_min", "bd_high": "mortes_max"}))
    por_regiao.to_csv(c.PROCESSED / "mortes_por_regiao.csv", index=False)

    # Maiores conflitos por ano, para rotular picos nos gráficos e no texto.
    maiores = (brd.groupby(["year", "conflict_id", "location_inc"], as_index=False)["bd_best"].sum()
               .rename(columns={"year": "ano", "bd_best": "mortes", "location_inc": "local"})
               .sort_values(["ano", "mortes"], ascending=[True, False]))
    maiores.to_csv(c.PROCESSED / "mortes_por_conflito.csv", index=False)

    # Envolvimento por país: governo que é parte primária (side_a ou side_b).
    # Em guerras interestatais os dois governos recebem o conflito e as mortes
    # inteiras; a soma entre países, portanto, conta essas mortes em dobro.
    def explode(df: pd.DataFrame) -> pd.DataFrame:
        gov = df.apply(lambda r: sorted(set(_governos(r["side_a"]) + _governos(r["side_b"]))), axis=1)
        return df.assign(iso3=gov).explode("iso3").dropna(subset=["iso3"])

    envolv = (explode(acd).groupby(["iso3", "year"])
              .agg(n_conflitos=("conflict_id", "nunique"), intensidade_max=("intensity_level", "max"))
              .reset_index().rename(columns={"year": "ano"}))
    mortes = (explode(brd).groupby(["iso3", "year"])["bd_best"].sum()
              .rename("mortes").reset_index().rename(columns={"year": "ano"}))
    por_pais = envolv.merge(mortes, on=["iso3", "ano"], how="outer").sort_values(["iso3", "ano"])
    por_pais.to_csv(c.PROCESSED / "conflitos_por_pais.csv", index=False)
    return {"tipo": por_tipo, "regiao": por_regiao, "pais": por_pais, "maiores": maiores}


# --- SIPRI Arms Transfers ----------------------------------------------------
def _ler_tiv(arquivo, papel: str) -> pd.DataFrame:
    linhas = arquivo.read_text(encoding="utf-8").splitlines()
    ini = next(i for i, l in enumerate(linhas) if re.match(r"^(Exports by|Imports by|Supplier|Recipient),\d{4}", l))
    tab = pd.read_csv(io.StringIO("\n".join(linhas[ini:])), header=None, skiprows=1, dtype=str)
    anos = [int(a) for a in linhas[ini].split(",")[1:] if re.fullmatch(r"\d{4}", a)]
    tab = tab.iloc[:, :len(anos) + 1]
    tab.columns = ["pais", *anos]
    longo = tab.melt(id_vars="pais", var_name="ano", value_name="tiv_milhoes")
    # Campo vazio = nenhuma entrega identificada (zero); "0" = entre 0 e 0,5 milhão.
    longo["tiv_milhoes"] = pd.to_numeric(longo["tiv_milhoes"].str.strip(), errors="coerce").fillna(0)
    longo["pais"] = longo["pais"].str.strip()
    longo["total_mundial"] = longo["pais"].str.lower().str.startswith("total")
    longo["iso3"] = longo["pais"].where(~longo["total_mundial"]).map(lambda n: iso3(n) if isinstance(n, str) else None)
    longo["papel"] = papel
    return longo.astype({"ano": int})


def limpar_sipri_armas() -> pd.DataFrame | None:
    if not (c.SIPRI_AT_EXPORTADORES.exists() and c.SIPRI_AT_IMPORTADORES.exists()):
        print("[aviso] TIV do SIPRI ausente em data/raw; figuras 4, 7 e 8 serão puladas.")
        return None
    df = pd.concat([_ler_tiv(c.SIPRI_AT_EXPORTADORES, "exportador"),
                    _ler_tiv(c.SIPRI_AT_IMPORTADORES, "importador")], ignore_index=True)
    df.to_csv(c.PROCESSED / "armas_tiv.csv", index=False)
    return df


# --- Brasil (Sinesp/MJSP) ----------------------------------------------------
def limpar_sinesp() -> pd.DataFrame | None:
    """Soma nacional de vítimas por ano e tipo de evento. Lento: ~1-2 min por arquivo."""
    import openpyxl

    arquivos = sorted(c.SINESP_PASTA.glob("bancovde-*.xlsx")) if c.SINESP_PASTA.exists() else []
    if not arquivos:
        print("[aviso] Sinesp ausente em data/raw/sinesp; figura 10 será pulada.")
        return None
    destino = c.PROCESSED / "brasil_sinesp_eventos.csv"
    pronto = pd.read_csv(destino) if destino.exists() else pd.DataFrame(columns=["ano"])
    partes = [pronto]
    for arq in arquivos:
        ano = int(re.search(r"(\d{4})", arq.name).group(1))
        if ano in set(pronto["ano"]):
            continue
        ws = openpyxl.load_workbook(arq, read_only=True).worksheets[0]
        linhas = ws.iter_rows(values_only=True)
        cab = [str(x) for x in next(linhas)]
        i_ev, i_data, i_vit, i_uf = (cab.index(k) for k in ("evento", "data_referencia", "total_vitima", "uf"))
        soma: dict[tuple, float] = {}
        ufs: dict[str, set] = {}
        for l in linhas:
            if l[i_ev] is None or l[i_vit] is None:
                continue
            chave = (l[i_data].year, l[i_ev])
            soma[chave] = soma.get(chave, 0) + l[i_vit]
            ufs.setdefault(l[i_ev], set()).add(l[i_uf])
        partes.append(pd.DataFrame([{"ano": a, "evento": e, "vitimas": v, "n_ufs": len(ufs[e])}
                                    for (a, e), v in soma.items()]))
        pd.concat(partes, ignore_index=True).to_csv(destino, index=False)
        print(f"[ok] Sinesp {ano} agregado")
    df = pd.concat(partes, ignore_index=True).sort_values(["ano", "evento"]).reset_index(drop=True)
    df.to_csv(destino, index=False)
    return df


def main(incluir_brasil: bool = True) -> None:
    limpar_banco_mundial()
    limpar_sipri_milex()
    limpar_ucdp()
    limpar_sipri_armas()
    if incluir_brasil:
        limpar_sinesp()
    # Atores não estatais e organizações vêm marcados com * no SIPRI; não são países.
    sem_iso = sorted(n for n in _sem_iso if "*" not in n and "unknown" not in n)
    if sem_iso:
        print("[aviso] nomes sem ISO3 (ficam fora dos cruzamentos por país):", sem_iso)
    print("[ok] tabelas em data/processed:", sorted(p.name for p in c.PROCESSED.glob("*.csv")))


if __name__ == "__main__":
    main()
