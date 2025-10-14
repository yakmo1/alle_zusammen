#!/usr/bin/env python3
"""
Performance Reporter - Automatische Trefferquoten und Performance-Analyse
Implementiert tägliche Reports gemäß automation.instructions.md
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv

# Lokale Imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.postgresql_manager import PostgreSQLManager

load_dotenv()

class PerformanceReporter:
    """
    Automatischer Performance Reporter für Trading Bot
    - Tägliche Trefferquoten (profit vs loss trades)
    - Performance-Trends und Optimierungsvorschläge
    - ML-Model Performance Tracking
    """
    
    def __init__(self):
        self.db = PostgreSQLManager()
        self.output_dir = "reports"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_daily_performance_report(self, date: str = None) -> Dict:
        """
        Generiert täglichen Performance-Report
        
        Args:
            date: Datum im Format 'YYYY-MM-DD', default heute
            
        Returns:
            Dict mit Performance-Metriken
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"📊 Generiere Performance-Report für {date}...")
        
        # Trades für den Tag abrufen
        query = """
            SELECT 
                strategy_name,
                COUNT(*) as total_trades,
                SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN profit_loss <= 0 THEN 1 ELSE 0 END) as losing_trades,
                SUM(profit_loss) as total_profit_loss,
                AVG(profit_loss) as avg_profit_loss,
                AVG(confidence_score) as avg_confidence,
                MAX(profit_loss) as max_win,
                MIN(profit_loss) as max_loss
            FROM trades 
            WHERE DATE(close_time) = %s AND status = 'CLOSED'
            GROUP BY strategy_name
        """
        
        results = self.db.fetch_all(query, (date,))
        
        report = {
            'date': date,
            'strategies': {},
            'overall': {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_profit_loss': 0.0,
                'avg_profit_loss': 0.0
            }
        }
        
        # Strategien-spezifische Metriken
        for row in results:
            strategy_name = row[0]
            total_trades = row[1]
            winning_trades = row[2]
            losing_trades = row[3]
            total_pl = float(row[4] or 0)
            avg_pl = float(row[5] or 0)
            avg_confidence = float(row[6] or 0)
            max_win = float(row[7] or 0)
            max_loss = float(row[8] or 0)
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            report['strategies'][strategy_name] = {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': round(win_rate, 2),
                'total_profit_loss': round(total_pl, 2),
                'avg_profit_loss': round(avg_pl, 2),
                'avg_confidence': round(avg_confidence, 3),
                'max_win': round(max_win, 2),
                'max_loss': round(max_loss, 2),
                'risk_reward_ratio': round(abs(max_win/max_loss), 2) if max_loss != 0 else 0
            }
            
            # Overall Metriken aktualisieren
            report['overall']['total_trades'] += total_trades
            report['overall']['winning_trades'] += winning_trades
            report['overall']['losing_trades'] += losing_trades
            report['overall']['total_profit_loss'] += total_pl
        
        # Overall Win Rate berechnen
        if report['overall']['total_trades'] > 0:
            report['overall']['win_rate'] = round(
                report['overall']['winning_trades'] / report['overall']['total_trades'] * 100, 2
            )
            report['overall']['avg_profit_loss'] = round(
                report['overall']['total_profit_loss'] / report['overall']['total_trades'], 2
            )
        
        # Performance in DB speichern
        self._save_performance_to_db(report)
        
        return report
    
    def generate_weekly_trend_analysis(self) -> Dict:
        """Generiert 7-Tage Trend-Analyse"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        query = """
            SELECT 
                date,
                strategy_name,
                total_trades,
                winning_trades,
                win_rate,
                profit_loss,
                daily_return
            FROM performance_tracking 
            WHERE date >= %s AND date <= %s
            ORDER BY date DESC, strategy_name
        """
        
        results = self.db.fetch_all(query, (start_date.date(), end_date.date()))
        
        # Trend-Analyse
        df = pd.DataFrame(results, columns=[
            'date', 'strategy_name', 'total_trades', 'winning_trades', 
            'win_rate', 'profit_loss', 'daily_return'
        ])
        
        trend_analysis = {
            'period': f"{start_date.strftime('%Y-%m-%d')} bis {end_date.strftime('%Y-%m-%d')}",
            'strategies': {}
        }
        
        if not df.empty:
            for strategy in df['strategy_name'].unique():
                strategy_df = df[df['strategy_name'] == strategy].copy()
                
                if len(strategy_df) >= 2:
                    # Trend-Berechnung
                    win_rate_trend = np.polyfit(range(len(strategy_df)), strategy_df['win_rate'], 1)[0]
                    profit_trend = np.polyfit(range(len(strategy_df)), strategy_df['profit_loss'], 1)[0]
                    
                    trend_analysis['strategies'][strategy] = {
                        'avg_win_rate': round(strategy_df['win_rate'].mean(), 2),
                        'total_profit_loss': round(strategy_df['profit_loss'].sum(), 2),
                        'win_rate_trend': 'steigend' if win_rate_trend > 0 else 'fallend',
                        'profit_trend': 'steigend' if profit_trend > 0 else 'fallend',
                        'best_day': strategy_df.loc[strategy_df['win_rate'].idxmax(), 'date'].strftime('%Y-%m-%d'),
                        'worst_day': strategy_df.loc[strategy_df['win_rate'].idxmin(), 'date'].strftime('%Y-%m-%d')
                    }
        
        return trend_analysis
    
    def generate_optimization_recommendations(self, min_trades: int = 10) -> List[Dict]:
        """
        Generiert Optimierungsempfehlungen basierend auf Performance-Daten
        
        Args:
            min_trades: Mindestanzahl Trades für Analyse
            
        Returns:
            Liste von Optimierungsempfehlungen
        """
        
        # Letzte 30 Tage Performance
        query = """
            SELECT 
                strategy_name,
                AVG(win_rate) as avg_win_rate,
                SUM(total_trades) as total_trades,
                SUM(profit_loss) as total_profit,
                AVG(daily_return) as avg_daily_return,
                MAX(max_drawdown) as max_drawdown
            FROM performance_tracking 
            WHERE date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY strategy_name
            HAVING SUM(total_trades) >= %s
        """
        
        results = self.db.fetch_all(query, (min_trades,))
        
        recommendations = []
        
        for row in results:
            strategy_name = row[0]
            avg_win_rate = float(row[1] or 0)
            total_trades = row[2]
            total_profit = float(row[3] or 0)
            avg_daily_return = float(row[4] or 0)
            max_drawdown = float(row[5] or 0)
            
            # Optimierungslogik
            if avg_win_rate < 60:
                recommendations.append({
                    'strategy': strategy_name,
                    'type': 'WIN_RATE_LOW',
                    'priority': 'HIGH',
                    'message': f'Win-Rate ({avg_win_rate:.1f}%) unter Ziel (60%). ML-Model neu trainieren.',
                    'suggested_action': 'retrain_ml_model'
                })
            
            if total_profit < 0:
                recommendations.append({
                    'strategy': strategy_name,
                    'type': 'NEGATIVE_PROFIT',
                    'priority': 'CRITICAL',
                    'message': f'Negative Gesamtperformance ({total_profit:.2f}). Strategie überprüfen.',
                    'suggested_action': 'review_strategy_params'
                })
            
            if max_drawdown > 10:
                recommendations.append({
                    'strategy': strategy_name,
                    'type': 'HIGH_DRAWDOWN',
                    'priority': 'MEDIUM',
                    'message': f'Hoher Drawdown ({max_drawdown:.1f}%). Risk Management anpassen.',
                    'suggested_action': 'adjust_risk_management'
                })
            
            if avg_win_rate > 80:
                recommendations.append({
                    'strategy': strategy_name,
                    'type': 'EXCELLENT_PERFORMANCE',
                    'priority': 'INFO',
                    'message': f'Ausgezeichnete Performance ({avg_win_rate:.1f}%). Konfiguration dokumentieren.',
                    'suggested_action': 'document_config'
                })
        
        return recommendations
    
    def create_performance_visualization(self, days: int = 30) -> str:
        """
        Erstellt Performance-Visualisierung
        
        Args:
            days: Anzahl Tage für Analyse
            
        Returns:
            Pfad zur erstellten Grafik
        """
        
        # Daten abrufen
        query = """
            SELECT date, strategy_name, win_rate, profit_loss, total_trades
            FROM performance_tracking 
            WHERE date >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY date
        """
        
        results = self.db.fetch_all(query, (days,))
        
        if not results:
            print("⚠️ Keine Daten für Visualisierung verfügbar")
            return ""
        
        df = pd.DataFrame(results, columns=['date', 'strategy_name', 'win_rate', 'profit_loss', 'total_trades'])
        
        # Grafik erstellen
        plt.style.use('seaborn-v0_8')
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. Win Rate über Zeit
        for strategy in df['strategy_name'].unique():
            strategy_df = df[df['strategy_name'] == strategy]
            ax1.plot(strategy_df['date'], strategy_df['win_rate'], marker='o', label=strategy)
        
        ax1.set_title('Win Rate Entwicklung')
        ax1.set_ylabel('Win Rate (%)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. Profit/Loss über Zeit
        for strategy in df['strategy_name'].unique():
            strategy_df = df[df['strategy_name'] == strategy]
            ax2.plot(strategy_df['date'], strategy_df['profit_loss'].cumsum(), marker='o', label=strategy)
        
        ax2.set_title('Kumulativer Profit/Loss')
        ax2.set_ylabel('Profit/Loss')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. Trades pro Tag
        daily_trades = df.groupby('date')['total_trades'].sum()
        ax3.bar(daily_trades.index, daily_trades.values, alpha=0.7)
        ax3.set_title('Trades pro Tag')
        ax3.set_ylabel('Anzahl Trades')
        ax3.grid(True, alpha=0.3)
        
        # 4. Win Rate Distribution
        ax4.hist(df['win_rate'], bins=20, alpha=0.7, edgecolor='black')
        ax4.axvline(df['win_rate'].mean(), color='red', linestyle='--', label=f'Durchschnitt: {df["win_rate"].mean():.1f}%')
        ax4.set_title('Win Rate Verteilung')
        ax4.set_xlabel('Win Rate (%)')
        ax4.set_ylabel('Häufigkeit')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Grafik speichern
        filename = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def _save_performance_to_db(self, report: Dict):
        """Speichert Performance-Report in Datenbank"""
        
        for strategy_name, metrics in report['strategies'].items():
            query = """
                INSERT INTO performance_tracking 
                (date, strategy_name, total_trades, winning_trades, losing_trades, 
                 profit_loss, win_rate, daily_return)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (date, strategy_name) 
                DO UPDATE SET
                    total_trades = EXCLUDED.total_trades,
                    winning_trades = EXCLUDED.winning_trades,
                    losing_trades = EXCLUDED.losing_trades,
                    profit_loss = EXCLUDED.profit_loss,
                    win_rate = EXCLUDED.win_rate,
                    daily_return = EXCLUDED.daily_return
            """
            
            daily_return = (metrics['total_profit_loss'] / float(os.getenv('INITIAL_CAPITAL', 50000))) * 100
            
            self.db.execute_query(query, (
                report['date'],
                strategy_name,
                metrics['total_trades'],
                metrics['winning_trades'],
                metrics['losing_trades'],
                metrics['total_profit_loss'],
                metrics['win_rate'],
                round(daily_return, 4)
            ))
    
    def generate_full_report(self) -> Dict:
        """Generiert vollständigen Performance-Report"""
        
        print("📊 Generiere vollständigen Performance-Report...")
        
        # Täglicher Report
        daily_report = self.generate_daily_performance_report()
        
        # Wöchentlicher Trend
        weekly_trend = self.generate_weekly_trend_analysis()
        
        # Optimierungsempfehlungen
        recommendations = self.generate_optimization_recommendations()
        
        # Visualisierung erstellen
        chart_path = self.create_performance_visualization()
        
        full_report = {
            'generated_at': datetime.now().isoformat(),
            'daily_performance': daily_report,
            'weekly_trend': weekly_trend,
            'recommendations': recommendations,
            'chart_path': chart_path
        }
        
        # Report als JSON speichern
        report_filename = f"full_performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = os.path.join(self.output_dir, report_filename)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(full_report, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"✅ Vollständiger Report gespeichert: {report_path}")
        
        return full_report

def main():
    """Hauptfunktion für Performance-Reporting"""
    
    print("🚀 Starte Performance Reporter...")
    
    try:
        reporter = PerformanceReporter()
        
        # Vollständigen Report generieren
        report = reporter.generate_full_report()
        
        # Wichtige Metriken ausgeben
        print("\n📈 PERFORMANCE SUMMARY:")
        print("="*50)
        
        if report['daily_performance']['overall']['total_trades'] > 0:
            overall = report['daily_performance']['overall']
            print(f"Trades heute: {overall['total_trades']}")
            print(f"Win Rate: {overall['win_rate']}%")
            print(f"Profit/Loss: {overall['total_profit_loss']}")
            
            # Ziel-Check (60-70% Win Rate)
            if overall['win_rate'] >= 60:
                print("✅ Win Rate Ziel erreicht!")
            else:
                print("⚠️ Win Rate unter Ziel (60%)")
        else:
            print("ℹ️ Keine Trades heute")
        
        # Empfehlungen ausgeben
        if report['recommendations']:
            print(f"\n🔧 OPTIMIERUNGSEMPFEHLUNGEN ({len(report['recommendations'])}):")
            for rec in report['recommendations'][:3]:  # Top 3
                print(f"  {rec['priority']}: {rec['message']}")
        
        print("\n✅ Performance-Analyse abgeschlossen!")
        
    except Exception as e:
        print(f"❌ Fehler im Performance Reporter: {e}")

if __name__ == "__main__":
    main()
