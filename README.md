# Guerra, armas e relações internacionais

Miniprojeto reprodutível sobre gasto militar, transferências de armas e conflitos
armados, com foco de 2014 ao dado mais recente (2025). Produz dez figuras em português,
um roteiro de discussão e um rascunho de texto de divulgação.

## Como rodar

Requer Python 3.11 ou mais novo (testado em 3.14, Windows).

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m src.pipeline
```

O `pipeline` baixa os dados, limpa, gera as figuras e imprime os números usados nos
textos. A primeira execução baixa cerca de 280 MB e leva de 20 a 30 minutos, quase tudo
por conta das onze planilhas do Sinesp (Brasil). Depois disso tudo fica em cache e roda
em menos de um minuto. Para refazer os downloads: `python -m src.pipeline --forcar`.

Para o notebook:

```bash
jupyter notebook notebooks/analise.ipynb
```

ou, sem abrir o navegador:

```bash
jupyter nbconvert --to notebook --execute --inplace notebooks/analise.ipynb
```

Etapas isoladas: `python -m src.download`, `python -m src.limpeza`,
`python -m src.graficos 1 2 5` (só as figuras indicadas), `python -m src.verifica`.

Antes de publicar qualquer figura, rode a auditoria de layout:

```bash
python -m src.auditoria
```

Ela regera as dez figuras nos dois formatos e reprova (código de saída 1) se houver
texto fora da margem de segurança, texto sobre texto, rótulo atravessando barra, linha
de série ou marcador, fonte abaixo de 20 px no formato Instagram, ou arquivo com
dimensões diferentes das esperadas. A mesma checagem roda toda vez que uma figura é
salva e avisa no terminal.

## Estrutura

```
data/raw/          arquivos originais + _manifesto.json (URL, data de acesso, versão)
data/processed/    tabelas limpas usadas pelas figuras
data/README.md     fontes, versões, download manual e cuidados de leitura
src/config.py      caminhos, lista de países, metas da OTAN
src/download.py    baixa cada fonte
src/limpeza.py     raw -> processed
src/graficos.py    uma função por figura (layout medido, dois formatos)
src/auditoria.py   checagem automática de texto cortado, sobreposto ou ilegível
src/verifica.py    imprime os números citados nos textos
src/pipeline.py    roda tudo
notebooks/analise.ipynb
outputs/figures/   figNN_*.png (16:9, 3840×2160), figNN_*.svg, figNN_*_instagram.png (4:5, 1080×1350)
outputs/texto/     roteiro_reuniao.md, rascunho_publicacao.md
```

## Figuras

| Nº | Arquivo | Conteúdo | Fonte |
|---|---|---|---|
| 1 | `fig01_gasto_mundial` | Gasto militar mundial, 1988–2025, e % do PIB, 1960–2025 | SIPRI; Banco Mundial |
| 2 | `fig02_otan_pib` | % do PIB: OTAN europeia e Brasil, com metas de 2%, 3,5% e 5% | Banco Mundial |
| 3 | `fig03_ranking_gasto` | 15 maiores orçamentos em 2025 e variação desde 2015 | SIPRI |
| 4 | `fig04_exportadores_importadores` | Maiores exportadores e importadores, 2016–20 e 2021–25 | SIPRI (TIV) |
| 5 | `fig05_conflitos_tipo` | Conflitos ativos por tipo, 1946–2025 | UCDP/PRIO |
| 6 | `fig06_mortes_regiao` | Mortes em batalha por região, 1989–2025 | UCDP |
| 7 | `fig07_concentracao_mercado` | Participação nas exportações, janelas de 5 anos | SIPRI (TIV) |
| 8 | `fig08_conflito_armas` | Maiores importadores e exportadores × conflito ativo | SIPRI (TIV); UCDP |
| 9 | `fig09_gasto_mortes` | Gasto militar (% do PIB) × mortes em batalha, 2021–25 | Banco Mundial; UCDP |
| 10 | `fig10_brasil_violencia` | Brasil: mortes violentas e mortes por intervenção policial | MJSP/Sinesp |

## Decisões metodológicas

- **Meta da OTAN.** A Cúpula de Haia (junho de 2025) trocou os 2% de Gales (2014) por
  5% do PIB até 2035: 3,5% em defesa e 1,5% em gastos correlatos (infraestrutura,
  resiliência, indústria), com revisão em 2029. A Fig. 2 mostra as três linhas; a de
  3,5% é a que se compara ao dado de gasto militar.
- **Termos reais.** Séries em dólar usam preços constantes de 2024 (SIPRI). O Banco
  Mundial só publica dólares correntes, usados aqui apenas para conferência.
- **TIV em janelas de cinco anos**, como faz o próprio SIPRI, para suavizar entregas
  concentradas em poucos anos.
- **Envolvimento em conflito** = governo listado pelo UCDP como parte primária (lado A
  ou B). Apoio com tropas a outro governo não conta.
- **Figuras 8 e 9 mostram associação, não causa.**
- **Brasil.** A fonte usada é o Sinesp/MJSP, e não o Anuário do Fórum Brasileiro de
  Segurança Pública, porque só a primeira tem download automático. Ver ressalvas em
  `data/README.md`.

## Fora desta versão

- Uso de inteligência artificial em guerra: não há base quantitativa padronizada.
- ACLED (exige cadastro), que permitiria incluir violência política abaixo do limiar do UCDP.
- Violência não estatal e contra civis (UCDP GED), que mudaria o quadro do Sahel, do
  Sudão e de Gaza.
- Comparação com os percentuais oficiais da OTAN.
