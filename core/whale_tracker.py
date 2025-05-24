# core/whale_tracker.py
from typing import List, Dict, Set
from core.models import TokenSnapshot, WhaleSummaryResult

class WhaleTracker:
    def __init__(self, config: Dict, tracked_whale_wallets: Set[str]):
        self.tracked_wallets = tracked_whale_wallets
        self.lookback_period_minutes = config.get("whale_lookback_minutes", 15)

    def analyze(self, token: TokenSnapshot) -> WhaleSummaryResult:
        # This is a simplified version that uses the pre-aggregated snapshot
        # A real version would process token.transactionStream
        net_buy_usd = 0.0
        distinct_buyers = 0

        if token.whaleActivity: # Using the pre-calculated snapshot from mock data
            net_buy_usd = token.whaleActivity.netBuyVolumeLast15MinUSD or 0.0
            distinct_buyers = token.whaleActivity.distinctBuyingWhales or 0
        else:
            # Placeholder: if you had transactionStream, you'd iterate here
            # and check if tx.walletAddress is in self.tracked_wallets
            # and sum up buy/sell amounts within self.lookback_period_minutes
            print(f"WhaleTracker: No pre-aggregated whaleActivity for {token.ticker}, or transactionStream processing not implemented.")
            pass

        return WhaleSummaryResult(
            token_id=token.tokenId,
            net_buy_volume_usd_15m=net_buy_usd,
            distinct_buying_whales_15m=distinct_buyers
        )