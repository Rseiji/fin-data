# Referência de símbolos da API fin-data

Este documento padroniza os símbolos esperados por cada fonte de dados e o significado de cada padrão. O objetivo é servir como referência para integrações, consultas e manutenção da API.

## Regra geral

- Todos os `symbol` são normalizados para maiúsculas na API.
- O padrão varia por categoria de ativo.
- A API usa `asset_type` para distinguir o tipo de dado:
  - `stock`
  - `etf`
  - `crypto`
  - `currency`
  - `index`

---

## 1) Ações da B3

### Padrão

`<TICKER>`

### Exemplos

- `PETR4` → Petrobras PN
- `ITUB4` → Itaú Unibanco PN
- `SAPR11` → Santander PNB
- `VALE3` → Vale ON
- `BBAS3` → Banco do Brasil ON

### Significado

- A maioria dos tickers de ações brasileiras usa números no fim para identificar a classe do papel, como:
  - `3` = ON
  - `4` = PN
  - `11` = PNB / outra classe de ação listada na B3
- A parte inicial representa o código do ativo ou da empresa.

### Fonte

- Yahoo Finance / B3 via ticker com sufixo `.SA`
- Exemplos no código: `src/infrastructure/scrapers/stocks.py`

---

## 2) ETFs da B3

### Padrão

`<TICKER>`

### Exemplos

- `IVVB11` → ETF de índice de ações brasileiras
- `BOVA11` → ETF BOVA11
- `DIVO11` → ETF de dividendos
- `SMAL11` → ETF de empresas menores
- `XFIX11` → ETF de renda fixa

### Significado

- Os tickers de ETF também seguem o padrão da B3.
- Em geral, o sufixo final `11` indica que o ativo é um ETF ou fundo listados na B3.
- O prefixo geralmente identifica o nome do fundo ou da estratégia.

### Fonte

- Yahoo Finance / B3
- Exemplos no código: `src/infrastructure/scrapers/stocks.py`

---

## 3) Criptomoedas

### Padrão

`<CRYPTO><CURRENCY>`

### Exemplos

- `BTCUSD` → Bitcoin em dólares
- `ETHUSD` → Ethereum em dólares
- `BNBUSD` → Binance Coin em dólares
- `SOLUSD` → Solana em dólares
- `ADAUSD` → Cardano em dólares

### Significado

- O lado esquerdo indica a criptomoeda.
- O lado direito indica a moeda de referência.
- Neste projeto, a referência principal é `USD`.

### Fonte

- CoinGecko
- Mapemento em `src/infrastructure/scrapers/crypto.py`

---

## 4) Pares de moedas (FX)

### Padrão

`<BASE><QUOTE>`

### Exemplos

- `USDBRL` → dólar americano em reais
- `JPYBRL` → iene japonês em reais
- `USDEUR` → dólar americano em euro
- `EURUSD` → euro em dólar americano
- `GBPBRL` → libra esterlina em reais

### Significado

- O primeiro código é a moeda base.
- O segundo código é a moeda de cotação.
- Exemplo: `USDBRL` significa "quantos reais valem 1 dólar americano?"

### Fonte

- Open ER API / Frankfurter
- Mapemento em `src/infrastructure/scrapers/currencies.py`

---

## 5) Indicadores macroeconômicos do BCB

### Padrão

`<NOME_DO_INDICADOR>`

### Exemplos

- `SELIC` → taxa Selic
- `CDI` → taxa de CDI
- `IPCA` → inflação oficial do Brasil

### Significado

- Os símbolos são nomes padronizados do Banco Central do Brasil.
- Não seguem o mesmo esquema de ticker financeiro, porque são séries macroeconômicas e não ativos de mercado.

### Fonte

- API do Banco Central do Brasil (BCB/SGS)
- Mapemento em `src/infrastructure/scrapers/indexes.py`

---

## 6) Mapeamento por categoria

| Categoria | Exemplo | Pattern | Fonte |
|---|---|---|---|
| Ação B3 | `PETR4` | `<ticker>` | Yahoo Finance |
| ETF B3 | `BOVA11` | `<ticker>` | Yahoo Finance |
| Crypto | `BTCUSD` | `<coin><currency>` | CoinGecko |
| Moeda | `USDBRL` | `<base><quote>` | Open ER API |
| índice macro | `SELIC` | `<nome>` | BCB |

---

## 7) Recomendação de uso na API

Para novas integrações ou consultas, prefira manter a convenção abaixo:

- Ações e ETFs: usar o ticker oficial da B3 em letras maiúsculas.
- Criptos: usar sempre a moeda de referência em `USD` quando houver.
- Moedas: usar sempre `BASE` + `QUOTE` com ISO currency codes.
- Indicadores: usar a sigla oficial do BCB.

Exemplos válidos:

```text
PETR4
BOVA11
BTCUSD
USDBRL
SELIC
```

Exemplos inválidos:

```text
petr4
bova11
btc-usd
usdbrl
selic_br
```

---

## 8) Observações técnicas

A API e os scrapers fazem o seguinte:

- `symbol.upper()` na maioria das consultas para garantir padronização.
- `asset_type` diferencia categorias no banco e nas respostas.
- Cada scraper mantém seu próprio mapeamento de símbolos para a fonte correta.

Esse padrão deve ser copiado ao adicionar novos símbolos ou novas fontes de dados.
