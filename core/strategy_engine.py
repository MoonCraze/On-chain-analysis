from typing import List, Dict
from core.models import TokenSnapshot, TechnicalAnalysisResult, WhaleSummaryResult, SecurityCheckResult
import datetime

class StrategyEngine:
    def __init__(self, config: Dict):
        self.config = config

    def get_applicable_strategies(
        self,
        token: TokenSnapshot,
        ta_result: TechnicalAnalysisResult,
        whale_summary: WhaleSummaryResult,
        security_result: SecurityCheckResult # Needed to avoid suggesting strategies for unsafe tokens
    ) -> List[str]:
        applicable = []

        if security_result.overall_status in ["SCAM_LIKELY", "HIGH_RISK"]:
            return [] # Don't suggest strategies for very risky tokens

        # --- Asia Time Hunter ---
        # Simplistic time check - a real one needs timezone awareness
        # current_hour_est = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-5))).hour
        # if 23 <= current_hour_est or current_hour_est <= 1: # Approx 11PM - 1AM EST
        if ta_result.identified_pattern == "POTENTIAL_HOCKEY_STICK" or \
           (ta_result.ema_cross_state == "BULLISH_ABOVE" and (token.volume.five_min_usd or 0) > self.config.get("asia_min_volume", 50000)):
            # Add (mock) meta fit check here if possible
            applicable.append("AsiaTime")

        # --- Post Rug Opportunist ---
        # Condition: Token had a significant past run-up & rug, now showing floor formation
        # This requires knowledge of past MCAP, which isn't directly in TokenSnapshot unless it's stored
        # For now, rely on ta_result.identified_pattern
        if ta_result.identified_pattern == "FLOOR_FORMATION_DOUBLE_BOUNCE" and \
           (token.volume.five_min_usd or 0) > self.config.get("post_rug_min_volume", 15000) and \
           ta_result.rsi_state == "OVERSOLD" or (ta_result.rsi_state == "NEUTRAL_RISING" and (ta_result.rsi_14_value or 0) < 45) :
            applicable.append("PostRug")

        # --- Momentum Rider ---
        is_bullish_ta = (
            ta_result.ema_cross_state in ["BULLISH_CROSS_RECENT", "BULLISH_ABOVE"] and
            ta_result.rsi_state not in ["OVERBOUGHT"] and (ta_result.rsi_14_value or 100) < 68 and # Not too close to overbought
            ta_result.macd_state in ["BULLISH_CROSS_HIST", "BULLISH_MOMENTUM_HIST"]
        )
        if is_bullish_ta and \
           (token.volume.five_min_usd or 0) > self.config.get("momentum_min_volume", 20000) and \
           whale_summary.net_buy_volume_usd_15m > self.config.get("momentum_min_whale_net_buy", 500.0):
            applicable.append("MomentumRider")

        return list(set(applicable)) # Ensure unique strategies