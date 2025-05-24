import json
import time
from core import models # This might need to be from core.models import ... depending on your structure
from utils import data_loader
from core.recon_filters import Reconnaissance
from core.security_analyzer import SecurityAnalyzer
from core.technical_analyzer import TechnicalAnalyzer
from core.whale_tracker import WhaleTracker
from core.strategy_engine import StrategyEngine
from core.decision_engine import DecisionEngine

def load_config(filepath="config.json") -> Dict:
    with open(filepath, 'r') as f:
        return json.load(f)

def load_tracked_whales(filepath: str) -> Set[str]:
    try:
        with open(filepath, 'r') as f:
            return {line.strip() for line in f if line.strip()}
    except FileNotFoundError:
        print(f"Whale wallet file not found: {filepath}. Returning empty set.")
        return set()

def main():
    print("Starting Vic's Viper AI (Mock Data Mode)...")
    config = load_config()
    tracked_whales = load_tracked_whales(config.get("tracked_whale_wallets_file", ""))

    # --- Load Mock Data ---
    # Assuming your JSON is structured as a list of token snapshot dicts
    raw_token_snapshots_data = data_loader.load_token_snapshots("mock_data/token_snapshots.json")
    all_token_snapshots: List[models.TokenSnapshot] = []

    # Populate historical and transaction data for each snapshot
    for snap_data in raw_token_snapshots_data: # snap_data is now a TokenSnapshot object
        # The data_loader.py example needs to be more robust to create TokenSnapshot directly
        # For now, let's assume snap_data is a TokenSnapshot object.
        # If it's still a dict, you'd instantiate here.
        # snap_data.historicalCandleData = data_loader.load_historical_data(snap_data.tokenId)
        # snap_data.transactionStream = data_loader.load_transaction_stream(snap_data.tokenId) # If you implement this
        all_token_snapshots.append(snap_data)


    print(f"Loaded {len(all_token_snapshots)} total token snapshots.")

    # --- Initialize Modules ---
    recon_module = Reconnaissance(config)
    security_module = SecurityAnalyzer(config)
    ta_module = TechnicalAnalyzer(config)
    whale_module = WhaleTracker(config, tracked_whales)
    strategy_module = StrategyEngine(config)
    decision_module = DecisionEngine(config)

    # --- Main Processing Loop (Simulated) ---
    # In a real system, this would run continuously or on a schedule
    # For mock data, we process once.

    potential_candidates = recon_module.filter_tokens(all_token_snapshots)

    active_positions = {} # Simulate open trades: {token_id: {"entry_price": ..., "amount_held": ..., "buy_strategy": ...}}

    for token in potential_candidates:
        print(f"\n--- Analyzing Token: {token.ticker} ({token.contractAddress}) ---")

        # If we have an active position, check for SELL signals first
        if token.tokenId in active_positions:
            current_pos_details = active_positions[token.tokenId]
            # Re-run TA and Security for current state
            # In a real system, you'd fetch fresh data for the token here
            # For mock, we use the same snapshot, but TA should be on its historical.
            # We need to ensure the token snapshot being used for TA is the *latest*
            # For simplicity with mock, we'll use the existing ta_result if available from the snapshot,
            # but ideally, it should be recalculated based on the *current time* relative to historical data.
            # This is a limitation of static mock data processing.

            # Let's assume historical data is part of the token object for TA module
            token.historicalCandleData = data_loader.load_historical_data(token.tokenId, "mock_data/historical_data") # Reload for TA
            
            current_ta_result = ta_module.analyze(token)
            current_security_result = security_module.analyze(token) # Re-check security

            sell_signal = decision_module.generate_sell_signal(
                token, current_pos_details, current_ta_result, current_security_result
            )
            if sell_signal:
                print(f"SELL SIGNAL for {sell_signal.ticker}: Type: {sell_signal.sell_type}, Price: ${sell_signal.suggested_exit_price:.6f}")
                for reason in sell_signal.reasoning: print(f"  - {reason}")
                # Simulate selling:
                del active_positions[token.tokenId]
                continue # Don't check for buy if we just sold


        # If no active position, or didn't sell, check for BUY signals
        security_result = security_module.analyze(token)
        if security_result.overall_status in ["SCAM_LIKELY", "HIGH_RISK"]:
            print(f"Security Risk for {token.ticker}: {security_result.overall_status}. Details:")
            # for detail in security_result.details: print(f"  - {detail['check']}: {detail['status']} - {detail['reason']}")
            continue

        # Load historical data for TA
        token.historicalCandleData = data_loader.load_historical_data(token.tokenId, "mock_data/historical_data")
        if not token.historicalCandleData:
             print(f"No historical data for {token.ticker} to perform TA. Skipping TA.")
             # Decide if you want to proceed without TA or skip
             # For now, let's require TA
             continue


        ta_result = ta_module.analyze(token)
        whale_summary = whale_module.analyze(token) # Uses snapshot data if available
        
        print(f"  TA: EMA: {ta_result.ema_cross_state}, RSI: {ta_result.rsi_state} ({ta_result.rsi_14_value:.2f}), MACD: {ta_result.macd_state}")
        print(f"  Whales: Net Buy 15m: ${whale_summary.net_buy_volume_usd_15m:.0f}, Buyers: {whale_summary.distinct_buying_whales_15m}")
        print(f"  Security: {security_result.overall_status}")


        applicable_strategies = strategy_module.get_applicable_strategies(
            token, ta_result, whale_summary, security_result
        )
        print(f"  Applicable Strategies: {applicable_strategies}")

        if applicable_strategies:
            buy_signal = decision_module.generate_buy_signal(
                token, applicable_strategies, ta_result, whale_summary, security_result
            )
            if buy_signal:
                print(f"BUY SIGNAL for {buy_signal.ticker}: Strategy: {buy_signal.strategy}, Confidence: {buy_signal.confidence_score:.2f}")
                print(f"  Entry Range: ${buy_signal.suggested_entry_price_range[0]:.6f} - ${buy_signal.suggested_entry_price_range[1]:.6f}")
                for reason in buy_signal.reasoning: print(f"  - {reason}")
                # Simulate buying:
                active_positions[token.tokenId] = {
                    "entry_price": (buy_signal.suggested_entry_price_range[0] + buy_signal.suggested_entry_price_range[1]) / 2,
                    "amount_held": 1000, # Dummy amount
                    "buy_strategy": buy_signal.strategy,
                    "initial_security_status": security_result.overall_status # Store for sell logic
                }

    print("\n--- Processing Complete ---")
    if active_positions:
        print("Simulated Active Positions:")
        for token_id, pos_details in active_positions.items():
            print(f"  Token ID: {token_id}, Entry: ${pos_details['entry_price']:.6f}, Strategy: {pos_details['buy_strategy']}")


