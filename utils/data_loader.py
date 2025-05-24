import json
import os
from typing import List, Dict, Any
from core.models import TokenSnapshot # Assuming models.py is in a 'core' sibling directory or package

# Helper to convert JSON keys with specific metadata
def _convert_keys(d, key_map):
    if isinstance(d, dict):
        return {key_map.get(k, k): _convert_keys(v, key_map) for k, v in d.items()}
    elif isinstance(d, list):
        return [_convert_keys(i, key_map) for i in d]
    return d

def load_token_snapshots(filepath: str) -> List[TokenSnapshot]:
    """Loads token snapshots from a JSON file."""
    snapshots = []
    # Define key mappings based on your TokenSnapshot VolumeInfo field metadata
    # This is a simplified example; a more robust solution would inspect dataclass metadata
    key_map = {
        "5minUSD": "five_min_usd",
        "1hrUSD": "one_hr_usd",
        "6hrUSD": "six_hr_usd",
        "24hrUSD": "twenty_four_hr_usd"
    }
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            for item_data in data:
                # Apply key conversion specifically for the volume part if needed
                if 'volume' in item_data and isinstance(item_data['volume'], dict):
                    item_data['volume'] = _convert_keys(item_data['volume'], key_map)

                # Handle nested dataclasses by pre-constructing them if necessary
                # This part can get complex and might need a library like dacite or manual construction
                # For simplicity, we'll assume direct mapping works for most fields
                # or that the JSON is structured to match the dataclass.
                # Example for one nested class:
                if 'security' in item_data and item_data['security'] and 'bundlerAnalysis' in item_data['security'] and item_data['security']['bundlerAnalysis']:
                     item_data['security']['bundlerAnalysis'] = models.BundleAnalysisInfo(**item_data['security']['bundlerAnalysis'])
                if 'security' in item_data and item_data['security']:
                    item_data['security'] = models.SecurityInfo(**item_data['security'])
                if 'links' in item_data and item_data['links']:
                    item_data['links'] = models.LinkInfo(**item_data['links'])
                # ... and so on for other nested dataclasses like LiquidityInfo, VolumeInfo, HolderInfo etc.
                # This is where a library like `dacite` would be very helpful:
                # from dacite import from_dict
                # snapshot = from_dict(data_class=TokenSnapshot, data=item_data)

                try:
                    # Simplistic instantiation, may fail with complex nesting without proper pre-processing
                    # or a library like dacite.
                    # For now, let's assume the JSON structure is massaged to fit or
                    # we manually instantiate nested objects.
                    snapshot = TokenSnapshot(**item_data) # This is very basic
                    snapshots.append(snapshot)
                except TypeError as e:
                    print(f"Error instantiating TokenSnapshot for item: {item_data.get('ticker', 'N/A')}. Error: {e}")
                    print("Problematic item data:", item_data)


    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {filepath}")
    return snapshots


def load_historical_data(token_id: str, base_path: str = "mock_data/historical_data") -> Dict[str, List[Dict[str, Any]]]:
    """Loads historical OHLCV data for a specific token."""
    filepath = os.path.join(base_path, f"{token_id}_ohlcv.json")
    try:
        with open(filepath, 'r') as f:
            return json.load(f) # Expects format: {"1m": [candles], "5m": [candles]}
    except FileNotFoundError:
        print(f"Warning: Historical data not found for {token_id} at {filepath}")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {filepath}")
        return {}

# Add similar loader for transaction_stream if needed