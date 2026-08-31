"""
Section: Exchange Holdings / Flows.
"""

from reports.sections._base import SectionRenderer


class SectionFlows(SectionRenderer):

    def render(self) -> str:
        flows = self.data.get("exchange_flows", {})
        if not flows:
            return ""

        ex_data = flows.get("flows", {}) or {}
        ex_exchanges = flows.get("exchanges", {}) or {}

        if not ex_data and not ex_exchanges:
            return ""

        lines = ["## 🏦 Exchange Holdings"]

        exchange_names = ["Binance", "Coinbase", "Kraken", "Bybit", "OKX"]
        flow_rows = []
        net_btc = 0
        net_eth = 0

        for name in exchange_names:
            if ex_data:
                ef = ex_data.get(name, {})
                btc_f = ef.get("bitcoin", {})
                eth_f = ef.get("ethereum", {})
                btc_delta = btc_f.get("delta", 0) or 0
                eth_delta = eth_f.get("ethereum", {}).get("delta", 0) or 0
            elif ex_exchanges:
                ex = ex_exchanges.get(name, {})
                btc_t = ex.get("bitcoin", {}).get("total_btc", 0) or 0
                eth_t = ex.get("ethereum", {}).get("total_eth", 0) or 0
                btc_delta = 0
                eth_delta = 0
            else:
                continue

            if ex_data:
                if abs(btc_delta) >= 0.1:
                    btc_str = f"{abs(btc_delta):,.1f} {'<-' if btc_delta < 0 else '->'}"
                    net_btc += btc_delta
                else:
                    btc_str = "--"

                if abs(eth_delta) >= 10:
                    eth_str = f"{abs(eth_delta):,.0f} {'<-' if eth_delta < 0 else '->'}"
                    net_eth += eth_delta
                else:
                    eth_str = "--"

                flow_rows.append([name[:8], btc_str, eth_str])
            elif ex_exchanges and (btc_t > 0 or eth_t > 0):
                btc_s = f"{btc_t:,.0f}" if btc_t > 0 else "--"
                eth_s = f"{eth_t:,.0f}" if eth_t > 0 else "--"
                flow_rows.append([name[:8], btc_s, eth_s])

        if not flow_rows:
            return ""

        table = self.box_table(
            headers=["Exchange", "BTC", "ETH"],
            rows=flow_rows,
            aligns=["l", "r", "r"],
        )
        lines.append(f"```\n{table}\n```")

        return "\n".join(lines)


def render(data: dict) -> str:
    return SectionFlows(data).render()
