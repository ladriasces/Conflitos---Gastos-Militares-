"""Caminhos, listas de países e parâmetros comuns do projeto."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
RAW = RAIZ / "data" / "raw"
PROCESSED = RAIZ / "data" / "processed"
FIGURAS = RAIZ / "outputs" / "figures"
TEXTO = RAIZ / "outputs" / "texto"
MANIFESTO = RAW / "_manifesto.json"

for _p in (RAW, PROCESSED, FIGURAS, TEXTO):
    _p.mkdir(parents=True, exist_ok=True)

# --- Fontes -----------------------------------------------------------------
WB_API = "https://api.worldbank.org/v2"
WB_INDICADORES = {
    "MS.MIL.XPND.CD": "gasto_usd_corrente",
    "MS.MIL.XPND.GD.ZS": "gasto_pct_pib",
}
SIPRI_MILEX_URL = "https://www.sipri.org/sites/default/files/SIPRI-Milex-data-1949-2025.xlsx"
SIPRI_MILEX_ARQ = RAW / "SIPRI-Milex-data-1949-2025.xlsx"
UCDP_VERSAO = "26.1"
UCDP_ARQUIVOS = {
    "acd": "https://ucdp.uu.se/downloads/ucdpprio/ucdp-prio-acd-261-csv.zip",
    "brd": "https://ucdp.uu.se/downloads/brd/ucdp-brd-conf-261-csv.zip",
}
SIPRI_AT_BACKEND = "https://atbackend.sipri.org/api/p"
SIPRI_AT_EXPORTADORES = RAW / "sipri_tiv_exportadores.csv"
SIPRI_AT_IMPORTADORES = RAW / "sipri_tiv_importadores.csv"
SIPRI_AT_ANO_INI, SIPRI_AT_ANO_FIM = 1992, 2025
SINESP_PASTA = RAW / "sinesp"
SINESP_ANOS = range(2015, 2026)  # 2026 ainda parcial; fica de fora
SINESP_URL = ("https://www.gov.br/mj/pt-br/assuntos/sua-seguranca/seguranca-publica/estatistica/"
              "download/dnsp-base-de-dados/bancovde-{ano}.xlsx/@@download/file")

# --- Recortes ---------------------------------------------------------------
ANO_INICIO_FOCO = 2014
ANO_INVASAO = 2022

# Membros europeus da OTAN (ISO3), exceto a Islândia: não tem forças armadas e
# aparece com gasto 0 na base, o que distorceria mediana e contagens.
# Suécia (2024) e Finlândia (2023) entram na série inteira para comparação,
# mesmo antes da adesão.
OTAN_EUROPA = [
    "ALB", "BEL", "BGR", "HRV", "CZE", "DNK", "EST", "FIN", "FRA", "DEU",
    "GRC", "HUN", "ITA", "LVA", "LTU", "LUX", "MNE", "NLD", "MKD",
    "NOR", "POL", "PRT", "ROU", "SVK", "SVN", "ESP", "SWE", "TUR", "GBR",
]
OTAN_DESTAQUES = ["POL", "DEU", "FRA", "GBR", "ITA", "ESP", "EST"]

# Metas da OTAN: Gales (2014) = 2% do PIB; Haia (jun/2025) = 5% até 2035,
# sendo 3,5% defesa "núcleo" + 1,5% gastos correlatos.
META_GALES = 2.0
META_HAIA_NUCLEO = 3.5
META_HAIA_TOTAL = 5.0
META_HAIA_ANO = 2035

NOMES_PT = {
    "USA": "Estados Unidos", "CHN": "China", "RUS": "Rússia", "DEU": "Alemanha",
    "IND": "Índia", "GBR": "Reino Unido", "SAU": "Arábia Saudita", "UKR": "Ucrânia",
    "FRA": "França", "JPN": "Japão", "KOR": "Coreia do Sul", "ISR": "Israel",
    "POL": "Polônia", "ITA": "Itália", "AUS": "Austrália", "CAN": "Canadá",
    "TUR": "Turquia", "ESP": "Espanha", "NLD": "Países Baixos", "DZA": "Argélia",
    "BRA": "Brasil", "MEX": "México", "EST": "Estônia", "LVA": "Letônia",
    "LTU": "Lituânia", "GRC": "Grécia", "SWE": "Suécia", "FIN": "Finlândia",
    "NOR": "Noruega", "DNK": "Dinamarca", "BEL": "Bélgica", "PRT": "Portugal",
    "ROU": "Romênia", "HUN": "Hungria", "CZE": "Tchéquia", "SVK": "Eslováquia",
    "SVN": "Eslovênia", "HRV": "Croácia", "BGR": "Bulgária", "ALB": "Albânia",
    "MNE": "Montenegro", "MKD": "Macedônia do Norte", "LUX": "Luxemburgo",
    "ISL": "Islândia", "PAK": "Paquistão", "IRN": "Irã", "TWN": "Taiwan",
    "SGP": "Singapura", "IDN": "Indonésia", "COL": "Colômbia", "KWT": "Kuwait",
    "QAT": "Catar", "EGY": "Egito", "ARE": "Emirados Árabes", "SDN": "Sudão",
    "ETH": "Etiópia", "MMR": "Mianmar", "NGA": "Nigéria", "MLI": "Mali",
    "BFA": "Burkina Faso", "SYR": "Síria", "YEM": "Iêmen", "IRQ": "Iraque",
    "AFG": "Afeganistão", "SOM": "Somália", "COD": "RD Congo", "LBN": "Líbano",
    "PSE": "Palestina", "NER": "Níger", "CHE": "Suíça", "OMN": "Omã",
    "DZA": "Argélia", "MAR": "Marrocos", "THA": "Tailândia", "PHL": "Filipinas",
    "ARM": "Armênia", "AZE": "Azerbaijão", "SSD": "Sudão do Sul", "HTI": "Haiti",
    "KEN": "Quênia", "UGA": "Uganda", "TCD": "Chade", "CMR": "Camarões",
    "MOZ": "Moçambique", "BDI": "Burundi", "RWA": "Ruanda", "LBY": "Líbia",
    "TJK": "Tajiquistão", "KGZ": "Quirguistão", "BEN": "Benin", "TGO": "Togo",
    "CAF": "Rep. Centro-Africana", "KHM": "Camboja", "JOR": "Jordânia",
    "BGD": "Bangladesh", "VNM": "Vietnã", "ZAF": "África do Sul", "SRB": "Sérvia",
    "BLR": "Belarus", "KAZ": "Cazaquistão", "ARG": "Argentina", "CHL": "Chile",
    "PER": "Peru", "VEN": "Venezuela", "ECU": "Equador", "BHR": "Bahrein",
    "ERI": "Eritreia", "DJI": "Djibuti", "GIN": "Guiné", "SEN": "Senegal",
    "TZA": "Tanzânia", "AGO": "Angola", "GHA": "Gana", "MRT": "Mauritânia",
}


def nome_pt(iso3: str, padrao: str | None = None) -> str:
    return NOMES_PT.get(iso3, padrao or iso3)
