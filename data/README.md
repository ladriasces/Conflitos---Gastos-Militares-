# Dados

Todas as bases foram baixadas automaticamente por `src/download.py` em **13/10/2026**.
A data de acesso, a URL exata e a data do arquivo no servidor ficam gravadas em
`data/raw/_manifesto.json` a cada execução. Nenhum valor foi digitado, estimado ou
completado à mão: o que falta na fonte aparece como lacuna.

## Fontes

| Base | Arquivo em `data/raw/` | URL | Versão | Usada em |
|---|---|---|---|---|
| Banco Mundial, World Development Indicators: gasto militar em US$ correntes (`MS.MIL.XPND.CD`) e em % do PIB (`MS.MIL.XPND.GD.ZS`) | `wb_MS.MIL.XPND.CD.json`, `wb_MS.MIL.XPND.GD.ZS.json`, `wb_paises.json` | https://api.worldbank.org/v2/country/all/indicator/MS.MIL.XPND.GD.ZS | WDI, atualização de 08/10/2026; série 1960–2025. Origem dos dados: SIPRI | Fig. 1, 2, 9 |
| SIPRI Military Expenditure Database | `SIPRI-Milex-data-1949-2025.xlsx` | https://www.sipri.org/sites/default/files/SIPRI-Milex-data-1949-2025.xlsx | Edição de abril de 2026, 1949–2025; US$ constantes de 2024 | Fig. 1, 3 |
| SIPRI Arms Transfers Database, tabelas de TIV por exportador e por importador | `sipri_tiv_exportadores.csv`, `sipri_tiv_importadores.csv` | https://armstransfers.sipri.org/ArmsTransfer/ImportExport | Consulta de 13/10/2026, entregas de 1992–2025 | Fig. 4, 7, 8 |
| UCDP/PRIO Armed Conflict Dataset | `ucdp_acd/UcdpPrioConflict_v26_1.csv` | https://ucdp.uu.se/downloads/ucdpprio/ucdp-prio-acd-261-csv.zip | v26.1, 1946–2025 | Fig. 5, 8 |
| UCDP Battle-Related Deaths Dataset (nível de conflito) | `ucdp_brd/BattleDeaths_v26_1_conf.csv` | https://ucdp.uu.se/downloads/brd/ucdp-brd-conf-261-csv.zip | v26.1, 1989–2025 | Fig. 6, 9 |
| MJSP, Sinesp VDE: base de dados dos gestores estaduais | `sinesp/bancovde-2015.xlsx` … `bancovde-2025.xlsx` (11 arquivos, ~270 MB) | https://www.gov.br/mj/pt-br/assuntos/sua-seguranca/seguranca-publica/estatistica/download/dnsp-base-de-dados/ | Arquivos anuais 2015–2025; 2026 não usado por estar incompleto | Fig. 10 |

Não usadas: ACLED (exige cadastro) e a API do UCDP (exige token; os CSVs trazem o mesmo conteúdo).

## Se o download automático falhar

O script avisa no terminal e segue com o resto. Para repor um arquivo à mão:

- **SIPRI Milex**: em https://www.sipri.org/databases/milex, baixar a planilha Excel com
  os dados de todos os países (1949–2025) e salvar em `data/raw/` com o nome
  `SIPRI-Milex-data-1949-2025.xlsx`.
- **SIPRI Arms Transfers**: em https://armstransfers.sipri.org/ArmsTransfer/ImportExport
  (tabelas de TIV de importação/exportação), preencher o intervalo 1992–2025, pedir a
  tabela por fornecedor (todos os países) e baixar o CSV como
  `data/raw/sipri_tiv_exportadores.csv`; repetir por destinatário e salvar como
  `data/raw/sipri_tiv_importadores.csv`. O arquivo deve manter o cabeçalho original do
  SIPRI (as linhas de aviso antes da tabela).
- **UCDP**: em https://ucdp.uu.se/downloads/, baixar o CSV do "UCDP/PRIO Armed Conflict
  Dataset version 26.1" e extrair em `data/raw/ucdp_acd/`; baixar o CSV "Conflict-level"
  do "UCDP Battle-Related Deaths Dataset version 26.1" e extrair em `data/raw/ucdp_brd/`.
