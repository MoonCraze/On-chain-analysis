# core/technical_analyzer.py
from typing import List, Dict, Any
from core.models import TokenSnapshot, TechnicalAnalysisResult, Candle
import pandas as pd
import pandas_ta as ta # Make sure to install this: pip install pandas_ta

class TechnicalAnalyzer:
    def __init__(self, config: Dict):
        self.ema_short_period = config.get("ta_ema_short", 9)
        self.ema_long_period = config.get("ta_ema_long", 21)
        self.rsi_period = config.get("ta_rsi_period", 14)
        self.rsi_overbought = config.get("ta_rsi_overbought", 70)
        self.rsi_oversold = config.get("ta_rsi_oversold", 30)
        # MACD default periods are usually fine (12, 26, 9)

    def _get_candle_dataframe(self, historical_data: Dict[str, List[Dict[str, Any]]], timeframe: str = "1m") -> Optional[pd.DataFrame]:
        if timeframe not in historical_data or not historical_data[timeframe]:
            print(f"Warning: No historical data for timeframe {timeframe}")
            return None
        try:
            df = pd.DataFrame(historical_data[timeframe])
            # Ensure correct dtypes - this is critical for TA libraries
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            for col in ['open', 'high', 'low', 'close', 'volume']:
                 df[col] = pd.to_numeric(df[col], errors='coerce')
            df.set_index('timestamp', inplace=True)
            df.dropna(inplace=True) # Drop rows with NaN if any conversion failed
            if len(df) < max(self.ema_long_period, self.rsi_period, 26): # MACD needs at least 26 periods
                print(f"Warning: Not enough data points ({len(df)}) for TA calculations on timeframe {timeframe}.")
                return None
            return df
        except Exception as e:
            print(f"Error creating DataFrame for TA: {e}")
            return None


    def analyze(self, token: TokenSnapshot) -> TechnicalAnalysisResult:
        # Prioritize shorter timeframes for meme coins if available, e.g., "1m" or "5m"
        # For this example, let's assume we want to use "1m" if available, else "5m"
        df = self._get_candle_dataframe(token.historicalCandleData, "1m")
        if df is None or len(df) < 26: # Check length again
            df = self._get_candle_dataframe(token.historicalCandleData, "5m")
            if df is None or len(df) < 26:
                 print(f"TA: Not enough data for {token.ticker} on primary timeframes.")
                 return TechnicalAnalysisResult(token_id=token.tokenId) # Return empty result

        close_prices = df['close']

        # EMA
        ema_short = ta.ema(close_prices, length=self.ema_short_period)
        ema_long = ta.ema(close_prices, length=self.ema_long_period)
        ema_cross_state = "NEUTRAL"
        if ema_short is not None and ema_long is not None and not ema_short.empty and not ema_long.empty:
            if ema_short.iloc[-1] > ema_long.iloc[-1] and ema_short.iloc[-2] <= ema_long.iloc[-2]:
                ema_cross_state = "BULLISH_CROSS_RECENT"
            elif ema_short.iloc[-1] < ema_long.iloc[-1] and ema_short.iloc[-2] >= ema_long.iloc[-2]:
                ema_cross_state = "BEARISH_CROSS_RECENT"
            elif ema_short.iloc[-1] > ema_long.iloc[-1]:
                ema_cross_state = "BULLISH_ABOVE"
            elif ema_short.iloc[-1] < ema_long.iloc[-1]:
                ema_cross_state = "BEARISH_BELOW"
        else:
            print(f"TA: Could not calculate EMAs for {token.ticker}")


        # RSI
        rsi = ta.rsi(close_prices, length=self.rsi_period)
        rsi_state = "NEUTRAL"
        current_rsi_value = None
        if rsi is not None and not rsi.empty:
            current_rsi_value = rsi.iloc[-1]
            if current_rsi_value > self.rsi_overbought:
                rsi_state = "OVERBOUGHT"
            elif current_rsi_value < self.rsi_oversold:
                rsi_state = "OVERSOLD"
            elif len(rsi) > 1:
                if current_rsi_value > rsi.iloc[-2]: # Rising
                    rsi_state = "NEUTRAL_RISING"
                else: # Falling
                    rsi_state = "NEUTRAL_FALLING"
        else:
            print(f"TA: Could not calculate RSI for {token.ticker}")


        # MACD
        macd_df = ta.macd(close_prices) # Uses default 12, 26, 9
        macd_state = "NEUTRAL"
        current_macd_val, current_macd_sig, current_macd_hist = None, None, None
        if macd_df is not None and not macd_df.empty:
            current_macd_val = macd_df[f'MACD_{macd_df.columns[0].split("_")[1]}_{macd_df.columns[0].split("_")[2]}_{macd_df.columns[1].split("_")[2]}'].iloc[-1] # Column names can vary
            current_macd_sig = macd_df[f'MACDs_{macd_df.columns[0].split("_")[1]}_{macd_df.columns[0].split("_")[2]}_{macd_df.columns[1].split("_")[2]}'].iloc[-1]
            current_macd_hist = macd_df[f'MACDh_{macd_df.columns[0].split("_")[1]}_{macd_df.columns[0].split("_")[2]}_{macd_df.columns[1].split("_")[2]}'].iloc[-1]

            if current_macd_hist > 0 and (len(macd_df) < 2 or macd_df[f'MACDh_{macd_df.columns[0].split("_")[1]}_{macd_df.columns[0].split("_")[2]}_{macd_df.columns[1].split("_")[2]}'].iloc[-2] <=0):
                macd_state = "BULLISH_CROSS_HIST" # Histogram just crossed positive
            elif current_macd_hist < 0 and (len(macd_df) < 2 or macd_df[f'MACDh_{macd_df.columns[0].split("_")[1]}_{macd_df.columns[0].split("_")[2]}_{macd_df.columns[1].split("_")[2]}'].iloc[-2] >=0):
                macd_state = "BEARISH_CROSS_HIST"
            elif current_macd_hist > 0 :
                macd_state = "BULLISH_MOMENTUM_HIST"
            elif current_macd_hist < 0 :
                macd_state = "BEARISH_MOMENTUM_HIST"
        else:
            print(f"TA: Could not calculate MACD for {token.ticker}")


        # Pattern Recognition (Very Basic Heuristics - needs significant improvement)
        identified_pattern = None
        # Example: Hockey Stick (needs volume data from df too)
        if len(close_prices) > 5:
            price_change_last_5_periods = (close_prices.iloc[-1] - close_prices.iloc[-6]) / close_prices.iloc[-6]
            # Add volume check here from df['volume']
            if price_change_last_5_periods > 0.50: # e.g. 50% increase in last 5 periods
                # A real hockey stick needs more context (low base, rapid acceleration)
                # identified_pattern = "POTENTIAL_HOCKEY_STICK"
                pass # This is too naive, leave for later improvement


        return TechnicalAnalysisResult(
            token_id=token.tokenId,
            ema_9_value=ema_short.iloc[-1] if ema_short is not None and not ema_short.empty else None,
            ema_21_value=ema_long.iloc[-1] if ema_long is not None and not ema_long.empty else None,
            ema_cross_state=ema_cross_state,
            rsi_14_value=current_rsi_value,
            rsi_state=rsi_state,
            macd_value=current_macd_val,
            macd_signal_value=current_macd_sig,
            macd_histogram_value=current_macd_hist,
            macd_state=macd_state,
            identified_pattern=identified_pattern
        )