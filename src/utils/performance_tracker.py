"""
Performance Tracking und Reporting
Überwacht und bewertet die Trading-Performance
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
import matplotlib.pyplot as plt
import seaborn as sns
from database.db_manager import DatabaseManager

class PerformanceTracker:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        
    def update_daily_performance(self):
        """Aktualisiert die täglichen Performance-Metriken"""
        try:
            today = date.today()
            
            # Alle Strategien abrufen
            strategies = self.get_active_strategies()
            
            for strategy in strategies:
                metrics = self.calculate_daily_metrics(strategy, today)
                self.save_daily_metrics(strategy, today, metrics)
                
            logging.info(f"Performance-Metriken für {today} aktualisiert")
            
        except Exception as e:
            logging.error(f"Fehler beim Performance-Update: {e}")
    
    def get_active_strategies(self) -> List[str]:
        """Aktive Strategien aus der Datenbank abrufen"""
        try:
            cursor = self.db_manager.connection.cursor()
            cursor.execute("""
                SELECT DISTINCT strategy_name 
                FROM trading_history 
                WHERE strategy_name IS NOT NULL
            """)
            
            result = cursor.fetchall()
            cursor.close()
            
            return [row[0] for row in result if row[0]]
            
        except Exception as e:
            logging.error(f"Fehler beim Abrufen der Strategien: {e}")
            return []
    
    def calculate_daily_metrics(self, strategy: str, target_date: date) -> Dict[str, float]:
        """Berechnet Metriken für einen Tag und eine Strategie"""
        try:
            cursor = self.db_manager.connection.cursor()
            
            # Trades für den Tag abrufen
            cursor.execute("""
                SELECT ticket, profit, commission, swap, volume, 
                       open_price, close_price, open_time, close_time
                FROM trading_history 
                WHERE strategy_name = %s 
                AND DATE(open_time) = %s
                AND close_time IS NOT NULL
            """, (strategy, target_date))
            
            trades = cursor.fetchall()
            cursor.close()
            
            if not trades:
                return self.get_empty_metrics()
            
            # Metriken berechnen
            total_trades = len(trades)
            profits = [trade[1] for trade in trades if trade[1] is not None]
            
            winning_trades = len([p for p in profits if p > 0])
            losing_trades = len([p for p in profits if p < 0])
            
            gross_profit = sum([p for p in profits if p > 0])
            gross_loss = abs(sum([p for p in profits if p < 0]))
            net_profit = sum(profits)
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
            
            # Drawdown berechnen
            max_drawdown = self.calculate_max_drawdown(strategy, target_date)
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'gross_profit': gross_profit,
                'gross_loss': gross_loss,
                'net_profit': net_profit,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'max_drawdown': max_drawdown
            }
            
        except Exception as e:
            logging.error(f"Fehler bei der Metrik-Berechnung: {e}")
            return self.get_empty_metrics()
    
    def get_empty_metrics(self) -> Dict[str, float]:
        """Leere Metriken für Tage ohne Trades"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'gross_profit': 0,
            'gross_loss': 0,
            'net_profit': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'max_drawdown': 0
        }
    
    def calculate_max_drawdown(self, strategy: str, target_date: date) -> float:
        """Berechnet den maximalen Drawdown bis zum Zieldatum"""
        try:
            cursor = self.db_manager.connection.cursor()
            
            # Alle Trades bis zum Zieldatum
            cursor.execute("""
                SELECT profit, close_time
                FROM trading_history 
                WHERE strategy_name = %s 
                AND DATE(close_time) <= %s
                AND close_time IS NOT NULL
                ORDER BY close_time
            """, (strategy, target_date))
            
            trades = cursor.fetchall()
            cursor.close()
            
            if len(trades) < 2:
                return 0
            
            # Kumulativen Profit berechnen
            cumulative_profits = []
            running_total = 0
            
            for trade in trades:
                running_total += trade[0] if trade[0] else 0
                cumulative_profits.append(running_total)
            
            # Maximaler Drawdown
            peak = cumulative_profits[0]
            max_drawdown = 0
            
            for profit in cumulative_profits[1:]:
                if profit > peak:
                    peak = profit
                else:
                    drawdown = peak - profit
                    max_drawdown = max(max_drawdown, drawdown)
            
            return max_drawdown
            
        except Exception as e:
            logging.error(f"Fehler bei Drawdown-Berechnung: {e}")
            return 0
    
    def save_daily_metrics(self, strategy: str, target_date: date, metrics: Dict[str, float]):
        """Speichert die täglichen Metriken in der Datenbank"""
        try:
            cursor = self.db_manager.connection.cursor()
            
            cursor.execute("""
                INSERT INTO performance_metrics 
                (date, strategy_name, total_trades, winning_trades, losing_trades,
                 gross_profit, gross_loss, net_profit, win_rate, profit_factor, max_drawdown)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (date, strategy_name) DO UPDATE SET
                total_trades = %s, winning_trades = %s, losing_trades = %s,
                gross_profit = %s, gross_loss = %s, net_profit = %s,
                win_rate = %s, profit_factor = %s, max_drawdown = %s
            """, (
                target_date, strategy, metrics['total_trades'], metrics['winning_trades'],
                metrics['losing_trades'], metrics['gross_profit'], metrics['gross_loss'],
                metrics['net_profit'], metrics['win_rate'], metrics['profit_factor'],
                metrics['max_drawdown'],
                # UPDATE Werte
                metrics['total_trades'], metrics['winning_trades'], metrics['losing_trades'],
                metrics['gross_profit'], metrics['gross_loss'], metrics['net_profit'],
                metrics['win_rate'], metrics['profit_factor'], metrics['max_drawdown']
            ))
            
            cursor.close()
            
        except Exception as e:
            logging.error(f"Fehler beim Speichern der Metriken: {e}")
    
    def generate_daily_report(self) -> Dict[str, Any]:
        """Generiert einen täglichen Performance-Report"""
        try:
            today = date.today()
            yesterday = today - timedelta(days=1)
            
            cursor = self.db_manager.connection.cursor()
            
            # Heutige Performance
            cursor.execute("""
                SELECT strategy_name, total_trades, winning_trades, losing_trades,
                       net_profit, win_rate, profit_factor
                FROM performance_metrics 
                WHERE date = %s
            """, (today,))
            
            today_data = cursor.fetchall()
            
            # Gestrige Performance zum Vergleich
            cursor.execute("""
                SELECT strategy_name, net_profit, win_rate
                FROM performance_metrics 
                WHERE date = %s
            """, (yesterday,))
            
            yesterday_data = {row[0]: {'net_profit': row[1], 'win_rate': row[2]} 
                            for row in cursor.fetchall()}
            
            cursor.close()
            
            report = {
                'date': today.isoformat(),
                'strategies': {},
                'summary': {
                    'total_trades': 0,
                    'total_profit': 0,
                    'avg_win_rate': 0
                }
            }
            
            total_profit = 0
            win_rates = []
            total_trades = 0
            
            for row in today_data:
                strategy = row[0]
                data = {
                    'total_trades': row[1],
                    'winning_trades': row[2],
                    'losing_trades': row[3],
                    'net_profit': row[4],
                    'win_rate': row[5],
                    'profit_factor': row[6]
                }
                
                # Vergleich mit gestern
                if strategy in yesterday_data:
                    data['profit_change'] = row[4] - yesterday_data[strategy]['net_profit']
                    data['win_rate_change'] = row[5] - yesterday_data[strategy]['win_rate']
                
                report['strategies'][strategy] = data
                
                total_profit += row[4]
                total_trades += row[1]
                if row[5] > 0:
                    win_rates.append(row[5])
            
            # Summary
            report['summary']['total_trades'] = total_trades
            report['summary']['total_profit'] = total_profit
            report['summary']['avg_win_rate'] = np.mean(win_rates) if win_rates else 0
            
            return report
            
        except Exception as e:
            logging.error(f"Fehler beim Erstellen des Reports: {e}")
            return {'error': str(e)}
    
    def generate_performance_chart(self, strategy: str, days: int = 30) -> str:
        """Erstellt ein Performance-Chart für eine Strategie"""
        try:
            cursor = self.db_manager.connection.cursor()
            
            # Daten der letzten X Tage
            start_date = date.today() - timedelta(days=days)
            cursor.execute("""
                SELECT date, net_profit, win_rate, total_trades
                FROM performance_metrics 
                WHERE strategy_name = %s 
                AND date >= %s
                ORDER BY date
            """, (strategy, start_date))
            
            data = cursor.fetchall()
            cursor.close()
            
            if not data:
                return "Keine Daten verfügbar"
            
            df = pd.DataFrame(data, columns=['date', 'net_profit', 'win_rate', 'total_trades'])
            df['cumulative_profit'] = df['net_profit'].cumsum()
            
            # Chart erstellen
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            
            # Kumulativer Profit
            ax1.plot(df['date'], df['cumulative_profit'], linewidth=2, color='blue')
            ax1.set_title(f'{strategy} - Kumulativer Profit ({days} Tage)')
            ax1.set_ylabel('Profit')
            ax1.grid(True, alpha=0.3)
            
            # Win Rate
            ax2.bar(df['date'], df['win_rate'], alpha=0.7, color='green')
            ax2.set_title(f'{strategy} - Tägliche Win Rate')
            ax2.set_ylabel('Win Rate (%)')
            ax2.set_ylim(0, 100)
            ax2.grid(True, alpha=0.3)
            
            # Speichern
            chart_path = f"reports/{strategy}_performance_{days}d.png"
            os.makedirs("reports", exist_ok=True)
            plt.tight_layout()
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return chart_path
            
        except Exception as e:
            logging.error(f"Fehler beim Erstellen des Charts: {e}")
            return f"Fehler: {e}"
    
    def get_strategy_ranking(self) -> List[Dict[str, Any]]:
        """Ranking der Strategien nach Performance"""
        try:
            cursor = self.db_manager.connection.cursor()
            
            # Performance der letzten 30 Tage
            start_date = date.today() - timedelta(days=30)
            cursor.execute("""
                SELECT strategy_name,
                       SUM(total_trades) as total_trades,
                       SUM(winning_trades) as winning_trades,
                       SUM(net_profit) as total_profit,
                       AVG(win_rate) as avg_win_rate,
                       AVG(profit_factor) as avg_profit_factor
                FROM performance_metrics 
                WHERE date >= %s
                GROUP BY strategy_name
                ORDER BY total_profit DESC
            """, (start_date,))
            
            data = cursor.fetchall()
            cursor.close()
            
            ranking = []
            for i, row in enumerate(data, 1):
                ranking.append({
                    'rank': i,
                    'strategy': row[0],
                    'total_trades': row[1],
                    'winning_trades': row[2],
                    'total_profit': row[3],
                    'avg_win_rate': row[4],
                    'avg_profit_factor': row[5],
                    'win_rate_percent': (row[2] / row[1] * 100) if row[1] > 0 else 0
                })
            
            return ranking
            
        except Exception as e:
            logging.error(f"Fehler beim Erstellen des Rankings: {e}")
            return []
