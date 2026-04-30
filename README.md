# Injective Derivatives Dashboard

https://injective-derivatives-dashboard-bazndcfmcrsvvkn6p3oxvi.streamlit.app/

A live analytics dashboard for perpetual futures markets on the Injective blockchain.

## Overview

Injective runs a fully on-chain orderbook derivatives exchange where every trade, liquidation, and funding payment is publicly verifiable. This dashboard surfaces that data in real time across all 60 active perpetual markets.

## Features

### Market Analytics
- **Price** — live trade price with 24h change
- **24h Volume** — total notional traded in the last 24 hours
- **Open Interest** — total value of all open positions (long + short)
- **Funding Rate** — current rate with direction indicator
- **24h Liquidations** — total notional liquidated in the last 24 hours
- **Price chart** — recent trade history with liquidations marked
- **Long vs Short** — open position breakdown by direction
- **Volume by hour** — 24h trading activity over time
- **Funding rates across all markets** — ranked bar chart showing market-wide sentiment

### Arbitrage Scanner
Identifies cash and carry arbitrage opportunities across all 60 active perpetual markets.

**The strategy:** When funding is positive, go long spot and short the perpetual. You collect funding payments from longs while remaining price-neutral. Your spot gains and perp losses cancel out, leaving the funding yield as pure return.

The scanner shows:
- **Annualized yield** — projected annual return from funding payments at the current rate
- **Signal strength** — STRONG (>20%), MODERATE (5–20%), WEAK (>0%), AVOID (negative)
- **Next funding countdown** — time until the next payment
- **Yield filter** — slider to focus on opportunities above a minimum threshold

Data refreshes automatically every 5 seconds.

## Data Source

All data is pulled live from Injective's public exchange API:
```
https://sentry.exchange.grpc-web.injective.network/api/exchange/derivative/v1
```

No authentication required. Prices are quoted in USDT.

## Notes

- Annualized yield assumes the current funding rate stays constant. In practice rates change every hour
- The scanner is a signal tool, not financial advice
- Open interest figures are based on a sample of up to 100 positions per market due to API limits
