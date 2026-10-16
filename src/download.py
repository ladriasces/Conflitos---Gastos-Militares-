"""Baixa as fontes que permitem download automático e registra o que foi obtido.

Uso: python -m src.download [--forcar]

Fontes que exigem download manual não interrompem a execução: a função
correspondente devolve False e imprime o que baixar e onde salvar.
"""
from __future__ import annotations

import io
import json
import sys
import zipfile
from datetime import date

import requests

from . import config as c

CABECALHOS = {"User-Agent": "Mozilla/5.0 (projeto de pesquisa LADRI)"}
TIMEOUT = 120


def _ler_manifesto() -> dict:
    if c.MANIFESTO.exists():
        return json.loads(c.MANIFESTO.read_text(encoding="utf-8"))
    return {}


def _registrar(chave: str, **info) -> None:
    m = _ler_manifesto()
    m[chave] = {"data_acesso": date.today().isoformat(), **info}
    c.MANIFESTO.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")


def baixar_banco_mundial(forcar: bool = False) -> bool:
    """Indicadores de gasto militar (origem SIPRI) para todos os países e agregados."""
    ok = True
    for indicador in c.WB_INDICADORES:
        destino = c.RAW / f"wb_{indicador}.json"
        if destino.exists() and not forcar:
            continue
        url = f"{c.WB_API}/country/all/indicator/{indicador}"
        r = requests.get(url, params={"format": "json", "per_page": 20000, "date": "1960:2030"},
                         headers=CABECALHOS, timeout=TIMEOUT)
        r.raise_for_status()
        meta, _ = r.json()
        if meta["pages"] != 1:
            raise RuntimeError(f"Banco Mundial paginou {indicador}: aumentar per_page")
        destino.write_bytes(r.content)
        _registrar(f"banco_mundial_{indicador}", url=r.url, arquivo=destino.name,
                   versao=f"WDI, atualização {meta['lastupdated']}")
        print(f"[ok] Banco Mundial {indicador}: {meta['total']} observações")

    destino = c.RAW / "wb_paises.json"
    if not destino.exists() or forcar:
        r = requests.get(f"{c.WB_API}/country", params={"format": "json", "per_page": 400},
                         headers=CABECALHOS, timeout=TIMEOUT)
        r.raise_for_status()
        destino.write_bytes(r.content)
        _registrar("banco_mundial_paises", url=r.url, arquivo=destino.name, versao="metadados de países")
    return ok


def baixar_sipri_milex(forcar: bool = False) -> bool:
    if c.SIPRI_MILEX_ARQ.exists() and not forcar:
        return True
    r = requests.get(c.SIPRI_MILEX_URL, headers=CABECALHOS, timeout=TIMEOUT)
    if r.status_code != 200 or r.content[:2] != b"PK":
        print("[manual] SIPRI Milex: baixe 'SIPRI-Milex-data-1949-2025.xlsx' em "
              "https://www.sipri.org/databases/milex e salve em data/raw/")
        return False
    c.SIPRI_MILEX_ARQ.write_bytes(r.content)
    _registrar("sipri_milex", url=c.SIPRI_MILEX_URL, arquivo=c.SIPRI_MILEX_ARQ.name,
               versao=f"SIPRI Military Expenditure Database 1949-2025 "
                      f"(arquivo de {r.headers.get('Last-Modified', 's/d')})")
    print(f"[ok] SIPRI Milex: {len(r.content) / 1e3:.0f} KB")
    return True


