# Crypto Monitor - User Requirements

Last updated: 2026-02-25

## Report Format Requirements

### General Rules
- Use metric units for charts
- Always verify changes follow these requirements before running anything
- ALWAYS answer ALL questions - never ignore any

### Tables (PNG)
- Headers visible (column names like "Coin", "Price", "24h", etc.)
- NO text inside PNG that belongs in Discord message
- Title emoji in Discord message, NOT inside table
- Colored cells for positive (green) / negative (red) values
- Prices/Movers/Sectors: use colored cells
- Headers: Use full names (not abbreviated like "Chg", "Prob", "Dir")
- Column widths proportional to content, no cutting of words
- Image size proportional to content - no black empty space around table

### Empty Lines (MANDATORY)
- Use braille blank `⠀` (U+2800) for ONE empty line BEFORE EVERY section header
- After every chart/table AND before every text section header
- NOT multiple empty lines

### Links
- Plain links WITHOUT < > wrappers (so they are clickable)
- Links NOT showing Discord preview cards - user will disable in Discord settings

### Section Headers (in Discord message, NOT in PNG)
All sections MUST have emoji header in Discord message:
1. Prices: "## 💰 Prices"
2. Top Movers: "## 📈 Top Movers"
3. Trending Narratives: "## 📰 Trending Narratives"
4. Coin Sentiment: "## 💭 Coin Sentiment"
5. Market Indicators: "## 📉 Market Indicators"
6. BTC Dominance: "## 📊 BTC Dominance"
7. Crypto Sectors: "## 🏭 Crypto Sectors"
8. ETH Gas: "## ⛽ ETH Gas"
9. Market Breadth: "## 📊 Market Breadth"
10. Spot ETF Flows: "## 📈 Spot ETF Flows"
11. Stablecoin Supply: "## 💵 Stablecoin Supply"
12. Funding Rates: "## 💰 Funding Rates"
13. Exchange Holdings: "## 🏦 Exchange Holdings"
14. Whale Activity: "## 🐋 Whale Activity"
15. Airdrops: "## 🪂 Airdrops"
16. Market Summary: "## 📋 Market Summary"
17. Quick Links: "## 🔗 Quick Links"

### Chart/Gauge Settings (EXACT VALUES)

#### Gauges (Fear & Greed, Cycle Score, Sentiment)
- File: reports/charts.py, function: render_gauge
- Resolution: 3840 x 1920 (2:1 ratio)
- Internal: 2x resolution, downscaled with LANCZOS
- Output: 3840x1920 PNG

#### Trending Narratives
- File: reports/charts.py, function: render_trending_narratives
- figsize: (18, max(6, len(sorted_cats) * 1.5))
- bar height: 0.9
- title fontsize: 48
- label fontsize: 36
- value fontsize: 32

#### Coin Sentiment
- File: reports/charts.py, function: render_coin_sentiment
- figsize: (12, fig_height)
- bar height: 0.5
- x-axis padding: max_abs * 0.15 (15%)
- label fontsize: 20
- value fontsize: 24

#### BTC Dominance Chart
- Uses matplotlib default sizing (no custom)

### Report Order (23 messages)
1. # 📊 Daily Crypto Report (title)
2. timestamp
3. gauge_fng.png + braille
4. gauge_cycle.png + braille
5. gauge_sentiment.png + braille
6. table_prices.png + braille + ## 💰 Prices
7. table_movers.png + braille + ## 📈 Top Movers
8. trending_narratives.png + braille + ## 📰 Trending Narratives
9. coin_sentiment.png + braille + ## 💭 Coin Sentiment
10. table_indicators.png + braille + ## 📉 Market Indicators
11. btc_dominance.png + braille + ## 📊 BTC Dominance
12. table_sectors.png + braille + ## 🏭 Crypto Sectors
13. braille + ## ⛽ ETH Gas + text
14. braille + ## 📊 Market Breadth + text
15. braille + ## 📈 Spot ETF Flows + text
16. braille + ## 💵 Stablecoin Supply + text
17. braille + ## 💰 Funding Rates + text
18. table_flows.png + ## 🏦 Exchange Holdings
19. table_whales.png + braille + ## 🐋 Whale Activity
20. table_airdrops.png + braille + ## 🪂 Airdrops
21. Airdrop links
22. braille + ## 📋 Market Summary + content
23. braille + ## 🔗 Quick Links + links
