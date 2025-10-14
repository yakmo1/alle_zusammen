"""
Performance Tracker
Überwacht und bewertet Trading Performance
"""

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
import json

from ..utils.logger import get_logger, log_exception
from ..utils.config_loader import get_config
from ..data.database_manager import get_database


class PerformanceTracker:
    """Trackt und analysiert Trading Performance"""

    def __init__(self, db_type: str = 'local'):
        """
        Initialisiert den Performance Tracker

        Args:
            db_type: Database Type
        """
        self.logger = get_logger(self.__class__.__name__)
        self.config = get_config()
        self.db = get_database(db_type)

    def calculate_trade_metrics(self, days: int = 30) -> Dict[str, Any]:
        """
        Berechnet Gesamt-Trade-Metriken

        Args:
            days: Anzahl Tage zurück

        Returns:
            Metrics Dictionary
        """
        try:
            query = """
                SELECT
                    COUNT(*) as total_trades,
                    COUNT(CASE WHEN exit_price > entry_price AND type = 'BUY' THEN 1
                               WHEN exit_price < entry_price AND type = 'SELL' THEN 1 END) as winning_trades,
                    COUNT(CASE WHEN exit_price < entry_price AND type = 'BUY' THEN 1
                               WHEN exit_price > entry_price AND type = 'SELL' THEN 1 END) as losing_trades,
                    AVG(CASE WHEN exit_price > entry_price AND type = 'BUY'
                             THEN (exit_price - entry_price) * volume
                             WHEN exit_price < entry_price AND type = 'SELL'
                             THEN (entry_price - exit_price) * volume
                             ELSE 0 END) as avg_win,
                    AVG(CASE WHEN exit_price < entry_price AND type = 'BUY'
                             THEN (entry_price - exit_price) * volume
                             WHEN exit_price > entry_price AND type = 'SELL'
                             THEN (exit_price - entry_price) * volume
                             ELSE 0 END) as avg_loss,
                    SUM(CASE WHEN exit_price > entry_price AND type = 'BUY'
                             THEN (exit_price - entry_price) * volume
                             WHEN exit_price < entry_price AND type = 'SELL'
                             THEN (entry_price - exit_price) * volume
                             ELSE 0 END) as gross_profit,
                    SUM(CASE WHEN exit_price < entry_price AND type = 'BUY'
                             THEN (entry_price - exit_price) * volume
                             WHEN exit_price > entry_price AND type = 'SELL'
                             THEN (exit_price - entry_price) * volume
                             ELSE 0 END) as gross_loss
                FROM trades
                WHERE status = 'CLOSED'
                  AND entry_time >= NOW() - INTERVAL '{days} days'
            """.format(days=days)

            result = self.db.fetch_dict(query)

            if not result or result['total_trades'] == 0:
                return self._empty_metrics()

            # Calculate derived metrics
            total_trades = int(result['total_trades'])
            winning_trades = int(result['winning_trades'] or 0)
            losing_trades = int(result['losing_trades'] or 0)
            gross_profit = float(result['gross_profit'] or 0)
            gross_loss = float(result['gross_loss'] or 0)
            avg_win = float(result['avg_win'] or 0)
            avg_loss = float(result['avg_loss'] or 0)

            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
            net_profit = gross_profit - gross_loss
            expectancy = (win_rate / 100 * avg_win) - ((100 - win_rate) / 100 * avg_loss)

            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'gross_profit': gross_profit,
                'gross_loss': gross_loss,
                'net_profit': net_profit,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'expectancy': expectancy,
                'period_days': days
            }

        except Exception as e:
            log_exception(self.logger, e, "Failed to calculate trade metrics")
            return self._empty_metrics()

    def calculate_drawdown(self, days: int = 30) -> Dict[str, Any]:
        """
        Berechnet Drawdown Metriken

        Args:
            days: Anzahl Tage zurück

        Returns:
            Drawdown Dictionary
        """
        try:
            # Get all closed trades
            query = """
                SELECT
                    entry_time,
                    CASE
                        WHEN exit_price > entry_price AND type = 'BUY'
                        THEN (exit_price - entry_price) * volume
                        WHEN exit_price < entry_price AND type = 'SELL'
                        THEN (entry_price - exit_price) * volume
                        WHEN exit_price < entry_price AND type = 'BUY'
                        THEN -((entry_price - exit_price) * volume)
                        WHEN exit_price > entry_price AND type = 'SELL'
                        THEN -((exit_price - entry_price) * volume)
                        ELSE 0
                    END as profit
                FROM trades
                WHERE status = 'CLOSED'
                  AND entry_time >= NOW() - INTERVAL '{days} days'
                ORDER BY entry_time ASC
            """.format(days=days)

            results = self.db.fetch_all_dict(query)

            if not results:
                return {'max_drawdown': 0, 'max_drawdown_pct': 0, 'recovery_time_days': 0}

            # Calculate cumulative profit
            cumulative = []
            running_total = 0

            for row in results:
                running_total += float(row['profit'])
                cumulative.append(running_total)

            # Calculate drawdown
            peak = cumulative[0]
            max_drawdown = 0
            max_drawdown_pct = 0

            for profit in cumulative:
                if profit > peak:
                    peak = profit
                else:
                    drawdown = peak - profit
                    drawdown_pct = (drawdown / peak * 100) if peak > 0 else 0
                    max_drawdown = max(max_drawdown, drawdown)
                    max_drawdown_pct = max(max_drawdown_pct, drawdown_pct)

            return {
                'max_drawdown': max_drawdown,
                'max_drawdown_pct': max_drawdown_pct,
                'current_equity_curve_length': len(cumulative),
                'peak_equity': peak
            }

        except Exception as e:
            log_exception(self.logger, e, "Failed to calculate drawdown")
            return {'max_drawdown': 0, 'max_drawdown_pct': 0}

    def calculate_sharpe_ratio(self, days: int = 30, risk_free_rate: float = 0.02) -> float:
        """
        Berechnet Sharpe Ratio

        Args:
            days: Anzahl Tage zurück
            risk_free_rate: Risk-free Rate (annualisiert)

        Returns:
            Sharpe Ratio
        """
        try:
            # Get daily returns
            query = """
                SELECT
                    DATE(entry_time) as trade_date,
                    SUM(CASE
                        WHEN exit_price > entry_price AND type = 'BUY'
                        THEN (exit_price - entry_price) * volume
                        WHEN exit_price < entry_price AND type = 'SELL'
                        THEN (entry_price - exit_price) * volume
                        WHEN exit_price < entry_price AND type = 'BUY'
                        THEN -((entry_price - exit_price) * volume)
                        WHEN exit_price > entry_price AND type = 'SELL'
                        THEN -((exit_price - entry_price) * volume)
                        ELSE 0
                    END) as daily_return
                FROM trades
                WHERE status = 'CLOSED'
                  AND entry_time >= NOW() - INTERVAL '{days} days'
                GROUP BY DATE(entry_time)
                ORDER BY trade_date
            """.format(days=days)

            results = self.db.fetch_all_dict(query)

            if len(results) < 2:
                return 0.0

            returns = [float(r['daily_return']) for r in results]

            # Calculate Sharpe Ratio
            mean_return = np.mean(returns)
            std_return = np.std(returns)

            if std_return == 0:
                return 0.0

            # Annualize (assuming 252 trading days)
            annualized_return = mean_return * 252
            annualized_std = std_return * np.sqrt(252)

            sharpe_ratio = (annualized_return - risk_free_rate) / annualized_std

            return float(sharpe_ratio)

        except Exception as e:
            log_exception(self.logger, e, "Failed to calculate Sharpe ratio")
            return 0.0

    def get_performance_by_symbol(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Performance pro Symbol

        Args:
            days: Anzahl Tage zurück

        Returns:
            Liste von Performance Dictionaries pro Symbol
        """
        try:
            query = """
                SELECT
                    symbol,
                    COUNT(*) as total_trades,
                    COUNT(CASE WHEN exit_price > entry_price AND type = 'BUY' THEN 1
                               WHEN exit_price < entry_price AND type = 'SELL' THEN 1 END) as winning_trades,
                    SUM(CASE
                        WHEN exit_price > entry_price AND type = 'BUY'
                        THEN (exit_price - entry_price) * volume
                        WHEN exit_price < entry_price AND type = 'SELL'
                        THEN (entry_price - exit_price) * volume
                        WHEN exit_price < entry_price AND type = 'BUY'
                        THEN -((entry_price - exit_price) * volume)
                        WHEN exit_price > entry_price AND type = 'SELL'
                        THEN -((exit_price - entry_price) * volume)
                        ELSE 0
                    END) as net_profit
                FROM trades
                WHERE status = 'CLOSED'
                  AND entry_time >= NOW() - INTERVAL '{days} days'
                GROUP BY symbol
                ORDER BY net_profit DESC
            """.format(days=days)

            results = self.db.fetch_all_dict(query)

            performance = []
            for row in results:
                total_trades = int(row['total_trades'])
                winning_trades = int(row['winning_trades'] or 0)
                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

                performance.append({
                    'symbol': row['symbol'],
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'win_rate': win_rate,
                    'net_profit': float(row['net_profit'] or 0)
                })

            return performance

        except Exception as e:
            log_exception(self.logger, e, "Failed to get performance by symbol")
            return []

    def save_daily_metrics(self, metrics: Dict[str, Any]):
        """
        Speichert tägliche Metriken

        Args:
            metrics: Metrics Dictionary
        """
        try:
            insert_sql = """
                INSERT INTO performance_metrics
                    (timestamp, metric_name, metric_value, period_days)
                VALUES
                    (%s, %s, %s, %s)
            """

            timestamp = datetime.now()
            period_days = metrics.get('period_days', 30)

            # Save each metric
            for key, value in metrics.items():
                if key != 'period_days' and isinstance(value, (int, float)):
                    self.db.execute(insert_sql, (
                        timestamp,
                        key,
                        float(value),
                        period_days
                    ))

            self.logger.info("Daily metrics saved to database")

        except Exception as e:
            log_exception(self.logger, e, "Failed to save daily metrics")

    def generate_performance_report(self, days: int = 30) -> Dict[str, Any]:
        """
        Generiert vollständigen Performance Report

        Args:
            days: Anzahl Tage zurück

        Returns:
            Report Dictionary
        """
        try:
            self.logger.info(f"Generating performance report for last {days} days...")

            # Calculate all metrics
            trade_metrics = self.calculate_trade_metrics(days)
            drawdown_metrics = self.calculate_drawdown(days)
            sharpe_ratio = self.calculate_sharpe_ratio(days)
            symbol_performance = self.get_performance_by_symbol(days)

            report = {
                'timestamp': datetime.now().isoformat(),
                'period_days': days,
                'trade_metrics': trade_metrics,
                'drawdown_metrics': drawdown_metrics,
                'sharpe_ratio': sharpe_ratio,
                'symbol_performance': symbol_performance,
                'summary': {
                    'status': self._get_status(trade_metrics, drawdown_metrics),
                    'recommendation': self._get_recommendation(trade_metrics, drawdown_metrics, sharpe_ratio)
                }
            }

            # Save metrics
            self.save_daily_metrics(trade_metrics)

            self.logger.info("Performance report generated successfully")
            return report

        except Exception as e:
            log_exception(self.logger, e, "Failed to generate performance report")
            return {'error': str(e)}

    def _get_status(self, trade_metrics: Dict, drawdown_metrics: Dict) -> str:
        """Bestimmt den Status basierend auf Metriken"""
        win_rate = trade_metrics.get('win_rate', 0)
        profit_factor = trade_metrics.get('profit_factor', 0)
        max_drawdown_pct = drawdown_metrics.get('max_drawdown_pct', 0)

        if win_rate >= 55 and profit_factor >= 1.5 and max_drawdown_pct < 10:
            return 'EXCELLENT'
        elif win_rate >= 50 and profit_factor >= 1.2 and max_drawdown_pct < 15:
            return 'GOOD'
        elif win_rate >= 45 and profit_factor >= 1.0 and max_drawdown_pct < 20:
            return 'ACCEPTABLE'
        else:
            return 'NEEDS_IMPROVEMENT'

    def _get_recommendation(
        self,
        trade_metrics: Dict,
        drawdown_metrics: Dict,
        sharpe_ratio: float
    ) -> str:
        """Gibt Empfehlung basierend auf Metriken"""
        win_rate = trade_metrics.get('win_rate', 0)
        profit_factor = trade_metrics.get('profit_factor', 0)
        max_drawdown_pct = drawdown_metrics.get('max_drawdown_pct', 0)

        if profit_factor < 1.0:
            return "Stop trading and review strategy - losing system"
        elif max_drawdown_pct > 20:
            return "Reduce position sizes - drawdown too high"
        elif win_rate < 45:
            return "Review entry criteria - win rate too low"
        elif sharpe_ratio < 0.5:
            return "Risk-adjusted returns too low - optimize strategy"
        else:
            return "Continue trading - performance is acceptable"

    def _empty_metrics(self) -> Dict[str, Any]:
        """Leere Metriken"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'gross_profit': 0.0,
            'gross_loss': 0.0,
            'net_profit': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0,
            'expectancy': 0.0
        }


if __name__ == "__main__":
    # Test
    print("=== Performance Tracker Test ===\n")

    tracker = PerformanceTracker()

    # Generate report
    print("Generating performance report...")
    report = tracker.generate_performance_report(days=30)

    if 'error' not in report:
        print("\nPerformance Report:")
        print(f"Period: {report['period_days']} days")
        print(f"\nTrade Metrics:")
        for key, value in report['trade_metrics'].items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")

        print(f"\nDrawdown Metrics:")
        for key, value in report['drawdown_metrics'].items():
            print(f"  {key}: {value:.2f}")

        print(f"\nSharpe Ratio: {report['sharpe_ratio']:.3f}")
        print(f"\nStatus: {report['summary']['status']}")
        print(f"Recommendation: {report['summary']['recommendation']}")
    else:
        print(f"\nError: {report['error']}")
