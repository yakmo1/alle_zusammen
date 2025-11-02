#!/usr/bin/env python3
"""
Live Order Decision Monitor - Real-time tracking of trading decisions
Erweitert das Ultimate Dashboard um Order-Decision-Tracking
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template_string, jsonify
import sqlite3
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import json
from order_decision_tracker import OrderDecisionTracker

app = Flask(__name__)

class LiveDecisionMonitor:
    def __init__(self):
        self.tracker = OrderDecisionTracker()
        
    def get_live_decision_data(self):
        """Get current decision data for dashboard"""
        try:
            # Get recent signals
            signals = self.tracker.get_recent_signals(hours=2)
            
            # Analyze each signal
            analyses = []
            for signal in signals:
                analysis = self.tracker.analyze_signal_decision(signal['symbol'], signal)
                analyses.append(analysis)
                
            # Get current trading conditions
            symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD']
            current_conditions = {}
            
            for symbol in symbols:
                current_conditions[symbol] = self.tracker.check_trading_conditions(symbol)
                
            return {
                'timestamp': datetime.now().isoformat(),
                'recent_analyses': analyses,
                'current_conditions': current_conditions,
                'account_info': self.tracker.get_account_info(),
                'risk_parameters': self.tracker.get_risk_parameters()
            }
            
        except Exception as e:
            return {'error': str(e)}

monitor = LiveDecisionMonitor()

@app.route('/decision_data')
def get_decision_data():
    """API endpoint for decision data"""
    return jsonify(monitor.get_live_decision_data())

@app.route('/decisions')
def decision_dashboard():
    """Order Decision Dashboard"""
    template = """