def baixar_ucdp(forcar: bool = False) -> bool:
    ok = True
    for chave, url in c.UCDP_ARQUIVOS.items():
        pasta = c.RAW / f"ucdp_{chave}"
        if pasta.exists() and any(pasta.glob("*.csv")) and not forcar:
            continue
        r = requests.get(url, headers=CABECALHOS, timeout=TIMEOUT)
        if r.status_code != 200 or r.content[:2] != b"PK":
            print(f"[manual] UCDP {chave}: baixe o CSV em https://ucdp.uu.se/downloads/ "
                  f"e extraia em data/raw/ucdp_{chave}/")
            ok = False
            continue
        pasta.mkdir(exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            nomes = [n for n in z.namelist() if n.lower().endswith(".csv")]
            for n in nomes:
                (pasta / n.split("/")[-1]).write_bytes(z.read(n))
        _registrar(f"ucdp_{chave}", url=url, arquivo=f"ucdp_{chave}/{', '.join(nomes)}",
                   versao=f"UCDP versão {c.UCDP_VERSAO}")
        print(f"[ok] UCDP {chave}: {nomes}")
    return ok


def _filtros_sipri_at(ano_ini: int, ano_fim: int, por_exportador: bool) -> dict:
    """Mesmo corpo de requisição que o formulário 'Import/Export TIV tables' envia."""
    vazio = {"oldField": "", "condition": "", "value2": "", "listData": []}
    filtros = [{"field": "Year range 1", "oldField": "", "condition": "contains",
                "value1": ano_ini, "value2": ano_fim, "listData": []}]
    if por_exportador:
        filtros.append({"field": "orderbyseller", "value1": "", **vazio})
    filtros += [{"field": "summarize-by", "value1": "country", **vazio},
                {"field": "DeliveryType", "value1": "delivered", **vazio},
                {"field": "Status", "value1": "0", **vazio}]
    return {"filters": filtros, "logic": "AND"}


def baixar_sipri_armas(forcar: bool = False) -> bool:
    """Tabelas de TIV por exportador e por importador (SIPRI Arms Transfers Database).

    O site só oferece formulário; aqui se faz a mesma consulta pública que o
    formulário faz. Se o SIPRI mudar o serviço, cai-se no download manual.
    """
    ok = True
    for destino, por_exportador in [(c.SIPRI_AT_EXPORTADORES, True), (c.SIPRI_AT_IMPORTADORES, False)]:
        if destino.exists() and not forcar:
            continue
        try:
            r = requests.post(f"{c.SIPRI_AT_BACKEND}/trades/import-export-csv-str/",
                              json=_filtros_sipri_at(c.SIPRI_AT_ANO_INI, c.SIPRI_AT_ANO_FIM, por_exportador),
                              headers={**CABECALHOS, "Origin": "https://armstransfers.sipri.org"},
                              timeout=TIMEOUT)
            r.raise_for_status()
            texto = r.json()["result"]
            if "trend-indicator" not in texto or len(texto.splitlines()) < 20:
                raise ValueError("resposta inesperada")
        except Exception as e:
            papel = "Suppliers (exportadores)" if por_exportador else "Recipients (importadores)"
            print(f"[manual] SIPRI Arms Transfers ({e}). Em https://armstransfers.sipri.org/ArmsTransfer/ImportExport "
                  f"escolha {papel}, anos {c.SIPRI_AT_ANO_INI}-{c.SIPRI_AT_ANO_FIM}, 'Download as CSV' "
                  f"e salve como data/raw/{destino.name}")
            ok = False
            continue
        destino.write_text(texto, encoding="utf-8")
        gerado = next((l for l in texto.splitlines() if l.startswith("Data generated")), "")
        _registrar(destino.stem, url="https://armstransfers.sipri.org/ArmsTransfer/ImportExport",
                   arquivo=destino.name,
                   versao=f"SIPRI Arms Transfers Database, {c.SIPRI_AT_ANO_INI}-{c.SIPRI_AT_ANO_FIM}. {gerado}")
        print(f"[ok] SIPRI Arms Transfers: {destino.name}")
    return ok


def baixar_sinesp(forcar: bool = False) -> bool:
    """Base de Dados e Notas Metodológicas dos Gestores Estaduais (Sinesp VDE), MJSP.

    Um arquivo .xlsx por ano (~25 MB cada), por município e mês.
    """
    ok = True
    c.SINESP_PASTA.mkdir(exist_ok=True)
    for ano in c.SINESP_ANOS:
        destino = c.SINESP_PASTA / f"bancovde-{ano}.xlsx"
        if destino.exists() and not forcar:
            continue
        url = c.SINESP_URL.format(ano=ano)
        try:
            for tentativa in range(3):  # o servidor do gov.br às vezes corta a conexão
                try:
                    r = requests.get(url, headers=CABECALHOS, timeout=600)
                    break
                except requests.exceptions.RequestException:
                    if tentativa == 2:
                        raise
            if r.status_code != 200 or r.content[:2] != b"PK":
                raise ValueError(f"HTTP {r.status_code}")
        except Exception as e:
            print(f"[manual] Sinesp {ano} ({e}): baixe 'bancovde-{ano}.xlsx' em "
                  "https://www.gov.br/mj/pt-br/assuntos/sua-seguranca/seguranca-publica/estatistica/dados-nacionais-1/"
                  "base-de-dados-e-notas-metodologicas-dos-gestores-estaduais-sinesp-vde-2022-e-2023 "
                  "e salve em data/raw/sinesp/")
            ok = False
            continue
        destino.write_bytes(r.content)
        _registrar(f"sinesp_{ano}", url=url, arquivo=f"sinesp/{destino.name}",
                   versao=f"Sinesp VDE {ano} (arquivo de {r.headers.get('Last-Modified', 's/d')})")
        print(f"[ok] Sinesp {ano}: {len(r.content) / 1e6:.0f} MB")
    return ok


def main(forcar: bool = False) -> dict[str, bool]:
    resultado = {}
    for nome, func in [("banco_mundial", baixar_banco_mundial),
                       ("sipri_milex", baixar_sipri_milex),
                       ("ucdp", baixar_ucdp),
                       ("sipri_armas", baixar_sipri_armas),
                       ("sinesp", baixar_sinesp)]:
        try:
            resultado[nome] = func(forcar)
        except Exception as e:  # rede fora do ar não deve derrubar as demais fontes
            print(f"[erro] {nome}: {e}")
            resultado[nome] = False
    return resultado


if __name__ == "__main__":
    print(main(forcar="--forcar" in sys.argv))
