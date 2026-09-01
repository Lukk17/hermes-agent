#!/usr/bin/env python3
"""
Generate Report JSON
Runs all collectors, analyzers, and builds report_latest.json.

Error handling: each collector runs independently - if one fails,
it logs an error and continues. Pipeline never crashes.
"""

import sys
import subprocess
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
REPORT_DIR = PROJECT_ROOT / "data" / "reports"

# Add project to path for src imports
sys.path.insert(0, str(PROJECT_ROOT))

# Use venv Python for matplotlib support
PYTHON_BIN = PROJECT_ROOT / ".venv" / "bin" / "python"

TIMEOUT = 60  # seconds per step


def run_script(script_path, label):
    """
    Run a Python script with timeout.
    Captures errors but never crashes the pipeline.
    """
    print(f"{label}")
    try:
        result = subprocess.run(
            [str(PYTHON_BIN), str(script_path)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=TIMEOUT
        )
        if result.returncode != 0:
            # Script exited with error - but pipeline continues
            stderr_preview = result.stderr.strip()[:200] if result.stderr else ""
            stdout_preview = result.stdout.strip()[:200] if result.stdout else ""
            error_msg = stderr_preview or stdout_preview or "Unknown error"
            print(f"  ⚠️ {label} completed with warnings: {error_msg}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"  ⚠️ {label} timed out after {TIMEOUT}s")
        return False
    except Exception as e:
        print(f"  ⚠️ {label} error: {e}")
        return False


def main():
    report_date = datetime.utcnow().strftime("%Y-%m-%d")
    
    print("=" * 50)
    print("RUNNING CRYPTO-MONITOR PIPELINE")
    print(f"Date: {report_date}")
    print("=" * 50)
    
    # Initialize error collector
    from src.pipeline_errors import error_collector
    error_collector.clear()
    
    # --- Collectors ---
    print("\n--- COLLECTORS ---")
    
    # Prefetch CoinGecko data ONCE for all collectors
    from collectors.cache_manager import prefetch_coingecko_data
    prefetch_coingecko_data()
    
    # Run ALL collectors - each handles own errors
    collectors = [
        ("collectors/coin_prices_collector.py", "💰 Coin Prices..."),
        ("collectors/news_collector.py", "📰 News Collector..."),
        ("collectors/exchange_flow_tracker.py", "🏦 Exchange Flows..."),
        ("collectors/whale_tracker_blockscout.py", "🐋 Whale Tracker (Blockscout)..."),
        ("collectors/whale_tracker_alchemy.py", "🐋 Whale Tracker (Alchemy)..."),
        ("collectors/index_scraper.py", "📊 External Indices..."),
        ("collectors/sector_collector.py", "🏭 Crypto Sectors..."),
        ("collectors/gas_collector.py", "⛽ ETH Gas..."),
        ("collectors/etf_flow_collector.py", "📊 ETF Flows..."),
        ("collectors/stablecoin_collector.py", "💵 Stablecoins..."),
        ("collectors/funding_collector.py", "💰 Funding Rates..."),
        ("collectors/influencer_collector.py", "👥 Influencer..."),
        ("collectors/dominance_chart.py", "📈 BTC Dominance..."),
        ("collectors/btc_price_chart.py", "₿ BTC Price..."),
        ("collectors/defi_tvl_collector.py", "📊 DeFi TVL..."),
        ("collectors/market_breadth_collector.py", "📊 Market Breadth..."),
    ]
    
    for script, label in collectors:
        run_script(PROJECT_ROOT / script, label)
    
    # --- Analyzers ---
    print("\n--- ANALYZERS ---")
    
    analyzers = [
        ("analyzers/cycle_analyzer.py", "📈 Cycle Analyzer..."),
        ("analyzers/sentiment.py", "💬 Sentiment Analyzer..."),
        ("analyzers/trend_detector.py", "🔍 Trend Detector..."),
        ("analyzers/whale_signals.py", "🐋 Whale Signals..."),
        ("analyzers/airdrop_tracker.py", "🪂 Airdrop Tracker..."),
    ]
    
    for script, label in analyzers:
        run_script(PROJECT_ROOT / script, label)
    
    # --- Report ---
    print("\n--- REPORT ---")
    
    run_script(PROJECT_ROOT / "reports/daily_report.py", "📊 Daily Report...")
    
    # Save pipeline errors
    error_collector.save(report_date)
    
    print("\n✅ Pipeline complete")
    
    if error_collector.has_errors():
        counts = error_collector.count_by_severity()
        print(f"\n⚠️  {error_collector.count_errors()} errors during pipeline")
        if counts["warning"]:
            print(f"   - {counts['warning']} warnings")
        if counts["error"]:
            print(f"   - {counts['error']} errors")
        print(f"   See data/reports/pipeline_errors_{report_date}.json for details")
    else:
        print("   No errors - clean run!")
    
    print("\nNext steps:")
    print("1. Agent generates news_summary.md")
    print("2. Agent generates market_summary.md")
    print("3. Run publish_report.py to send to Discord")


if __name__ == "__main__":
    main()
