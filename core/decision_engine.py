from typing import List, Dict, Optional, Tuple
from core.models import (
    TokenSnapshot, TechnicalAnalysisResult, WhaleSummaryResult,
    SecurityCheckResult, BuySignal, SellSignal
)

class DecisionEngine:
    def __init__(self, config: Dict):
        self.config = config
        self.min_confidence_buy = config.get("dec_min_confidence_buy", 0.6)

    def _calculate_confidence(self, reasons: List[str], strategy: str) -> float:
        # Very basic confidence calculation
        score = 0.5 # Base
        if "BULLISH_CROSS_RECENT" in str(reasons): score += 0.1
        if "RSI_NEUTRAL_RISING" in str(reasons): score += 0.05
        if "MACD_BULLISH_MOMENTUM" in str(reasons): score += 0.1
        if "STRONG_VOLUME" in str(reasons): score += 0.1
        if "WHALE_BUYING" in str(reasons): score += 0.1
        if strategy == "PostRug" and "FLOOR_FORMATION" in str(reasons): score += 0.15
        return min(1.0, score)


    def generate_buy_signal(
        self,
        token: TokenSnapshot,
        applicable_strategies: List[str],
        ta_result: TechnicalAnalysisResult,
        whale_summary: WhaleSummaryResult,
        security_result: SecurityCheckResult
    ) -> Optional[BuySignal]:

        if security_result.overall_status not in ["SAFE", "MODERATE_RISK"]: # Allow moderate for memes
            # print(f"DecisionEngine: Skipping BUY for {token.ticker} due to security: {security_result.overall_status}")
            return None
        if not applicable_strategies:
            return None

        # Prioritize strategies or pick the first one for simplicity
        strategy_to_use = applicable_strategies[0]
        reasons = [f"Strategy: {strategy_to_use}"]
        buy = False

        # --- Logic for each strategy ---
        if strategy_to_use == "MomentumRider":
            if (ta_result.ema_cross_state in ["BULLISH_CROSS_RECENT", "BULLISH_ABOVE"] and
                ta_result.rsi_state not in ["OVERBOUGHT"] and (ta_result.rsi_14_value or 100) < 65 and # Give some room
                ta_result.macd_state in ["BULLISH_CROSS_HIST", "BULLISH_MOMENTUM_HIST"] and
                (token.volume.five_min_usd or 0) > self.config.get("momentum_min_volume_buy_confirm", 25000) and
                whale_summary.net_buy_volume_usd_15m > self.config.get("momentum_min_whale_buy_confirm", 750.0)):
                buy = True
                reasons.append(f"TA: EMA {ta_result.ema_cross_state}, RSI {ta_result.rsi_state} ({ta_result.rsi_14_value:.2f}), MACD {ta_result.macd_state}")
                reasons.append(f"Volume: 5min Vol ${(token.volume.five_min_usd or 0):.0f} > Threshold")
                reasons.append(f"Whales: Net Buy ${whale_summary.net_buy_volume_usd_15m:.0f} > Threshold")

        elif strategy_to_use == "PostRug":
            if (ta_result.identified_pattern == "FLOOR_FORMATION_DOUBLE_BOUNCE" and
                ta_result.rsi_state == "NEUTRAL_RISING" and (ta_result.rsi_14_value or 0) < 50 and # Ensure it's still low
                (token.volume.five_min_usd or 0) > self.config.get("post_rug_min_volume_buy_confirm", 20000)):
                buy = True
                reasons.append(f"TA: Pattern {ta_result.identified_pattern}, RSI {ta_result.rsi_state} ({ta_result.rsi_14_value:.2f})")
                reasons.append(f"Volume: 5min Vol ${(token.volume.five_min_usd or 0):.0f} > Threshold")

        elif strategy_to_use == "AsiaTime":
             if (ta_result.identified_pattern == "POTENTIAL_HOCKEY_STICK" or \
                (ta_result.ema_cross_state == "BULLISH_ABOVE" and (token.volume.five_min_usd or 0) > self.config.get("asia_min_volume_buy_confirm", 60000))):
                buy = True
                reasons.append(f"TA: Pattern {ta_result.identified_pattern or 'Strong Upward EMA'}, EMA {ta_result.ema_cross_state}")
                reasons.append(f"Volume: 5min Vol ${(token.volume.five_min_usd or 0):.0f} > Threshold for Asia time")


        if buy:
            confidence = self._calculate_confidence(reasons, strategy_to_use)
            if confidence >= self.min_confidence_buy and token.technicalAnalysis and token.technicalAnalysis.priceUSD:
                entry_price = token.technicalAnalysis.priceUSD
                # Suggest a small range around current price
                entry_range = (entry_price * 0.995, entry_price * 1.005)
                return BuySignal(
                    token_id=token.tokenId, contract_address=token.contractAddress, ticker=token.ticker,
                    strategy=strategy_to_use, suggested_entry_price_range=entry_range,
                    confidence_score=confidence, reasoning=reasons
                )
        return None


    def generate_sell_signal(
        self,
        token: TokenSnapshot, # Current state of the token
        current_position: Dict, # e.g., {"entry_price": 0.0001, "amount_held": 1000000, "buy_strategy": "MomentumRider"}
        ta_result: TechnicalAnalysisResult,
        security_result: SecurityCheckResult # To check for degradation
    ) -> Optional[SellSignal]:
        # --- Stop Loss First ---
        if token.technicalAnalysis and token.technicalAnalysis.priceUSD:
            current_price = token.technicalAnalysis.priceUSD
            stop_loss_price = current_position['entry_price'] * (1 - self.config.get("stop_loss_percent", 0.25)) # 25% SL
            if current_price <= stop_loss_price:
                return SellSignal(token.tokenId, token.contractAddress, token.ticker, "STOP_LOSS", current_price,
                                  [f"Price hit stop loss level of ${stop_loss_price:.6f}"], "STOP_LOSS")

        # Security Degradation (e.g. new critical dev bundle found, LP unlocked)
        if security_result.overall_status in ["SCAM_LIKELY", "HIGH_RISK"] and \
           current_position.get("initial_security_status", "SAFE") not in ["SCAM_LIKELY", "HIGH_RISK"]: # if it was safe at buy time
            return SellSignal(token.tokenId,token.contractAddress, token.ticker, "EMERGENCY_SELL_SECURITY", current_price,
                              [f"Security status degraded to {security_result.overall_status}"], "STOP_LOSS")


        # --- Profit Taking ---
        entry_price = current_position['entry_price']
        profit_multiplier = (current_price / entry_price) if entry_price > 0 else 0

        # Strategy-specific take profit (Vic's advice)
        buy_strategy = current_position.get("buy_strategy")
        if buy_strategy == "PostRug":
            target_profit_post_rug = self.config.get("post_rug_take_profit_percent", 0.50) # e.g., 50%
            if profit_multiplier >= (1 + target_profit_post_rug):
                return SellSignal(token.tokenId, token.contractAddress, token.ticker, buy_strategy, current_price,
                                  [f"PostRug strategy hit {target_profit_post_rug*100}% profit target."], "TAKE_PROFIT_FULL")

        # General TA-based profit taking
        sell_reasons = []
        partial_sell = False
        full_sell = False

        if ta_result.rsi_state == "OVERBOUGHT" and (ta_result.rsi_14_value or 0) > self.config.get("rsi_sell_threshold", 75):
            sell_reasons.append(f"RSI Overbought ({ta_result.rsi_14_value:.2f})")
            partial_sell = True # Start taking profits
        if ta_result.ema_cross_state == "BEARISH_CROSS_RECENT":
            sell_reasons.append("EMA Bearish Cross")
            full_sell = True # Stronger sell signal
        if ta_result.macd_state in ["BEARISH_CROSS_HIST", "BEARISH_MOMENTUM_HIST_WEAKENING"]: # Add weakening concept
            sell_reasons.append(f"MACD Bearish ({ta_result.macd_state})")
            partial_sell = True
            if ta_result.macd_state == "BEARISH_CROSS_HIST": full_sell = True


        # Volume drop check
        # This requires comparing current 5min volume to a recent average or peak
        # For now, let's assume a simple check if current volume is low
        # if token.volume and (token.volume.five_min_usd or float('inf')) < self.config.get("min_sell_confirm_volume", 5000):
        #     sell_reasons.append("Volume Dropped Significantly")
        #     full_sell = True


        if full_sell and sell_reasons:
            return SellSignal(token.tokenId, token.contractAddress, token.ticker, "TA_EXIT", current_price, sell_reasons, "TAKE_PROFIT_FULL")
        elif partial_sell and sell_reasons:
            # Implement logic for how much to sell partially (e.g., 25%)
            partial_percent = self.config.get("partial_sell_amount_percent", 0.25)
            # Check if a partial sell was already done recently to avoid over-selling
            # This needs state tracking for positions.
            # For now, just generate the signal.
            return SellSignal(token.tokenId, token.contractAddress, token.ticker, "TA_EXIT_PARTIAL", current_price, sell_reasons,
                              "TAKE_PROFIT_PARTIAL", partial_sell_percent=partial_percent)

        return None