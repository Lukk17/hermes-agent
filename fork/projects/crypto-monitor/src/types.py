"""
src/types.py - Type definitions for crypto-monitor.

All dataclasses and type aliases should be defined here.
These provide type safety across collectors, analyzers, and reports.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


# =============================================================================
# Coin Data
# =============================================================================

@dataclass
class CoinData:
    """Single coin data entry."""
    id: str                    # CoinGecko coin ID
    symbol: str               # Uppercased ticker (BTC, ETH)
    name: str                 # Full name (Bitcoin, Ethereum)
    price: float              # Current price in USD
    change_24h: float         # 24h price change percentage
    market_cap: int          # Market cap in USD
    volume: int               # 24h trading volume
    
    @classmethod
    def from_dict(cls, data: dict) -> "CoinData":
        """Create from dictionary (e.g., CoinGecko API response)."""
        return cls(
            id=data.get("id", ""),
            symbol=data.get("symbol", "").upper(),
            name=data.get("name", ""),
            price=float(data.get("current_price", 0)),
            change_24h=float(data.get("price_change_percentage_24h", 0)),
            market_cap=int(data.get("market_cap", 0)),
            volume=int(data.get("total_volume", 0))
        )


# =============================================================================
# Whale Data
# =============================================================================

@dataclass
class BTCWhaleData:
    """Single BTC whale entry."""
    label: str
    address: str
    chain: Literal["bitcoin"] = "bitcoin"
    balance_btc: float = 0.0
    balance_usd: float = 0.0
    checked_at: str = ""


@dataclass
class ETHWhaleData:
    """Single ETH whale entry."""
    label: str
    address: str
    chain: Literal["ethereum"] = "ethereum"
    balance_eth: float = 0.0
    balance_usd: float = 0.0
    category: str = "unknown"
    checked_at: str = ""


# =============================================================================
# Stablecoin Data
# =============================================================================

@dataclass
class StablecoinData:
    """Single stablecoin data entry."""
    symbol: str
    name: str
    market_cap: int
    change_7d_pct: float = 0.0


@dataclass
class StablecoinsSummary:
    """Aggregated stablecoin data."""
    coins: list[StablecoinData] = field(default_factory=list)
    total_mcap: int = 0
    total_7d_change: float = 0.0
    direction: Literal["expanding", "contracting", "stable"] = "stable"


# =============================================================================
# Sector Data
# =============================================================================

@dataclass
class SectorData:
    """Single sector entry."""
    name: str
    full_name: str
    change_24h: float
    market_cap: int
    category: str = "other"


# =============================================================================
# Report Output
# =============================================================================

@dataclass
class ReportSection:
    """Single section of the daily report."""
    key: str          # e.g., "prices", "movers"
    content: str      # Formatted content (markdown for Discord)
    has_error: bool = False
    error_message: str = ""


@dataclass  
class ChartOutput:
    """Chart image output."""
    key: str          # e.g., "gauge_fng"
    path: str | None  # Path to generated image
    has_error: bool = False
    error_message: str = ""


@dataclass
class ReportOutput:
    """Complete daily report output."""
    sections: dict[str, str]
    charts: dict[str, str | None]
    timestamp: str
    has_errors: bool = False
    error_file: str | None = None