if __name__ == "__main__":
    # Create mock_data directory and dummy files if they don't exist for the script to run
    os.makedirs("mock_data/historical_data", exist_ok=True)
    os.makedirs("mock_data/transaction_data", exist_ok=True)
    # You would populate these with your actual mock data.
    # Example: Create a dummy token_snapshots.json
    dummy_snapshots = [
        # Add at least one complete TokenSnapshot dictionary here that matches your models.py
        # and for which you also create a corresponding _ohlcv.json file.
        # This is crucial for the script to have something to process.
        # For example:
        {
            "tokenId": "MOCK001_SOL_PUMP",
            "timestampCollected": "2024-07-29T10:00:05Z",
            "source": "AxiomPro_Pulse_NewPairs",
            "contractAddress": "MockSoLmAeMCo1nAdDrEsS001PUMP",
            "ticker": "MOCKROCKET",
            "name": "Mock Rocket To The Moon",
            "marketCap": 85000.00,
            "volume": {"5minUSD": 15200.00}, # Mapped to five_min_usd
            "security": {"mintAuthorityDisabled": True, "freezeAuthorityDisabled": True},
            "historicalCandleData": {}, # Will be loaded by load_historical_data
            "whaleActivity": {"netBuyVolumeLast15MinUSD": 1200.00, "distinctBuyingWhales": 2}
            # ... add other required fields as per TokenSnapshot model, even if None/empty
        }
    ]
    with open("mock_data/token_snapshots.json", "w") as f:
        json.dump(dummy_snapshots, f, indent=2)

    dummy_ohlcv_data = {
        "1m": [{"timestamp": "2024-07-29T09:58:00Z", "open": 0.000082, "high": 0.000083, "low": 0.000081, "close": 0.000083, "volume": 5200.00} for _ in range(30)], # Need enough for TA
        "5m": [{"timestamp": "2024-07-29T09:50:00Z", "open": 0.000075, "high": 0.000080, "low": 0.000074, "close": 0.000079, "volume": 25000.00} for _ in range(10)]
    }
    with open("mock_data/historical_data/MOCK001_SOL_PUMP_ohlcv.json", "w") as f:
        json.dump(dummy_ohlcv_data, f, indent=2)

    with open("mock_data/whale_wallets.txt", "w") as f:
        f.write("WhaleWallet1FakeAddress\n")
        f.write("WhaleWallet2OtherFake\n")


    main()