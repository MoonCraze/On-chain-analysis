# core/recon_filters.py
from typing import List, Dict
from core.models import TokenSnapshot

class Reconnaissance:
    def __init__(self, config: Dict):
        self.min_market_cap = config.get("recon_min_market_cap", 70000)
        self.max_market_cap = config.get("recon_max_market_cap", 11000000)
        self.min_5min_volume = config.get("recon_min_5min_volume", 10000)
        # Add other config params like boost status if needed

    def filter_tokens(self, tokens: List[TokenSnapshot]) -> List[TokenSnapshot]:
        potential_candidates = []
        for token in tokens:
            if not token.marketCap or not token.volume or not token.volume.five_min_usd:
                # print(f"Skipping {token.ticker} due to missing marketCap or 5min volume.")
                continue

            if not (self.min_market_cap <= token.marketCap <= self.max_market_cap):
                # print(f"Skipping {token.ticker} due to market cap: {token.marketCap}")
                continue
            if token.volume.five_min_usd < self.min_5min_volume:
                # print(f"Skipping {token.ticker} due to 5min volume: {token.volume.five_min_usd}")
                continue

            # Add pump.fun origin preference, boost status filters here if desired
            # if token.origin and token.origin.lower() != "pump.fun":
            #     continue

            potential_candidates.append(token)
        print(f"Recon: {len(potential_candidates)} potential candidates from {len(tokens)}.")
        return potential_candidates