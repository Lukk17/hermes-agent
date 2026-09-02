# Crypto Monitor - User Requirements

Last updated: 2026-02-25

## Report Format Requirements

### General Rules
- Use metric units for charts
- Always verify changes follow these requirements before running anything
- ALWAYS answer ALL questions - never ignore any

### Tables

Tables are currently sent as TEXT, not as PNGs. Table image rendering was
removed in a refactor (see the note at the end of `build_charts()` in
`reports/report_builder.py`), so no `table_*.png` file is produced. The rules
below are the requirements for table images and apply only if that rendering
is restored.

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

NOT every section has a header. Five are headerless BY DESIGN, because they have
no header to carry an emoji: they render a bare table or a bare list. Do not
"fix" them by adding one.

Headerless by design:

- Prices (a box table)
- Top Movers (a box table)
- Market Indicators (a box table)
- Market Breadth
- Crypto Sectors (a box table)

Sections that DO carry a header, exactly as the renderer emits it:

- `## 📰 Trending News` (model-written, replaces the data-rendered news section)
- `## ⛽ ETH Gas`
- `## 📈 Spot ETF Flows`
- `## 💵 Stablecoin Supply`
- `## 💰 Funding Rates`
- `## 🏦 Exchange Holdings`
- `## 🐋 Known Whales` and `## 🐋 Whale Moves` (the whales section emits both)
- `## 🪂 Airdrops`
- `## 📋 Market Summary` (model-written, replaces the data-rendered summary section)
- `## 🔗 Quick Links` (header, then four bare URLs, each wrapped in angle brackets)

The headers live in the section renderers under `reports/sections/`, except the
two model-written ones, which `reports/report_builder.py` supplies from
`MODEL_WRITTEN_SECTIONS`. Nothing downstream adds a header, so a section without
one in its renderer is delivered without one.

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

### Report Order

Title first, then EVERY chart, then the text sections. The charts lead so the
graphs are visible without scrolling. This is the delivered order and it is
fixed: a missing chart or section drops out without shifting anything that
survives.

**1. Title**

1. `# 📊 Daily Crypto Report` plus the timestamp

**2. Charts, all eight, in this order**

2. gauge_fng.png
3. gauge_cycle.png
4. gauge_sentiment.png
5. trending_narratives.png
6. coin_sentiment.png
7. btc_dominance_2y.png
8. btc_price_2y.png
9. gas_history_1y.png

**3. Text sections, in this order**

10. Prices
11. Top Movers
12. `## 📰 Trending News` (model-written)
13. Market Indicators
14. Market Breadth
15. Crypto Sectors
16. `## ⛽ ETH Gas`
17. `## 📈 Spot ETF Flows`
18. `## 💵 Stablecoin Supply`
19. `## 💰 Funding Rates`
20. `## 🏦 Exchange Holdings`
21. Whale Activity
22. `## 🪂 Airdrops`
23. `## 📋 Market Summary` (model-written)
24. `## 🔗 Quick Links`

That is 24 messages at most, and a typical run delivers about 22 because a
couple of sections have no data on any given day. Which two vary, so the count
is NOT the contract. The ORDER is: title, then every chart that exists, then
every text section that has content, each in the sequence above.

Chart files and where they are written. Three are NOT under `data/reports/`:

- `data/reports/gauge_fng.png`
- `data/reports/gauge_cycle.png`
- `data/reports/gauge_sentiment.png`
- `data/reports/trending_narratives.png`
- `data/reports/coin_sentiment.png`
- `data/dominance/charts/btc_dominance_2y.png`
- `data/btc_price/btc_price_2y.png`
- `data/gas/charts/gas_history_1y.png`

`btc_price_2y.png` and `gas_history_1y.png` are generated every run and are
delivered, not optional extras. ETH Gas has BOTH a chart in the leading block
and a text section later.

### Trending Narratives is the chart, Trending News is the list

Two different things that used to share one name:

- **Trending Narratives** is the horizontal bar chart of category counts, `trending_narratives.png`, titled "Trending Narratives" inside the image.
- **Trending News** is the model-written numbered list of the ten most important headlines, delivered as a text section under `## 📰 Trending News`.

The model-written sections REPLACE their data-rendered counterparts rather than
sitting beside them: `news_summary.md` replaces the `news` section and
`market_summary.md` replaces the `summary` section. A curated list next to a raw
top-ten list is duplication.

Both files hold body text only, with no heading. `reports/report_builder.py`
supplies the header.
