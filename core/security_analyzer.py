# core/security_analyzer.py
from typing import List, Dict, Tuple
from core.models import TokenSnapshot, SecurityCheckResult, SecurityInfo

class SecurityAnalyzer:
    def __init__(self, config: Dict):
        self.max_top_holder_percent = config.get("sec_max_top_holder_percent", 15.0)
        self.max_dev_holdings_percent = config.get("sec_max_dev_holdings_percent", 1.0) # Allow small for error margin
        self.max_total_bundled_percent = config.get("sec_max_total_bundled_percent", 8.0)
        # Add more config as needed

    def _add_result(self, details_list: List, check_name: str, status: str, reason: str):
        details_list.append({"check": check_name, "status": status, "reason": reason})

    def analyze(self, token: TokenSnapshot) -> SecurityCheckResult:
        details: List[Dict[str, str]] = []
        critical_failures = 0
        high_risk_flags = 0
        warnings = 0

        if not token.security:
            self._add_result(details, "Overall Security Data", "FAIL_CRITICAL", "Security data missing for token.")
            return SecurityCheckResult(token.tokenId, "SCAM_LIKELY", details)

        sec_info: SecurityInfo = token.security

        # Mint Authority
        if sec_info.mintAuthorityDisabled is False: # Explicitly False
            self._add_result(details, "Mint Authority", "FAIL_CRITICAL", "Mint authority is ENABLED.")
            critical_failures += 1
        else:
            self._add_result(details, "Mint Authority", "PASS", "Mint authority disabled.")

        # Freeze Authority
        if sec_info.freezeAuthorityDisabled is False: # Explicitly False
            self._add_result(details, "Freeze Authority", "FAIL_CRITICAL", "Freeze authority is ENABLED (Honeypot risk).")
            critical_failures += 1
        else:
            self._add_result(details, "Freeze Authority", "PASS", "Freeze authority disabled.")

        # LP Burned/Locked
        # This needs more nuance based on origin (Pump.fun vs Radium direct)
        if token.liquidity and token.liquidity.lpBurnedPercent is not None:
            if token.liquidity.lpBurnedPercent < 99.0: # Pump.fun tokens should be 100% after migration
                 # For non-pump.fun, you'd check if LP is locked if not burned (more complex)
                self._add_result(details, "LP Burn", "FAIL_HIGH_RISK", f"LP Burned: {token.liquidity.lpBurnedPercent}% (Should be >99% for migrated Pump.fun).")
                high_risk_flags +=1
            else:
                self._add_result(details, "LP Burn", "PASS", f"LP Burned: {token.liquidity.lpBurnedPercent}%.")
        else:
            self._add_result(details, "LP Burn", "WARNING", "LP Burn information missing or not applicable.")
            warnings +=1


        # Top Holders
        if token.holders and token.holders.top10HolderPercent is not None:
            if token.holders.top10HolderPercent > self.max_top_holder_percent:
                self._add_result(details, "Top 10 Holders", "FAIL_HIGH_RISK", f"Top 10 holders own {token.holders.top10HolderPercent}%. Limit: {self.max_top_holder_percent}%.")
                high_risk_flags += 1
            else:
                self._add_result(details, "Top 10 Holders", "PASS", f"Top 10 holders own {token.holders.top10HolderPercent}%.")
        else:
            self._add_result(details, "Top 10 Holders", "WARNING", "Top 10 holder information missing.")
            warnings += 1

        # Dev Holdings
        if sec_info.devHoldingsPercent is not None:
            if sec_info.devHoldingsPercent > self.max_dev_holdings_percent:
                self._add_result(details, "Dev Holdings", "WARNING", f"Dev holds {sec_info.devHoldingsPercent}%. Limit: {self.max_dev_holdings_percent}%.")
                warnings +=1 # Could be high risk depending on context
            else:
                 self._add_result(details, "Dev Holdings", "PASS", f"Dev holds {sec_info.devHoldingsPercent}%.")
        else:
            self._add_result(details, "Dev Holdings", "INFO", "Dev holdings info not available or 0%.")


        # Bundler Analysis
        if sec_info.bundlerAnalysis:
            ba = sec_info.bundlerAnalysis
            if ba.totalBundledPercent is not None and ba.totalBundledPercent > self.max_total_bundled_percent:
                self._add_result(details, "Bundled Supply", "FAIL_HIGH_RISK", f"Total bundled supply is {ba.totalBundledPercent}%. Limit: {self.max_total_bundled_percent}%.")
                high_risk_flags += 1
            elif ba.totalBundledPercent is not None:
                 self._add_result(details, "Bundled Supply", "PASS", f"Total bundled supply is {ba.totalBundledPercent}%.")

            if ba.freshWalletBundles:
                self._add_result(details, "Fresh Wallet Bundles", "WARNING", "Fresh wallets involved in bundling detected.")
                warnings += 1
            else:
                self._add_result(details, "Fresh Wallet Bundles", "INFO", "No significant fresh wallet bundling detected.")
        else:
            self._add_result(details, "Bundler Analysis", "INFO", "Bundler analysis data not available.")

        # Copycat
        if sec_info.isCopycat:
            self._add_result(details, "Copycat Check", "FAIL_HIGH_RISK", "Token identified as a potential copycat.")
            high_risk_flags += 1
        else:
            self._add_result(details, "Copycat Check", "PASS", "Token does not appear to be a copycat.")

        # --- Determine Overall Status ---
        overall_status = "SAFE"
        if critical_failures > 0:
            overall_status = "SCAM_LIKELY"
        elif high_risk_flags > 0:
            overall_status = "HIGH_RISK"
        elif warnings > 0:
            overall_status = "MODERATE_RISK"

        return SecurityCheckResult(token.tokenId, overall_status, details)