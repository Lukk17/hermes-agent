#!/usr/bin/env python3
"""
Generate Report JSON
Runs all collectors, analyzers, and builds report_latest.json.

Error handling: each step runs independently - if one fails, it is recorded
and the pipeline continues. The exit code reports the outcome so the caller
never publishes yesterday's report as today's.

Exit codes:
    0 - report_latest.json rewritten, no critical step failed
    1 - a critical step failed
    2 - report_latest.json was not rewritten this run
"""

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
REPORT_DIR = PROJECT_ROOT / "data" / "reports"
REPORT_LATEST = REPORT_DIR / "report_latest.json"

# Add project to path for src imports
sys.path.insert(0, str(PROJECT_ROOT))

# Use venv Python for matplotlib support
PYTHON_BIN = PROJECT_ROOT / ".venv" / "bin" / "python"

TIMEOUT = 60  # seconds per step

EXIT_OK = 0
EXIT_CRITICAL = 1
EXIT_STALE_REPORT = 2


def run_script(script_path, label, severity="error"):
    """
    Run a Python script with timeout.
    Records failures on the error collector but never crashes the pipeline.
    """
    from src.pipeline_errors import error_collector

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
            error_collector.add_error(Path(script_path).name, error_msg, severity)
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"  ⚠️ {label} timed out after {TIMEOUT}s")
        error_collector.add_error(
            Path(script_path).name, f"timed out after {TIMEOUT}s", severity
        )
        return False
    except OSError as e:
        print(f"  ⚠️ {label} error: {e}")
        error_collector.add_error(Path(script_path).name, str(e), severity)
        return False


def main():
    started_at = time.time()
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

    run_script(
        PROJECT_ROOT / "reports/daily_report.py", "📊 Daily Report...", "critical"
    )

    # Save pipeline errors
    error_collector.save(report_date)

    print("\n✅ Pipeline complete")

    counts = error_collector.count_by_severity()
    if error_collector.has_errors():
        print(f"\n⚠️  {error_collector.total_count()} errors during pipeline")
        if counts["warning"]:
            print(f"   - {counts['warning']} warnings")
        if counts["error"]:
            print(f"   - {counts['error']} errors")
        if counts["critical"]:
            print(f"   - {counts['critical']} critical")
        print(f"   See data/reports/pipeline_errors_{report_date}.json for details")
    else:
        print("   No errors - clean run!")

    if not report_is_fresh(started_at):
        print(f"\n❌ {REPORT_LATEST} was not rewritten this run")
        print("   Refusing to publish a stale report")
        return EXIT_STALE_REPORT

    if counts["critical"]:
        print("\n❌ A critical step failed - refusing to publish this run")
        return EXIT_CRITICAL

    print("\nNext step: daily_report_pipeline.sh runs scripts/post_to_discord.py,")
    print("which delivers report_latest.json via services.agent_bridge.send_message().")
    return EXIT_OK


def report_is_fresh(started_at):
    """True when report_latest.json was written after the pipeline started."""
    try:
        return REPORT_LATEST.stat().st_mtime >= started_at
    except OSError:
        return False


if __name__ == "__main__":
    sys.exit(main())
