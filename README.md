# Gasto militar, transferências de armas e conflitos armados (2014–2025)

**LADRI · ASCES** — grupo de pesquisa em análise de dados em Relações Internacionais

---

## Resumo

Este repositório reúne uma análise exploratória e reprodutível da relação entre gasto
militar, comércio internacional de armas e conflitos armados, com ênfase no período de
2014 a 2025. Os dados vêm de cinco bases públicas: SIPRI Military Expenditure Database,
SIPRI Arms Transfers Database, UCDP/PRIO Armed Conflict Dataset, UCDP Battle-Related
Deaths Dataset e Sinesp/MJSP. O processamento é integralmente automatizado em Python,
do download à geração das figuras.

Os resultados indicam que o gasto militar mundial atingiu US$ 2,77 trilhões em 2025
(preços constantes de 2024), o maior valor da série iniciada em 1988 e 43% acima do
nível de 2014. Como proporção do PIB mundial, contudo, o gasto (2,5%) permanece bem
abaixo do patamar da década de 1960 (6,0%). A expansão recente concentra-se na Europa,
onde o número de membros da OTAN acima de 2% do PIB passou de 2 para 21 entre 2014 e
2025. O mercado de armas tornou-se mais dependente dos Estados Unidos (42% das
exportações em 2021–25), enquanto a participação russa caiu de 26% para 7%. O UCDP
registra 65 conflitos de base estatal ativos em 2025, recorde desde 1946, oito deles
interestatais. No nível dos países, a associação entre intensidade do conflito e esforço
militar é fraca (ρ de Spearman = 0,22). Para o Brasil, a análise documenta a queda das
mortes violentas desde 2017 e o aumento da parcela atribuída a agentes do Estado, de
4,8% em 2015 para 16,0% em 2025.

**Palavras-chave:** gasto militar; comércio de armas; conflitos armados; OTAN; SIPRI;
UCDP; segurança internacional; violência letal no Brasil.

---

## 1. Questões exploradas

1. Como evoluiu o gasto militar mundial em termos absolutos e relativos ao PIB?
2. Em que medida os membros europeus da OTAN convergiram para as metas da aliança, e
   como o Brasil se compara a eles?
3. Quem são os principais exportadores e importadores de armas, e quão concentrado é o
   mercado?
4. Como evoluíram o número de conflitos armados e as mortes em combate, por tipo e por
   região?
5. Há associação, no nível dos países, entre envolvimento em conflito, comércio de
   armas e gasto militar?
6. Como se comporta a violência letal no Brasil, em especial a causada por agentes do
   Estado?

## 2. Dados

| Base | Variáveis usadas | Cobertura | Versão |
|---|---|---|---|
| SIPRI Military Expenditure Database | Gasto militar em US$ constantes de 2024; totais regionais | 1949–2025 (total mundial desde 1988) | Edição de abril de 2026 |
| Banco Mundial, World Development Indicators | `MS.MIL.XPND.GD.ZS` (% do PIB) e `MS.MIL.XPND.CD` (US$ correntes), ambos com origem no SIPRI | 1960–2025 | Atualização de 08/10/2026 |
| SIPRI Arms Transfers Database | Volume de transferências de grandes armas, em TIV, por exportador e importador | 1992–2025 | Consulta de 13/10/2026 |
| UCDP/PRIO Armed Conflict Dataset | Conflitos ativos por ano, tipo e partes | 1946–2025 | v26.1 |
| UCDP Battle-Related Deaths Dataset | Mortes em batalha (estimativas baixa, melhor e alta) por conflito e região | 1989–2025 | v26.1 |
| MJSP, Sinesp VDE | Vítimas por tipo de ocorrência, por município e mês | 2015–2025 | Arquivos anuais publicados até out. 2026 |

URLs, datas de acesso e procedimentos de download manual estão em
[`data/README.md`](data/README.md). O arquivo `data/raw/_manifesto.json` registra, para
cada arquivo baixado, a URL exata, a data de acesso e a versão informada pela fonte.

## 3. Métodos

**Princípio geral.** Nenhum valor foi imputado, interpolado ou digitado manualmente.
Ausências na fonte permanecem como lacunas e são declaradas nas figuras (por exemplo, o
SIPRI não publica total mundial para 1991; Síria e Iêmen não têm dado de gasto em
2021–2025).

**Gasto militar.** Comparações no tempo usam US$ constantes de 2024 (SIPRI). A
proporção do PIB vem do Banco Mundial, que reproduz a série do SIPRI; as duas fontes
coincidem nos 150 países com dado em 2025. Os percentuais seguem a definição de gasto
militar do SIPRI, que difere da adotada pela OTAN, de modo que não reproduzem os números
oficiais da aliança. A Islândia, sem forças armadas, foi excluída do grupo europeu da
OTAN; Finlândia e Suécia integram a série inteira, apesar da adesão em 2023 e 2024.

