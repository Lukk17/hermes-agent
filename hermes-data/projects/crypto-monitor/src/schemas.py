"""
src/schemas.py - ONE source of truth for all data file formats.

Defines the expected structure for all data files used across collectors,
analyzers, and reports. If schema changes, update here first.
"""

from typing import TypedDict


# =============================================================================
# Coin Prices
# =============================================================================

class CoinEntry(TypedDict):
    """Single coin data entry."""
    id: str
    symbol: str
    name: str
    price: float
    change_24h: float
    market_cap: int
    volume: int


class CoinPricesData(TypedDict):
    """Schema for coin_prices_latest.json and coin_prices_history.json."""
    coins: list[CoinEntry]
    status: str  # "ok" | "error"
    error: str | None
    timestamp: str  # ISO format


# =============================================================================
# Whales
# =============================================================================

class BTCWhaleEntry(TypedDict):
    """Single BTC whale entry."""
    label: str
    address: str
    chain: str  # always "bitcoin"
    balance_btc: float
    balance_usd: float
    checked_at: str  # ISO format


class ETHWhaleEntry(TypedDict):
    """Single ETH whale entry."""
    label: str
    address: str
    chain: str  # always "ethereum"
    balance_eth: float
    balance_usd: float
    category: str
    checked_at: str  # ISO format


class WhalesData(TypedDict):
    """Schema for whales_latest.json and whales_history.json."""
    bitcoin: list[BTCWhaleEntry]
    ethereum: list[ETHWhaleEntry]
    timestamp: str  # ISO format


# =============================================================================
# Stablecoins
# =============================================================================

class StablecoinEntry(TypedDict):
    """Single stablecoin data entry."""
    symbol: str
    name: str
    market_cap: int
    change_7d_pct: float


class StablecoinsData(TypedDict):
    """Schema for stablecoins_latest.json."""
    coins: list[StablecoinEntry]
    total_mcap: int
    total_7d_change: float
    direction: str  # "expanding" | "contracting" | "stable"
    error: str | None
    timestamp: str


# =============================================================================
# Sectors
# =============================================================================

class SectorEntry(TypedDict):
    """Single sector data entry."""
    name: str
    full_name: str
    change_24h: float
    market_cap: int
    category: str


class SectorsData(TypedDict):
    """Schema for sectors_latest.json."""
    sectors: list[SectorEntry]
    error: str | None
    timestamp: str


# =============================================================================
# Market Breadth
# =============================================================================

class MarketBreadthData(TypedDict):
    """Schema for market_breadth_latest.json."""
    btc_dominance: float
    eth_dominance: float
    eth_btc_ratio: float
    health: str
    active_cryptocurrencies: int
    error: str | None
    timestamp: str


# =============================================================================
# ETF Flows
# =============================================================================

class ETFDay(TypedDict):
    """Single day of ETF flow data."""
    date: str
    total: float


class ETFData(TypedDict):
    """Schema for etf_flows_latest.json."""
    btc: dict
    eth: dict
    error: str | None
    timestamp: str


# =============================================================================
# Gas
# =============================================================================

class GasData(TypedDict):
    """Schema for gas_latest.json."""
    current: dict
    history: list
    error: str | None
    timestamp: str


# =============================================================================
# Fear & Greed
# =============================================================================

class FearGreedData(TypedDict):
    """Schema for fear_greed_latest.json."""
    fear_greed: dict
    timestamp: str


# =============================================================================
# Cycle
# =============================================================================

class CycleData(TypedDict):
    """Schema for cycle_latest.json."""
    cycle_score: float
    phase: str
    indicators: dict
    error: str | None
    timestamp: str


# =============================================================================
# Sentiment
# =============================================================================

class SentimentData(TypedDict):
    """Schema for sentiment_latest.json."""
    sentiment: float
    signal: str
    sources: dict
    error: str | None
    timestamp: str


# =============================================================================
# Trends
# =============================================================================

class TrendsData(TypedDict):
    """Schema for trends_latest.json."""
    trends: list
    error: str | None
    timestamp: str


# =============================================================================
# Whale Signals (analyzer output)
# =============================================================================

class WhaleSignalsData(TypedDict):
    """Schema for whale_signals_latest.json."""
    timestamp: str
    signals: list
    flow_analysis: dict
    balance_changes: dict
    smart_money: list
    error: str | None
