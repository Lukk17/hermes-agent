# Market Summary Guide

Use this guide when generating market_summary.md. It contains indicator interpretations and market context.

---

## Indicator Reference

### Fear & Greed Index (0-100)
| Value | Classification | Market Meaning |
|-------|----------------|----------------|
| 0-25 | Extreme Fear (red) | Market in depression. Historically good accumulation zone. Contrarian buy signal. |
| 25-50 | Fear (orange) | Uncertainty but not panic. |
| 50-75 | Greed (light green) | Optimism building. |
| 75-100 | Extreme Greed (green) | Market overheating. Risk of correction. |

### Cycle Score (0-100)
| Value | Phase | Market Meaning |
|-------|-------|----------------|
| 0-25 | Deep Accumulation | Bottom fishing territory. Historically best time to buy. |
| 25-50 | Accumulation | Early to mid accumulation. DCA zone. |
| 50-75 | Distribution | Smart money selling. Caution. |
| 75-100 | Euphoria | Top territory. Not recommended to buy. |

### BTC RSI (14-day)
| Value | Signal | Market Meaning |
|-------|--------|----------------|
| <30 | Oversold | Potential bounce. Contrarian buy signal. |
| 30-50 | Bearish | More selling than buying. |
| 50-70 | Bullish | Buying pressure increasing. |
| >70 | Overbought | Potential correction. |

### MA Cross (50d/200d)
| Signal | Classification | Market Meaning |
|--------|---------------|----------------|
| Death Cross | Bearish | 50d MA crosses below 200d MA. Confirms downtrend. Bearish for medium/long-term. |
| Golden Cross | Bullish | 50d MA crosses above 200d MA. Confirms uptrend. Bullish for medium/long-term. |

**MA Spread**: Distance between 50d and 200d MA as percentage. More negative = stronger bearish divergence.

### Price vs MA200
| Ratio | Market Meaning |
|-------|----------------|
| <0.8 | Significantly undervalued. Deep below long-term average. |
| 0.8-1.0 | Below average. Bearish but potentially oversold. |
| 1.0-1.2 | Above average. Bullish. |
| >1.2 | Significantly overvalued. |

**Deviation**: How far price is above/below MA200 as percentage. More negative = more oversold.

### Pi Cycle Top
| Signal | Market Meaning |
|--------|----------------|
| Safe | BTC price well below cycle top. No immediate cycle top risk. Good time to hold. |
| Danger | BTC approaching cycle top. Historically cycle top zone. Consider taking profits. |

**Distance %**: How far BTC is from the Pi Cycle top line. Higher % = safer.

### BTC Dominance (%)
| Value | Market Meaning |
|-------|----------------|
| >50% | BTC market share high. "BTC Season" - capital flows to BTC, alts struggle. |
| 40-50% | Neutral. Balanced market. |
| <40% | "Alt Season" - capital rotating to alts. Good for altcoins. |

### Hash Rate 7d Change
| Value | Market Meaning |
|-------|----------------|
| Positive | Miners expanding. Bullish signal for network health. Long-term positive. |
| Negative | Miners contracting. Could signal miner capitulation during selloffs. |

### MCap vs ATH
| Value | Market Meaning |
|-------|----------------|
| <50% ATH | Deep bear market. Maximum fear. Best accumulation. |
| 50-70% ATH | Bear market to cycle bottom. Good risk/reward. |
| 70-85% ATH | Mid-cycle. Unknown if continuation or reversal. |
| 85-100% ATH | Near ATH. Bull market. Higher risk. |
| >100% ATH | New ATH. Euphoria. Not recommended to buy. |

---

## Summary Generation Rules

### Structure
1. **Sentiment Opening** - Start with Fear & Greed classification and what it means
2. **Cycle Position** - Interpret Cycle Score and phase
3. **Trend Analysis** - MA Cross, MA Spread, Price/MA200
4. **Momentum** - RSI interpretation
5. **Network Health** - Hash Rate direction
6. **Cycle Top Risk** - Pi Cycle status
7. **Final Verdict** - Combine signals into actionable insight

### Tone
- Be direct and factual
- Use trader terminology (bullish/bearish/oversold/overbought)
- Include specific values when relevant
- End with actionable insight (accumulate, DCA, take profits, caution)

### Examples

**Bearish Market Summary:**
> Market sentiment shows **Extreme Fear (8)** - the market is in depression, which historically signals accumulation zones. The **Cycle Score of 26/100** confirms we're in the early accumulation phase. The **Death Cross** and **MA Spread of -24%** confirm bearish trend, but the **RSI at 17** shows extreme oversold conditions. **Pi Cycle is Safe** at 60% from top. **Hash Rate growing +1.1%** signals network strength.
>
> **Verdict: Strong accumulation zone.** Multiple indicators align for a potential bottom. Consider DCA into BTC/ETH.

**Bullish Market Summary:**
> Market sentiment shows **Greed (68)** - optimism is building but not yet extreme. The **Cycle Score of 72/100** indicates we're in the distribution phase where smart money is selling. The **Golden Cross** confirms medium-term bullish trend, but **RSI at 74** shows overbought conditions.
>
> **Verdict: Late cycle - hold core positions, avoid heavy alt purchases.** Consider taking some profits.

---

## Key Principles

1. **Combine indicators** - Don't interpret single indicator in isolation
2. **RSI + Extreme Fear + Low Cycle Score** = Strong accumulation signal
3. **RSI > 70 + Extreme Greed + High Cycle Score** = Distribution/top signal
4. **Always connect to actionable insight** - What should the reader DO with this information?
