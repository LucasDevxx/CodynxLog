# CodynxLog

O CodynxLog e um sistema simples de controle financeiro pessoal executado pelo terminal. O projeto foi criado para um portfólio universitário, com foco em código fácil de ler, testar e modificar.

## Sobre o projeto

O objetivo de aprendizagem e praticar fundamentos de Python em um programa completo: entrada de dados, validação, funções, persistência em JSON, tratamento de exceções e testes automatizados.

Os registros ficam em um arquivo `dados.json` criado automaticamente na pasta do projeto. Esse arquivo contém dados financeiros locais e não deve ser publicado no GitHub.

## Funcionalidades

- Cadastro de receitas e despesas.
- Consulta do total de receitas, despesas e saldo.
- Listagem ordenada por data.
- Edicao com manutencao de campos usando Enter.
- Exclusao protegida por confirmacao.
- Resumo mensal por mes e ano.
- Validacao de valores, datas, IDs e arquivo JSON.
- Salvamento atomico para reduzir risco de perda durante a gravacao.
- Encerramento controlado com Ctrl+C ou EOF.

## Estrutura dos arquivos

```text
CodynxLog/
├── main.py
├── README.md
├── .gitignore
└── tests/
    └── test_main.py
```

O arquivo `dados.json` aparece automaticamente depois do primeiro cadastro e permanece ignorado pelo Git.

## Tecnologias utilizadas

Python 3.11 ou superior e bibliotecas da linguagem padrao:

- `json`
- `pathlib`
- `datetime`
- `decimal`

## Como executar

Abra a pasta do projeto no VS Code. Depois, abra o terminal integrado em **Terminal > Novo Terminal** e execute:

```text
python main.py
```

O arquivo `dados.json` sera criado somente quando uma movimentacao for salva.

### Formatos aceitos

Valores podem usar virgula ou ponto como separador decimal. Um ponto com exatamente tres digitos, em um agrupamento valido, e interpretado como separador de milhar:

| Entrada | Valor salvo |
|---|---:|
| `1500` | `1500.00` |
| `1.500` | `1500.00` |
| `1.500,50` | `1500.50` |
| `1500,50` | `1500.50` |
| `1500.50` | `1500.50` |
| `55.00` | `55.00` |
| `1,50` | `1.50` |

Entradas com separadores conflitantes ou agrupamento invalido sao rejeitadas. Valores sao tratados com `Decimal`, arredondados para duas casas e nunca convertidos para `float`.

Datas podem ser informadas como `AAAA-MM-DD`, `DD-MM-AAAA` ou `DD/MM/AAAA`. Todas sao salvas internamente como `AAAA-MM-DD`.

## Como utilizar o menu

Ao executar o programa, escolha uma opcao digitando o numero correspondente:

```text
1 - Adicionar receita
2 - Adicionar despesa
3 - Consultar saldo
4 - Listar movimentacoes
5 - Editar movimentacao
6 - Excluir movimentacao
7 - Resumo mensal
0 - Sair
```

Para editar, informe o ID e pressione Enter em um campo para manter o valor anterior. Para excluir, confirme com `s` ou `sim`. Ctrl+C e EOF encerram o programa de forma controlada.

## Como executar os testes

```text
python -m unittest discover -s tests -v
```

## Exemplo fictício de funcionamento

```text
================================
           CODYNXLOG
================================

1 - Adicionar receita
2 - Adicionar despesa
3 - Consultar saldo
4 - Listar movimentacoes
5 - Editar movimentacao
6 - Excluir movimentacao
7 - Resumo mensal
0 - Sair

Escolha uma opcao: 1
Descricao: Bolsa de estudos
Valor: 2.000,00
Data (AAAA-MM-DD, DD-MM-AAAA ou DD/MM/AAAA): 19/11/2026
Movimentacao cadastrada com sucesso.
```

Outro exemplo fictício é cadastrar uma despesa com a descrição `Material de estudo`, valor `150,50` e data `2026-11-20`. Esses exemplos não representam dados reais de nenhuma pessoa.

## Conceitos praticados

- Funcoes com responsabilidades claras.
- Listas e dicionarios.
- Estruturas condicionais.
- Lacos de repeticao.
- Manipulacao de arquivos JSON.
- Tratamento de excecoes.
- Uso de `Decimal` para valores monetarios.

## Limitações

O sistema e local e executado apenas no terminal. Ele nao possui usuarios, sincronizacao entre computadores, banco de dados ou interface grafica. O arquivo `dados.json` deve ser mantido privado. Registros antigos ambíguos não são reinterpretados automaticamente, pois não é possível determinar com segurança a intenção original do valor.