**Metas da OTAN.** São marcadas a meta de 2% do PIB (Cúpula de Gales, 2014) e a meta
de 5% até 2035 (Cúpula de Haia, junho de 2025), composta de 3,5% para defesa
propriamente dita e 1,5% para gastos correlatos. A linha de 3,5% é a comparável ao
conceito de gasto militar.

**Transferências de armas.** O SIPRI mede volume em TIV (*trend-indicator value*), um
indicador de capacidade militar transferida baseado em custos de produção de
referência. **O TIV não é valor monetário**: não equivale a preço pago nem a receita de
exportação. Para reduzir a volatilidade das entregas, usam-se somas de cinco anos
(2016–20 e 2021–25) e, para a concentração do mercado, janelas móveis de cinco anos.

**Conflitos e mortes.** Adota-se a definição do UCDP: conflito de base estatal é
uma incompatibilidade em que ao menos uma das partes é um governo e que causa 25 ou
mais mortes em batalha no ano. Os tipos são extrassistêmico, interestatal, intraestatal
e intraestatal internacionalizado. As mortes usam a melhor estimativa, com o intervalo
entre as estimativas baixa e alta exibido nas figuras.

**Envolvimento por país.** Um país é considerado envolvido em conflito quando seu
governo aparece como parte primária (lado A ou B) no UCDP. Apoio com tropas a outro
governo não conta. Em guerras interestatais, as mortes são atribuídas integralmente a
cada governo participante; por isso, somas entre países contam essas mortes em dobro.
A associação entre mortes em batalha e gasto militar (% do PIB) é medida pela
correlação de postos de Spearman, adequada a distribuições muito assimétricas.

**Brasil.** As mortes violentas somam cinco categorias do Sinesp: homicídio doloso,
feminicídio, latrocínio, lesão corporal seguida de morte e morte por intervenção de
agente do Estado. A soma aproxima, mas não reproduz, o indicador de mortes violentas
intencionais (MVI) do Fórum Brasileiro de Segurança Pública. O Sinesp foi preferido por
permitir download automático e auditável. O ano de 2026, ainda incompleto, foi excluído.

**Controle de qualidade.** Os números citados neste documento são impressos
diretamente das tabelas processadas por `src/verifica.py`, que também confronta o
Banco Mundial com a planilha do SIPRI. As figuras passam por uma auditoria automática
de layout (`src/auditoria.py`) que reprova texto cortado, sobreposto ou abaixo do
tamanho mínimo.


## 4. Reprodutibilidade

Requer Python 3.11 ou superior (testado em Python 3.14, Windows 11).

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m src.pipeline
```

O pipeline baixa os dados, gera as tabelas processadas, produz as figuras e imprime os
números citados neste documento. A primeira execução transfere cerca de 280 MB e leva
de 20 a 30 minutos, sobretudo pelos arquivos do Sinesp. As execuções seguintes usam os
arquivos em cache. Os dados brutos não são versionados; as tabelas processadas estão em
`data/processed/` e permitem regerar as figuras sem novo download.

| Comando | Função |
|---|---|
| `python -m src.download` | Baixa as bases e atualiza o manifesto |
| `python -m src.limpeza` | Gera as tabelas de `data/processed/` |
| `python -m src.graficos [n ...]` | Gera todas as figuras ou apenas as indicadas |
| `python -m src.auditoria` | Regera as figuras e audita o layout (código de saída 1 em caso de falha) |
| `python -m src.verifica` | Imprime os números usados no texto e o cruzamento entre fontes |

O notebook [`notebooks/analise.ipynb`](notebooks/analise.ipynb) percorre a análise do
início ao fim. Além das figuras 16:9 versionadas aqui, o código gera localmente versões
em SVG e no formato 4:5 (1080×1350 px) para divulgação.

## 5. Estrutura do repositório

```
├── README.md                 este documento
├── requirements.txt          dependências
├── data/
│   ├── README.md             fontes, versões, download manual e cuidados de leitura
│   ├── raw/_manifesto.json   URL, data de acesso e versão de cada arquivo baixado
│   └── processed/            nove tabelas limpas (CSV) usadas nas figuras
├── notebooks/
│   └── analise.ipynb         análise completa, executada
├── outputs/figures/          dez figuras em PNG, 3840×2160 px
└── src/
    ├── config.py             caminhos, listas de países e metas da OTAN
    ├── download.py           aquisição dos dados
    ├── limpeza.py            padronização e agregação
    ├── graficos.py           uma função por figura
    ├── auditoria.py          controle de qualidade do layout das figuras
    ├── verifica.py           conferência dos números citados
    └── pipeline.py           execução de ponta a ponta
```

## 6. Como citar

> LADRI – ASCES. *Gasto militar, transferências de armas e conflitos armados
> (2014–2025)*. Versão 1.0. Repositório de dados e código, out. 2026. Disponível em:
> https://github.com/ladriasces/Conflitos---Gastos-Militares-.


O código e a primeira versão dos textos foram produzidos com assistência do Claude
(Anthropic), sob orientação e revisão do LADRI. Todos os números foram gerados a partir
das bases citadas e conferidos com `src/verifica.py`.
