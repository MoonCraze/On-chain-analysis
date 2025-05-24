from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass
class LinkInfo:
    x: Optional[str] = None
    telegram: Optional[str] = None
    website: Optional[str] = None

@dataclass
class LiquidityInfo:
    poolSizeUSD: Optional[float] = None
    lpBurnedPercent: Optional[float] = None
    creationTimestamp: Optional[str] = None
    lpTokenAddress: Optional[str] = None

@dataclass
class VolumeInfo:
    five_min_usd: Optional[float] = field(default=None, metadata={'json_name': '5minUSD'})
    one_hr_usd: Optional[float] = field(default=None, metadata={'json_name': '1hrUSD'})
    six_hr_usd: Optional[float] = field(default=None, metadata={'json_name': '6hrUSD'})
    twenty_four_hr_usd: Optional[float] = field(default=None, metadata={'json_name': '24hrUSD'})


@dataclass
class HolderInfo:
    count: Optional[int] = None
    proHoldersCount: Optional[int] = None
    top10HolderPercent: Optional[float] = None

@dataclass
class BundleAnalysisInfo:
    totalBundledPercent: Optional[float] = None
    topBundlePercent: Optional[float] = None
    freshWalletBundles: Optional[bool] = None

@dataclass
class XAccountRecycleCheck:
    checkedTimestamp: Optional[str] = None
    status: Optional[str] = None # "CLEAN", "SUSPICIOUS_RECENT_CHANGE", etc.
    accountAgeYears: Optional[float] = None
    previousUsernames: List[str] = field(default_factory=list)

@dataclass
class SecurityInfo:
    mintAuthorityDisabled: Optional[bool] = None
    freezeAuthorityDisabled: Optional[bool] = None
    devHoldingsPercent: Optional[float] = None
    insiderHoldingsPercent: Optional[float] = None
    sniperHoldingsPercent: Optional[float] = None
    bundlerAnalysis: Optional[BundleAnalysisInfo] = None
    isCopycat: Optional[bool] = None
    paidDexScreenerProfile: Optional[bool] = None
    developerWalletAddresses: List[str] = field(default_factory=list)
    xAccountRecycleCheck: Optional[XAccountRecycleCheck] = None
    websiteDomainAgeDays: Optional[int] = None

@dataclass
class MacdInfo:
    value: Optional[float] = None
    signal: Optional[float] = None
    histogram: Optional[float] = None
    state: Optional[str] = None # "BULLISH_DIVERGENCE", etc.

@dataclass
class TechnicalAnalysisSnapshot:
    priceUSD: Optional[float] = None
    emaCross_9_21: Optional[str] = None # "BULLISH_CROSS_RECENT", etc.
    rsi_14: Optional[float] = None
    macd: Optional[MacdInfo] = None
    chartPattern: Optional[str] = None # "EARLY_UPTREND", etc.

@dataclass
class WhaleActivitySnapshot:
    netBuyVolumeLast15MinUSD: Optional[float] = None
    distinctBuyingWhales: Optional[int] = None

@dataclass
class DexScreenerSpecific:
    boostScore: Optional[int] = None

@dataclass
class TokenSnapshot:
    tokenId: str
    timestampCollected: str
    source: str
    contractAddress: str
    ticker: str
    name: str
    profilePhotoUrl: Optional[str] = None
    origin: Optional[str] = None
    liquidityPool: Optional[str] = None
    bondingCurvePercent: Optional[float] = None
    devMigrations: Optional[int] = None
    links: Optional[LinkInfo] = None
    marketCap: Optional[float] = None
    liquidity: Optional[LiquidityInfo] = None
    volume: Optional[VolumeInfo] = None
    holders: Optional[HolderInfo] = None
    security: Optional[SecurityInfo] = None
    technicalAnalysis: Optional[TechnicalAnalysisSnapshot] = None # Snapshot, actual TA done on historical
    whaleActivity: Optional[WhaleActivitySnapshot] = None
    dexScreenerSpecific: Optional[DexScreenerSpecific] = None
    metaTags: List[str] = field(default_factory=list)
    solanaPriceUSD_atCollection: Optional[float] = None
    # These are added by the system, not directly from API typically
    historicalCandleData: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict) # e.g. {"1m": [candle_dict, ...]}
    transactionStream: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Candle:
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass
class SecurityCheckResult:
    token_id: str
    overall_status: str # "SAFE", "MODERATE_RISK", "HIGH_RISK", "SCAM_LIKELY"
    details: List[Dict[str, str]] = field(default_factory=list)

@dataclass
class TechnicalAnalysisResult:
    token_id: str
    ema_9_value: Optional[float] = None
    ema_21_value: Optional[float] = None
    ema_cross_state: Optional[str] = None # "BULLISH_CROSS", "BEARISH_CROSS", "NEUTRAL"
    rsi_14_value: Optional[float] = None
    rsi_state: Optional[str] = None # "OVERBOUGHT", "OVERSOLD", "NEUTRAL_RISING"
    macd_value: Optional[float] = None
    macd_signal_value: Optional[float] = None
    macd_histogram_value: Optional[float] = None
    macd_state: Optional[str] = None # "BULLISH_MOMENTUM", "BEARISH_MOMENTUM"
    identified_pattern: Optional[str] = None # "HOCKEY_STICK", "FLOOR_FORMATION"

@dataclass
class WhaleSummaryResult:
    token_id: str
    net_buy_volume_usd_15m: float = 0.0
    distinct_buying_whales_15m: int = 0

@dataclass
class BuySignal:
    token_id: str
    contract_address: str
    ticker: str
    strategy: str
    suggested_entry_price_range: Tuple[float, float]
    confidence_score: float # 0.0 to 1.0
    reasoning: List[str] = field(default_factory=list)

@dataclass
class SellSignal:
    token_id: str
    contract_address: str
    ticker: str
    strategy: str # or "TA_EXIT" / "STOP_LOSS"
    suggested_exit_price: float
    reasoning: List[str] = field(default_factory=list)
    sell_type: str # "TAKE_PROFIT_FULL", "TAKE_PROFIT_PARTIAL", "STOP_LOSS"
    partial_sell_percent: Optional[float] = None