- **Sinesp**: na página "Base de Dados e Notas Metodológicas dos Gestores Estaduais –
  Sinesp VDE" do MJSP, baixar `bancovde-AAAA.xlsx` de cada ano e salvar em
  `data/raw/sinesp/`.

## Tabelas processadas (`data/processed/`)

| Arquivo | Conteúdo |
|---|---|
| `gasto_banco_mundial.csv` | país/agregado × ano: gasto em US$ correntes e % do PIB |
| `gasto_sipri_regioes.csv` | mundo e regiões × ano: US$ bilhões constantes de 2024 |
| `gasto_sipri_paises.csv` | país × ano: US$ milhões constantes de 2024 e % do PIB |
| `armas_tiv.csv` | país × ano × papel (exportador/importador): milhões de TIV |
| `conflitos_por_tipo.csv` | ano × tipo de conflito: número de conflitos ativos |
| `conflitos_por_pais.csv` | país × ano: conflitos em que o governo é parte primária e mortes em batalha |
| `mortes_por_regiao.csv` | ano × região: mortes em batalha (melhor, baixa e alta) |
| `mortes_por_conflito.csv` | ano × conflito: mortes em batalha |
| `brasil_sinesp_eventos.csv` | ano × tipo de evento: vítimas no país e nº de UFs com registro |

## Cuidados de leitura

- **TIV não é dinheiro.** O *trend-indicator value* do SIPRI mede o volume de capacidade
  militar transferida, a partir de um valor de referência por tipo de equipamento. Não
  representa preço pago nem receita de vendas. Serve para comparar tendências e
  participações; por ser volátil ano a ano, usamos somas de cinco anos.
- **US$ constantes × correntes.** O total mundial de 2025 é US$ 2.771 bilhões na planilha
  do SIPRI (preços constantes de 2024) e US$ 2.856 bilhões no Banco Mundial (dólares
  correntes). São a mesma base em unidades diferentes. Em % do PIB as duas fontes
  coincidem em todos os 150 países comparados.
- **SIPRI × OTAN.** O SIPRI usa definição própria de gasto militar; os percentuais não
  coincidem com os divulgados pela OTAN, que é a régua oficial das metas de 2% e 3,5%.
- **Lacunas no gasto militar.** O SIPRI não publica total mundial para 1991. Vários
  países em guerra não têm dado recente (Síria e Iêmen não têm nenhum em 2021–2025;
  Sudão e Afeganistão têm um único ano). A Islândia aparece com gasto zero por não ter
  forças armadas e foi retirada da comparação da OTAN.
- **UCDP conta só conflito de base estatal** com ao menos 25 mortes em batalha no ano.
  Ficam de fora a violência entre grupos não estatais e os ataques deliberados a civis
  (o genocídio de Ruanda, por exemplo, não está na série de mortes em batalha). As
  estimativas de mortes têm intervalo amplo: em 2025, de 141 mil a 237 mil.
- **Mortes por país.** Em `conflitos_por_pais.csv`, uma guerra entre dois Estados é
  atribuída integralmente aos dois governos. Somar a coluna entre países conta em dobro.
- **Sinesp.** Os números vêm dos registros das secretarias estaduais. A cobertura varia:
  em 2015, uma UF não tem registro em parte das categorias. A soma usada na Fig. 10
  (homicídio doloso + feminicídio + latrocínio + lesão corporal seguida de morte + morte
  por intervenção de agente do Estado) aproxima o conceito de "mortes violentas
  intencionais" do Fórum Brasileiro de Segurança Pública, mas não é a série do Fórum.

## Citações sugeridas

- SIPRI Military Expenditure Database, 2026. Stockholm International Peace Research Institute.
- SIPRI Arms Transfers Database, 2026. Stockholm International Peace Research Institute.
- Gleditsch et al. (2002), "Armed Conflict 1946–2001: A New Dataset", *Journal of Peace
  Research* 39(5), e o artigo anual do UCDP no mesmo periódico (conferir a referência
  da versão 26.1 em https://ucdp.uu.se/downloads/ antes de publicar).
- World Bank, World Development Indicators.
- Ministério da Justiça e Segurança Pública, Sinesp Validador de Dados Estatísticos.
