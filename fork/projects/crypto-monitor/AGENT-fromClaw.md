# Crypto Report Agent Instructions

You are the crypto report agent. Complete the daily report.

## When Triggered

Cron triggers you after daily_report_pipeline.sh has run and created data/reports/report_latest.json.

## Your Task

### 1. Run Daily Report Pipeline
```bash
cd /home/node/.openclaw/workspace/crypto-monitor
bash daily_report_pipeline.sh
```

This creates data/reports/report_latest.json with placeholders.

### 2. Read News Data
Read from: /home/node/.openclaw/workspace/crypto-monitor/data/news/news_latest.json

If empty (no articles), find most recent file with data:
```bash
ls -lt /home/node/.openclaw/workspace/crypto-monitor/data/news/news_*.json | head -5
```

### 3. Generate news_summary.md
Create: /home/node/.openclaw/workspace/crypto-monitor/data/reports/news_summary.md

IMPORTANT: NO HEADER. Just list news items.

Format:
**1. Title here**
Brief description...

**2. Title here**
Brief description...

### 4. Generate market_summary.md
Read:
- /home/node/.openclaw/workspace/crypto-monitor/data/reports/report_latest.json
- /home/node/.openclaw/workspace/crypto-monitor/SUMMARY_GUIDE.md

Create: /home/node/.openclaw/workspace/crypto-monitor/data/reports/market_summary.md

IMPORTANT: NO HEADER. Just write content.

Use SUMMARY_GUIDE.md to interpret all indicators correctly. Include:
- Overall market sentiment (based on Fear & Greed)
- Cycle position interpretation
- Technical highlights (MA Cross, RSI, etc.)
- Network health (Hash Rate)
- Cycle top risk
- Brief verdict with actionable insight

Follow the Summary Generation Rules from SUMMARY_GUIDE.md.

### 5. Publish to Discord
After creating summaries, run:
```bash
cd /home/node/.openclaw/workspace/crypto-monitor
bash publish_pipeline.sh
```

This generates discord_messages.json and sends all messages to Discord.

---

## Key Rules

- news_summary.md: NO HEADER, just list items
- market_summary.md: NO HEADER, just write content
- Python scripts add headers automatically
- Always run publish_pipeline.sh at the end
