import time
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

BASE             = "https://sentry.exchange.grpc-web.injective.network/api/exchange/derivative/v1"
USDT_DEC         = 1e6
FUNDING_PER_YEAR = 24 * 365

st.set_page_config(
    page_title="Injective Derivatives",
    page_icon="assets/favicon.ico",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }

[data-testid="stAppViewContainer"] { background: #08090e; }
[data-testid="stSidebar"]          { background: #0d1017; border-right: 1px solid #1c2030; }
[data-testid="stSidebar"] *        { color: #a0aabb !important; }

/* Hide default streamlit chrome */
#MainMenu, footer, { visibility: hidden; }
header { background: #08090e !important; }
[data-testid="stDecoration"] { display: none; }

/* Tabs */
[data-testid="stTabs"] button {
    font-size: 13px;
    font-weight: 500;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: #4a5568 !important;
    padding: 10px 20px;
    border-bottom: 2px solid transparent;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #e2e8f0 !important;
    border-bottom: 2px solid #00b2ff;
}

/* Metric cards */
[data-testid="metric-container"] {
    background: #0d1117;
    border: 1px solid #1c2030;
    border-radius: 6px;
    padding: 16px 20px;
}
[data-testid="stMetricLabel"]  { font-size: 11px !important; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: #4a5568 !important; }
[data-testid="stMetricValue"]  { font-size: 22px !important; font-weight: 600; color: #e2e8f0 !important; letter-spacing: -0.02em; }
[data-testid="stMetricDelta"]  { font-size: 12px !important; }

/* Sidebar controls */
[data-testid="stSelectbox"] > div { background: #0d1117 !important; border: 1px solid #1c2030 !important; border-radius: 6px; }
[data-testid="stButton"] > button {
    background: transparent;
    border: 1px solid #1c2030;
    color: #a0aabb !important;
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.04em;
    border-radius: 6px;
    width: 100%;
}
[data-testid="stButton"] > button:hover { border-color: #00b2ff; color: #00b2ff !important; }

/* Slider */
[data-testid="stSlider"] { padding-top: 8px; }

/* Divider */
hr { border-color: #1c2030 !important; margin: 20px 0 !important; }

/* Dataframe */
[data-testid="stDataFrame"] { border: 1px solid #1c2030; border-radius: 6px; }
iframe { background: #0d1117 !important; }

/* Headings */
h1 { font-size: 20px !important; font-weight: 600 !important; color: #e2e8f0 !important; letter-spacing: -0.02em !important; }
h2 { font-size: 16px !important; font-weight: 600 !important; color: #e2e8f0 !important; }
h3 { font-size: 15px !important; font-weight: 600 !important; color: #e2e8f0 !important; }
h4 { font-size: 13px !important; font-weight: 600 !important; color: #8899aa !important; letter-spacing: 0.06em !important; text-transform: uppercase !important; }
p, div, span, label { color: #a0aabb; }

/* Caption */
[data-testid="stCaptionContainer"] p { font-size: 11px !important; color: #4a5568 !important; line-height: 1.6; }

/* Info/warning boxes */
[data-testid="stAlert"] { background: #0d1117; border: 1px solid #1c2030; border-radius: 6px; }

.signal-strong   { color: #3fb950; font-weight: 600; font-size: 12px; letter-spacing: 0.04em; }
.signal-moderate { color: #d29922; font-weight: 600; font-size: 12px; letter-spacing: 0.04em; }
.signal-weak     { color: #4a5568; font-weight: 600; font-size: 12px; letter-spacing: 0.04em; }
.signal-avoid    { color: #f85149; font-weight: 600; font-size: 12px; letter-spacing: 0.04em; }

.page-header { border-bottom: 1px solid #1c2030; padding-bottom: 16px; margin-bottom: 24px; }
.page-title  { font-size: 20px; font-weight: 600; color: #e2e8f0; letter-spacing: -0.02em; margin: 0; }
.page-sub    { font-size: 12px; color: #4a5568; margin: 4px 0 0 0; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
[data-testid="stSpinner"] { display: none; }
div[data-stale="true"] { opacity: 1 !important; }
</style>
""", unsafe_allow_html=True)


# ── Data fetching ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=30, show_spinner=False)
def get_markets() -> list[dict]:
    r = requests.get(f"{BASE}/markets", params={"marketStatus": "active"}, timeout=15)
    r.raise_for_status()
    return [m for m in r.json().get("markets", []) if "perpetualMarketFunding" in m]


@st.cache_data(ttl=5, show_spinner=False)
def get_trades(market_id: str, limit: int = 500) -> list[dict]:
    r = requests.get(
        f"{BASE}/trades",
        params={"marketId": market_id, "executionSide": "taker", "limit": limit},
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("trades", [])


@st.cache_data(ttl=5, show_spinner=False)
def get_positions(market_id: str, limit: int = 100) -> list[dict]:
    r = requests.get(
        f"{BASE}/positions",
        params={"marketId": market_id, "limit": limit},
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("positions", [])


# ── Parsing helpers ────────────────────────────────────────────────────────────

def to_usdt(raw) -> float:
    return float(raw) / USDT_DEC if raw else 0.0


def trades_to_df(raw: list) -> pd.DataFrame:
    if not raw:
        return pd.DataFrame()
    rows = []
    for t in raw:
        delta = t.get("positionDelta", {})
        price = to_usdt(delta.get("executionPrice", 0))
        qty   = float(delta.get("executionQuantity", 0))
        rows.append({
            "time":           pd.Timestamp(int(t["executedAt"]), unit="ms", tz="UTC"),
            "price":          price,
            "quantity":       qty,
            "notional":       price * qty,
            "direction":      delta.get("tradeDirection", ""),
            "is_liquidation": bool(t.get("isLiquidation", False)),
        })
    return pd.DataFrame(rows).sort_values("time").reset_index(drop=True)


def positions_to_df(raw: list) -> pd.DataFrame:
    if not raw:
        return pd.DataFrame()
    rows = [{
        "direction":         p.get("direction", ""),
        "quantity":          float(p.get("quantity", 0)),
        "mark_price":        to_usdt(p.get("markPrice", 0)),
        "notional":          float(p.get("quantity", 0)) * to_usdt(p.get("markPrice", 0)),
        "entry_price":       to_usdt(p.get("entryPrice", 0)),
        "liquidation_price": to_usdt(p.get("liquidationPrice", 0)),
    } for p in raw]
    return pd.DataFrame(rows)


def build_scanner_df(markets: list[dict]) -> pd.DataFrame:
    now = time.time()
    rows = []
    for m in markets:
        funding   = m.get("perpetualMarketFunding", {})
        perp_info = m.get("perpetualMarketInfo", {})
        rate      = float(funding.get("lastFundingRate", 0))
        ann       = rate * FUNDING_PER_YEAR * 100

        next_ts   = int(perp_info.get("nextFundingTimestamp", 0))
        secs_left = max(0, next_ts - now)
        m2, s2    = divmod(int(secs_left), 60)
        h2, m2    = divmod(m2, 60)
        countdown = f"{h2}h {m2:02d}m" if h2 else f"{m2}m {s2:02d}s"

        if ann > 20:
            signal = "STRONG"
        elif ann > 5:
            signal = "MODERATE"
        elif ann > 0:
            signal = "WEAK"
        else:
            signal = "AVOID"

        rows.append({
            "Market":           m["ticker"],
            "Funding Rate":     rate * 100,
            "Annualized Yield": ann,
            "Next Funding":     countdown,
            "Signal":           signal,
        })

    return pd.DataFrame(rows).sort_values("Annualized Yield", ascending=False).reset_index(drop=True)


# ── Chart theme ────────────────────────────────────────────────────────────────

DARK     = dict(
    template="plotly_dark",
    paper_bgcolor="#0d1117",
    plot_bgcolor="#08090e",
    margin=dict(l=0, r=0, t=30, b=0),
    height=320,
    font=dict(family="Inter, sans-serif", color="#a0aabb", size=11),
)
BLUE  = "#00b2ff"
RED   = "#f85149"
GREEN = "#3fb950"
GOLD  = "#d29922"
GREY  = "#4a5568"


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    st.markdown("""
    <div class="page-header">
        <p class="page-title">Injective Derivatives</p>
        <p class="page-sub">Perpetual futures · Live on-chain data</p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner(""):
        try:
            markets = get_markets()
        except Exception as e:
            st.error(f"Failed to load markets: {e}")
            return

    if not markets:
        st.error("No active derivative markets found.")
        return

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("<p style='font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#4a5568;margin-bottom:8px'>Market</p>", unsafe_allow_html=True)
        tickers = [m["ticker"] for m in markets]
        sel_idx = st.selectbox("", range(len(tickers)), format_func=lambda i: tickers[i], label_visibility="collapsed")
        market  = markets[sel_idx]

        st.divider()
        if st.button("Refresh"):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        st.markdown(f"<p style='font-size:11px;color:#4a5568'>{len(markets)} active perpetual markets</p>", unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_analytics, tab_scanner = st.tabs(["Market Analytics", "Arbitrage Scanner"])


    # ════════════════════════════════════════════════════════════════════════════
    # TAB 1 — Market Analytics
    # ════════════════════════════════════════════════════════════════════════════
    with tab_analytics:

        @st.fragment(run_every=2)
        def live_analytics(market, markets):
            mid    = market["marketId"]
            ticker = market["ticker"]

            try:
                df_trades = trades_to_df(get_trades(mid))
                df_pos    = positions_to_df(get_positions(mid))
            except Exception as e:
                st.error(f"Data fetch failed: {e}")
                return

            now    = pd.Timestamp.now(tz="UTC")
            cutoff = now - pd.Timedelta(hours=24)
            df_24h = df_trades[df_trades["time"] >= cutoff] if not df_trades.empty else pd.DataFrame()

            funding_pct   = float(market.get("perpetualMarketFunding", {}).get("lastFundingRate", 0)) * 100
            current_price = df_trades["price"].iloc[-1]  if not df_trades.empty else 0.0
            open_24h      = df_24h["price"].iloc[0]       if not df_24h.empty  else current_price
            price_chg     = ((current_price - open_24h) / open_24h * 100) if open_24h else 0.0
            volume_24h    = df_24h["notional"].sum()       if not df_24h.empty  else 0.0
            liq_vol       = df_24h[df_24h["is_liquidation"]]["notional"].sum() if not df_24h.empty else 0.0
            long_oi       = df_pos[df_pos["direction"] == "long"]["notional"].sum()  if not df_pos.empty else 0.0
            short_oi      = df_pos[df_pos["direction"] == "short"]["notional"].sum() if not df_pos.empty else 0.0
            total_oi      = long_oi + short_oi

            st.markdown(f"<h2 style='margin-bottom:16px'>{ticker}</h2>", unsafe_allow_html=True)

            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("Price",            f"${current_price:,.4f}", f"{price_chg:+.2f}%")
            k2.metric("24h Volume",       f"${volume_24h:,.0f}")
            k3.metric("Open Interest",    f"${total_oi:,.0f}")
            k4.metric("Funding Rate",     f"{funding_pct:.4f}%")
            k5.metric("24h Liquidations", f"${liq_vol:,.0f}")

            st.divider()

            col1, col2 = st.columns([3, 2])

            with col1:
                st.markdown("#### Price — Recent Trades")
                if not df_trades.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df_trades["time"], y=df_trades["price"],
                        mode="lines", line=dict(color=BLUE, width=1.5),
                        name="Price",
                        hovertemplate="%{x|%H:%M:%S}<br>$%{y:.4f}<extra></extra>",
                    ))
                    liq = df_trades[df_trades["is_liquidation"]]
                    if not liq.empty:
                        fig.add_trace(go.Scatter(
                            x=liq["time"], y=liq["price"], mode="markers",
                            marker=dict(color=GOLD, size=8, symbol="x", line=dict(width=2)),
                            name="Liquidation",
                            hovertemplate="%{x|%H:%M:%S}<br>$%{y:.4f}<extra>Liquidation</extra>",
                        ))
                    fig.update_layout(**DARK, legend=dict(bgcolor="#0d1117", font=dict(color="#a0aabb")))
                    fig.update_yaxes(tickprefix="$", gridcolor="#1c2030", zerolinecolor="#1c2030")
                    fig.update_xaxes(gridcolor="#1c2030")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No trade data available.")

            with col2:
                st.markdown("#### Long vs Short")
                if not df_pos.empty and total_oi > 0:
                    fig2 = px.pie(
                        pd.DataFrame({"side": ["Long", "Short"], "notional": [long_oi, short_oi]}),
                        values="notional", names="side", hole=0.6,
                        color="side", color_discrete_map={"Long": BLUE, "Short": RED},
                    )
                    fig2.update_traces(
                        textinfo="percent+label",
                        textfont=dict(size=12, color="#e2e8f0"),
                        hovertemplate="%{label}<br>$%{value:,.0f}<extra></extra>",
                    )
                    fig2.update_layout(**DARK, showlegend=False)
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info("No open position data.")

            col3, col4 = st.columns(2)

            with col3:
                st.markdown("#### 24h Volume by Hour")
                if not df_24h.empty:
                    hourly = df_24h.copy()
                    hourly["hour"] = hourly["time"].dt.floor("h")
                    hourly = hourly.groupby("hour")["notional"].sum().reset_index()
                    fig3 = px.bar(hourly, x="hour", y="notional",
                                  labels={"notional": "Volume (USDT)", "hour": ""},
                                  color_discrete_sequence=[BLUE])
                    fig3.update_traces(hovertemplate="%{x|%H:%M UTC}<br>$%{y:,.0f}<extra></extra>")
                    fig3.update_layout(**DARK)
                    fig3.update_yaxes(tickprefix="$", gridcolor="#1c2030", zerolinecolor="#1c2030")
                    fig3.update_xaxes(gridcolor="#1c2030")
                    st.plotly_chart(fig3, use_container_width=True)
                else:
                    st.info("No recent trade data.")

            with col4:
                st.markdown("#### 24h Liquidations")
                liq_df = df_24h[df_24h["is_liquidation"]] if not df_24h.empty else pd.DataFrame()
                if not liq_df.empty:
                    fig4 = px.scatter(
                        liq_df, x="time", y="notional",
                        color="direction",
                        color_discrete_map={"buy": BLUE, "sell": RED},
                        size="notional", size_max=35,
                        labels={"notional": "Size (USDT)", "time": ""},
                    )
                    fig4.update_traces(hovertemplate="%{x|%H:%M UTC}<br>$%{y:,.2f}<extra>%{fullData.name}</extra>")
                    fig4.update_layout(**DARK, legend=dict(bgcolor="#0d1117", font=dict(color="#a0aabb")))
                    fig4.update_yaxes(tickprefix="$", gridcolor="#1c2030", zerolinecolor="#1c2030")
                    fig4.update_xaxes(gridcolor="#1c2030")
                    st.plotly_chart(fig4, use_container_width=True)
                else:
                    st.info("No liquidations in the last 24h.")

            st.divider()
            st.markdown("#### Funding Rates Across All Markets")
            st.caption("Positive = longs pay shorts (bullish excess). Negative = shorts pay longs (bearish excess).")

            df_fr = pd.DataFrame([{
                "ticker": m["ticker"],
                "rate":   float(m.get("perpetualMarketFunding", {}).get("lastFundingRate", 0)) * 100,
            } for m in markets]).sort_values("rate", ascending=False)

            fig5 = px.bar(df_fr, x="ticker", y="rate", color="rate",
                          color_continuous_scale=[[0, RED], [0.5, "#1c2030"], [1, BLUE]],
                          color_continuous_midpoint=0,
                          labels={"rate": "Funding Rate (%)", "ticker": ""})
            fig5.update_traces(hovertemplate="%{x}<br>%{y:.5f}%<extra></extra>")
            fig5.update_layout(**{**DARK, "height": 380},
                               xaxis_tickangle=-40, coloraxis_showscale=False)
            fig5.update_yaxes(ticksuffix="%", gridcolor="#1c2030", zerolinecolor="#1c2030")
            fig5.update_xaxes(gridcolor="#1c2030")
            st.plotly_chart(fig5, use_container_width=True)

            if not df_pos.empty:
                with st.expander(f"Open Positions  ·  {len(df_pos)} loaded"):
                    display = df_pos.copy()
                    for col in ["mark_price", "entry_price", "liquidation_price", "notional"]:
                        display[col] = display[col].apply(lambda v: f"${v:,.4f}")
                    st.dataframe(display, use_container_width=True)

        live_analytics(market, markets)


    # ════════════════════════════════════════════════════════════════════════════
    # TAB 2 — Arbitrage Scanner
    # ════════════════════════════════════════════════════════════════════════════
    with tab_scanner:
        st.markdown("<h2 style='margin-bottom:4px'>Cash & Carry Scanner</h2>", unsafe_allow_html=True)
        st.caption(
            "Go long spot and short the perpetual on markets with positive funding. "
            "You collect funding payments while remaining price-neutral. "
            "Exit when funding turns negative or yield no longer justifies the risk."
        )
        st.divider()

        col_ctrl, _ = st.columns([1, 3])
        with col_ctrl:
            min_yield = st.slider("Min annualized yield (%)", 0, 50, 0, step=5)

        @st.fragment(run_every=2)
        def live_scanner(markets, min_yield):
            df_scan        = build_scanner_df(markets)
            df_pos_funding = df_scan[df_scan["Annualized Yield"] > 0]

            n_strong   = (df_scan["Signal"] == "STRONG").sum()
            n_moderate = (df_scan["Signal"] == "MODERATE").sum()
            avg_yield  = df_pos_funding["Annualized Yield"].mean() if not df_pos_funding.empty else 0
            best_mkt   = df_scan.iloc[0]["Market"]           if not df_scan.empty else "—"
            best_yield = df_scan.iloc[0]["Annualized Yield"] if not df_scan.empty else 0

            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Strong Signals",       f"{n_strong}",       help="Annualized yield > 20%")
            s2.metric("Moderate Signals",     f"{n_moderate}",     help="Annualized yield 5–20%")
            s3.metric("Avg Yield (positive)", f"{avg_yield:.1f}%")
            s4.metric("Best Market",          best_mkt, f"{best_yield:.1f}% annualized")

            st.divider()

            df_filtered    = df_scan[df_scan["Annualized Yield"] >= min_yield].copy()
            signal_colors  = {"STRONG": GREEN, "MODERATE": GOLD, "WEAK": GREY, "AVOID": RED}

            fig_scan = go.Figure()
            for signal, color in signal_colors.items():
                subset = df_filtered[df_filtered["Signal"] == signal]
                if subset.empty:
                    continue
                fig_scan.add_trace(go.Bar(
                    x=subset["Market"],
                    y=subset["Annualized Yield"],
                    name=signal,
                    marker_color=color,
                    hovertemplate="%{x}<br>%{y:.2f}% annualized<extra>" + signal + "</extra>",
                ))

            fig_scan.add_hline(y=20, line_dash="dot", line_color=GREEN, line_width=1,
                               annotation_text="20%", annotation_font_color=GREEN,
                               annotation_font_size=10)
            fig_scan.add_hline(y=5, line_dash="dot", line_color=GOLD, line_width=1,
                               annotation_text="5%", annotation_font_color=GOLD,
                               annotation_font_size=10)
            fig_scan.update_layout(
                **{**DARK, "height": 360},
                xaxis_tickangle=-40,
                yaxis_title="Annualized Yield (%)",
                yaxis_ticksuffix="%",
                barmode="overlay",
                legend=dict(bgcolor="#0d1117", font=dict(color="#a0aabb")),
            )
            fig_scan.update_yaxes(gridcolor="#1c2030", zerolinecolor="#1c2030")
            fig_scan.update_xaxes(gridcolor="#1c2030")
            st.plotly_chart(fig_scan, use_container_width=True)

            st.markdown("#### All Markets — Ranked by Yield")
            display = df_filtered[["Signal", "Market", "Annualized Yield", "Funding Rate", "Next Funding"]].copy()
            display["Annualized Yield"] = display["Annualized Yield"].apply(lambda v: f"{v:.2f}%")
            display["Funding Rate"]     = display["Funding Rate"].apply(lambda v: f"{v:.5f}%")
            st.dataframe(display, use_container_width=True, hide_index=True)

        live_scanner(markets, min_yield)

        st.divider()
        st.caption(
            "Annualized yield assumes the current funding rate persists — in practice it changes every hour. "
            "Primary risks: funding rate reversal, liquidation on the short leg during sharp price moves, "
            "and smart contract exposure on Injective. This is a signal scanner, not financial advice."
        )



if __name__ == "__main__":
    main()