<!DOCTYPE html>
<html>
<head>
    <title>Order Decision Monitor</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0c1e1e 0%, #1a3333 100%);
            color: #00ff88;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(0, 255, 136, 0.1);
            border-radius: 15px;
            border: 1px solid #00ff88;
        }
        
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: rgba(0, 0, 0, 0.6);
            border: 1px solid #00ff88;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
        }
        
        .card h3 {
            color: #00ff88;
            margin-bottom: 15px;
            font-size: 1.2em;
            text-align: center;
        }
        
        .signal-item {
            background: rgba(0, 255, 136, 0.1);
            border: 1px solid #00ff88;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
        }
        
        .signal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .symbol {
            font-weight: bold;
            font-size: 1.1em;
            color: #ffffff;
        }
        
        .decision-approved {
            background: rgba(0, 255, 0, 0.2);
            color: #00ff00;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: bold;
        }
        
        .decision-rejected {
            background: rgba(255, 0, 0, 0.2);
            color: #ff0000;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: bold;
        }
        
        .conditions-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 10px;
        }
        
        .condition-item {
            display: flex;
            justify-content: space-between;
            padding: 5px;
            font-size: 0.9em;
        }
        
        .condition-ok {
            color: #00ff00;
        }
        
        .condition-fail {
            color: #ff0000;
        }
        
        .reasons {
            margin-top: 10px;
            padding: 10px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 5px;
        }
        
        .reason-item {
            margin: 5px 0;
            font-size: 0.9em;
        }
        
        .refresh-btn {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #00ff88;
            color: #000;
            border: none;
            padding: 10px 20px;
            border-radius: 25px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        
        .refresh-btn:hover {
            background: #00cc66;
            transform: scale(1.05);
        }
        
        .timestamp {
            text-align: center;
            color: #888;
            margin-bottom: 20px;
        }
        
        .loading {
            text-align: center;
            color: #00ff88;
            font-size: 1.2em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 ORDER DECISION MONITOR</h1>
            <p>Live-Tracking von Trading-Entscheidungen</p>
        </div>
        
        <button class="refresh-btn" onclick="loadData()">🔄 Aktualisieren</button>
        
        <div class="timestamp" id="timestamp"></div>
        
        <div id="content" class="loading">
            Lade Entscheidungsdaten...
        </div>
    </div>

    <script>
        let currentData = null;
        
        function loadData() {
            fetch('/decision_data')
                .then(response => response.json())
                .then(data => {
                    currentData = data;
                    renderData(data);
                })
                .catch(error => {
                    console.error('Error:', error);
                    document.getElementById('content').innerHTML = '<div class="loading">❌ Fehler beim Laden der Daten</div>';
                });
        }
        
        function renderData(data) {
            if (data.error) {
                document.getElementById('content').innerHTML = `<div class="loading">❌ Fehler: ${data.error}</div>`;
                return;
            }
            
            document.getElementById('timestamp').innerHTML = `Letzte Aktualisierung: ${new Date(data.timestamp).toLocaleString('de-DE')}`;
            
            let html = '';
            
            // Recent Signals Analysis
            if (data.recent_analyses && data.recent_analyses.length > 0) {
                html += '<div class="grid">';
                html += '<div class="card">';
                html += '<h3>📊 Aktuelle Signal-Analysen</h3>';
                
                data.recent_analyses.forEach(analysis => {
                    const decisionClass = analysis.decision === 'APPROVED' ? 'decision-approved' : 'decision-rejected';
                    const decisionEmoji = analysis.decision === 'APPROVED' ? '✅' : '❌';
                    
                    html += `
                        <div class="signal-item">
                            <div class="signal-header">
                                <span class="symbol">${analysis.symbol}</span>
                                <span class="${decisionClass}">${decisionEmoji} ${analysis.decision}</span>
                            </div>
                            <div>
                                <strong>Action:</strong> ${analysis.signal.action || 'N/A'} | 
                                <strong>Confidence:</strong> ${analysis.signal.confidence || 0}% | 
                                <strong>Preis:</strong> ${analysis.signal.price || 'N/A'}
                            </div>
                            <div class="reasons">
                                <strong>Entscheidungsgrund:</strong>
                                ${analysis.decision_reasons.map(reason => `<div class="reason-item">• ${reason}</div>`).join('')}
                            </div>
                        </div>
                    `;
                });
                
                html += '</div>';
                
                // Trading Conditions Summary
                html += '<div class="card">';
                html += '<h3>🎯 Trading Bedingungen</h3>';
                
                Object.entries(data.current_conditions).forEach(([symbol, conditions]) => {
                    html += `
                        <div class="signal-item">
                            <div class="symbol">${symbol}</div>
                            <div class="conditions-grid">
                                <div class="condition-item">
                                    <span>Symbol handelbar:</span>
                                    <span class="${conditions.symbol_tradeable ? 'condition-ok' : 'condition-fail'}">
                                        ${conditions.symbol_tradeable ? '✅' : '❌'}
                                    </span>
                                </div>
                                <div class="condition-item">
                                    <span>Markt offen:</span>
                                    <span class="${conditions.market_open ? 'condition-ok' : 'condition-fail'}">
                                        ${conditions.market_open ? '✅' : '❌'}
                                    </span>
                                </div>
                                <div class="condition-item">
                                    <span>Margin OK:</span>
                                    <span class="${conditions.sufficient_margin ? 'condition-ok' : 'condition-fail'}">
                                        ${conditions.sufficient_margin ? '✅' : '❌'}
                                    </span>
                                </div>
                                <div class="condition-item">
                                    <span>Position Limit:</span>
                                    <span class="${conditions.position_limit_ok ? 'condition-ok' : 'condition-fail'}">
                                        ${conditions.position_limit_ok ? '✅' : '❌'}
                                    </span>
                                </div>
                                <div class="condition-item">
                                    <span>Spread OK:</span>
                                    <span class="${conditions.spread_acceptable ? 'condition-ok' : 'condition-fail'}">
                                        ${conditions.spread_acceptable ? '✅' : '❌'}
                                    </span>
                                </div>
                                <div class="condition-item">
                                    <span>Korrelation OK:</span>
                                    <span class="${conditions.correlation_ok ? 'condition-ok' : 'condition-fail'}">
                                        ${conditions.correlation_ok ? '✅' : '❌'}
                                    </span>
                                </div>
                            </div>
                        </div>
                    `;
                });
                
                html += '</div>';
                html += '</div>';
                
                // Account and Risk Info
                html += '<div class="grid">';
                
                if (data.account_info) {
                    html += '<div class="card">';
                    html += '<h3>💰 Account Status</h3>';
                    html += `
                        <div class="condition-item">
                            <span>Balance:</span>
                            <span>${data.account_info.balance ? data.account_info.balance.toFixed(2) : 'N/A'} ${data.account_info.currency || ''}</span>
                        </div>
                        <div class="condition-item">
                            <span>Equity:</span>
                            <span>${data.account_info.equity ? data.account_info.equity.toFixed(2) : 'N/A'} ${data.account_info.currency || ''}</span>
                        </div>
                        <div class="condition-item">
                            <span>Free Margin:</span>
                            <span>${data.account_info.free_margin ? data.account_info.free_margin.toFixed(2) : 'N/A'} ${data.account_info.currency || ''}</span>
                        </div>
                        <div class="condition-item">
                            <span>Margin Level:</span>
                            <span class="${data.account_info.margin_level > 200 ? 'condition-ok' : 'condition-fail'}">
                                ${data.account_info.margin_level ? data.account_info.margin_level.toFixed(1) + '%' : 'N/A'}
                            </span>
                        </div>
                    `;
                    html += '</div>';
                }
                
                if (data.risk_parameters) {
                    html += '<div class="card">';
                    html += '<h3>⚠️ Risk Parameter</h3>';
                    html += `
                        <div class="condition-item">
                            <span>Max Risk per Trade:</span>
                            <span>${data.risk_parameters.max_risk_per_trade || 'N/A'}%</span>
                        </div>
                        <div class="condition-item">
                            <span>Max Daily Loss:</span>
                            <span>${data.risk_parameters.max_daily_loss || 'N/A'}%</span>
                        </div>
                        <div class="condition-item">
                            <span>Max Positions:</span>
                            <span>${data.risk_parameters.max_positions || 'N/A'}</span>
                        </div>
                        <div class="condition-item">
                            <span>Min Confidence:</span>
                            <span>${data.risk_parameters.min_confidence || 'N/A'}%</span>
                        </div>
                    `;
                    html += '</div>';
                }
                
                html += '</div>';
                
            } else {
                html += '<div class="card"><h3>ℹ️ Keine aktuellen Signale gefunden</h3><p>Warte auf neue Trading-Signale...</p></div>';
            }
            
            document.getElementById('content').innerHTML = html;
        }
        
        // Auto-refresh every 30 seconds
        setInterval(loadData, 30000);
        
        // Initial load
        loadData();
    </script>
</body>
</html>
    """
    return render_template_string(template)

if __name__ == '__main__':
    print("🔍 Order Decision Monitor gestartet...")
    print("📊 Dashboard verfügbar unter: http://localhost:5005/decisions")
    app.run(host='0.0.0.0', port=5005, debug=True)
