"""
Signal Filter - Phase 3
Filters signals based on risk checks, market conditions, and quality criteria
"""

import MetaTrader5 as mt5
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple
import numpy as np

from src.utils.logger import get_logger
from src.data.database_manager import get_database

logger = get_logger('SignalFilter')


class SignalFilter:
    """Filters trading signals based on risk and quality criteria"""

    def __init__(self,
                 max_positions_per_symbol: int = 1,
                 max_total_positions: int = 3,
                 max_daily_loss: float = 500.0,
                 max_drawdown_pct: float = 10.0,
                 max_spread_pips: float = 2.0,
                 min_confidence: float = 0.70):
        """
        Initialize Signal Filter

        Args:
            max_positions_per_symbol: Max open positions per symbol
            max_total_positions: Max total open positions
            max_daily_loss: Max daily loss in account currency
            max_drawdown_pct: Max drawdown percentage
            max_spread_pips: Max spread in pips
            min_confidence: Minimum signal confidence
        """
        self.max_positions_per_symbol = max_positions_per_symbol
        self.max_total_positions = max_total_positions
        self.max_daily_loss = max_daily_loss
        self.max_drawdown_pct = max_drawdown_pct
        self.max_spread_pips = max_spread_pips
        self.min_confidence = min_confidence
        self.db = get_database('local')

        logger.info("Signal Filter initialized")
        logger.info(f"  Max positions per symbol: {max_positions_per_symbol}")
        logger.info(f"  Max total positions: {max_total_positions}")
        logger.info(f"  Max daily loss: ${max_daily_loss}")
        logger.info(f"  Max spread: {max_spread_pips} pips")

    def check_confidence(self, signal: Dict) -> Tuple[bool, str]:
        """Check if signal meets minimum confidence"""
        if signal['confidence'] < self.min_confidence:
            return False, f"Confidence {signal['confidence']:.2%} < {self.min_confidence:.2%}"
        return True, "Confidence OK"

    def check_position_limits(self, symbol: str) -> Tuple[bool, str]:
        """Check if position limits allow new position"""
        try:
            # Get all open positions
            positions = mt5.positions_get()
            if positions is None:
                logger.warning("Failed to get positions from MT5")
                return True, "Position check skipped (MT5 unavailable)"

            # Count positions per symbol
            symbol_positions = [p for p in positions if p.symbol == symbol]
            if len(symbol_positions) >= self.max_positions_per_symbol:
                return False, f"Max positions for {symbol}: {len(symbol_positions)}/{self.max_positions_per_symbol}"

            # Check total positions
            if len(positions) >= self.max_total_positions:
                return False, f"Max total positions: {len(positions)}/{self.max_total_positions}"

            return True, f"Positions OK ({len(positions)}/{self.max_total_positions})"

        except Exception as e:
            logger.error(f"Error checking position limits: {e}")
            return False, f"Position check error: {e}"

    def check_daily_loss_limit(self) -> Tuple[bool, str]:
        """Check if daily loss limit is reached"""
        try:
            # Get today's deals
            from datetime import date
            today = datetime.combine(date.today(), time.min)

            deals = mt5.history_deals_get(today, datetime.now())
            if deals is None:
                logger.warning("Failed to get deals from MT5")
                return True, "Daily loss check skipped (MT5 unavailable)"

            # Calculate today's P&L
            today_pnl = sum(deal.profit for deal in deals)

            if today_pnl < -self.max_daily_loss:
                return False, f"Daily loss limit: ${today_pnl:.2f} < -${self.max_daily_loss}"

            return True, f"Daily P&L: ${today_pnl:.2f}"

        except Exception as e:
            logger.error(f"Error checking daily loss: {e}")
            return False, f"Daily loss check error: {e}"

    def check_drawdown(self) -> Tuple[bool, str]:
        """Check if account drawdown is within limits"""
        try:
            account_info = mt5.account_info()
            if account_info is None:
                logger.warning("Failed to get account info from MT5")
                return True, "Drawdown check skipped (MT5 unavailable)"

            balance = account_info.balance
            equity = account_info.equity

            # Calculate drawdown
            if balance > 0:
                drawdown_pct = ((balance - equity) / balance) * 100
            else:
                drawdown_pct = 0.0

            if drawdown_pct > self.max_drawdown_pct:
                return False, f"Drawdown {drawdown_pct:.2f}% > {self.max_drawdown_pct}%"

            return True, f"Drawdown: {drawdown_pct:.2f}%"

        except Exception as e:
            logger.error(f"Error checking drawdown: {e}")
            return False, f"Drawdown check error: {e}"

    def check_spread(self, symbol: str) -> Tuple[bool, str]:
        """Check if spread is acceptable"""
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.warning(f"Failed to get tick for {symbol}")
                return True, "Spread check skipped (no tick data)"

            spread = tick.ask - tick.bid
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return True, "Spread check skipped (no symbol info)"

            point = symbol_info.point
            spread_pips = spread / point / 10  # Convert to pips

            if spread_pips > self.max_spread_pips:
                return False, f"Spread {spread_pips:.1f} pips > {self.max_spread_pips} pips"

            return True, f"Spread: {spread_pips:.1f} pips"

        except Exception as e:
            logger.error(f"Error checking spread: {e}")
            return False, f"Spread check error: {e}"

    def check_trading_session(self, symbol: str) -> Tuple[bool, str]:
        """Check if it's a good time to trade"""
        now = datetime.now()
        hour = now.hour

        # Avoid trading during:
        # - Asian session close (3-5 AM UTC)
        # - Weekend gaps (Friday 22:00 - Sunday 22:00 UTC)

        # For now, simple check: avoid low liquidity hours
        # TODO: Enhance with proper session detection per symbol

        if 3 <= hour <= 5:
            return False, "Low liquidity hours (3-5 AM UTC)"

        # Check if market is open
        if now.weekday() == 5:  # Saturday
            return False, "Market closed (Saturday)"
        if now.weekday() == 6 and hour < 22:  # Sunday before 22:00
            return False, "Market closed (Sunday)"

        return True, "Trading session OK"

    def check_correlation(self, symbol: str, signal_direction: str) -> Tuple[bool, str]:
        """
        Check if signal conflicts with existing positions due to correlation

        Args:
            symbol: Symbol to trade
            signal_direction: 'BUY' or 'SELL'

        Returns:
            (passes_check, reason)
        """
        try:
            # Highly correlated pairs
            correlations = {
                'EURUSD': ['GBPUSD'],
                'GBPUSD': ['EURUSD'],
                'AUDUSD': ['NZDUSD'],
                'NZDUSD': ['AUDUSD']
            }

            correlated_symbols = correlations.get(symbol, [])
            if not correlated_symbols:
                return True, "No correlation conflicts"

            # Get open positions
            positions = mt5.positions_get()
            if positions is None:
                return True, "Correlation check skipped (MT5 unavailable)"

            # Check for conflicting positions
            for pos in positions:
                if pos.symbol in correlated_symbols:
                    # Check if same direction (too correlated = too much risk)
                    pos_direction = 'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL'
                    if pos_direction == signal_direction:
                        return False, f"Correlation conflict: {pos.symbol} {pos_direction}"

            return True, "Correlation OK"

        except Exception as e:
            logger.error(f"Error checking correlation: {e}")
            return True, "Correlation check skipped (error)"

    def filter_signal(self, signal: Dict) -> Tuple[bool, List[str]]:
        """
        Apply all filters to a signal

        Args:
            signal: Signal dict to filter

        Returns:
            (passes_all_checks, list_of_reasons)
        """
        reasons = []
        passes = True

        # Run all checks
        checks = [
            self.check_confidence(signal),
            self.check_position_limits(signal['symbol']),
            self.check_daily_loss_limit(),
            self.check_drawdown(),
            self.check_spread(signal['symbol']),
            self.check_trading_session(signal['symbol']),
            self.check_correlation(signal['symbol'], signal['signal'])
        ]

        for check_pass, reason in checks:
            reasons.append(reason)
            if not check_pass:
                passes = False

        return passes, reasons

    def filter_signals(self, signals: List[Dict]) -> List[Dict]:
        """
        Filter a list of signals

        Args:
            signals: List of signals to filter

        Returns:
            List of signals that pass all filters
        """
        filtered_signals = []

        for signal in signals:
            if signal['signal'] == 'FLAT':
                continue

            passes, reasons = self.filter_signal(signal)

            if passes:
                logger.info(
                    f"Signal PASSED: {signal['symbol']} {signal['signal']} "
                    f"(confidence: {signal['confidence']:.2%})"
                )
                for reason in reasons:
                    logger.debug(f"  {reason}")
                filtered_signals.append(signal)
            else:
                logger.info(
                    f"Signal REJECTED: {signal['symbol']} {signal['signal']} "
                    f"(confidence: {signal['confidence']:.2%})"
                )
                for reason in reasons:
                    logger.info(f"  {reason}")

        logger.info(f"Filtered {len(filtered_signals)}/{len(signals)} signals")
        return filtered_signals
