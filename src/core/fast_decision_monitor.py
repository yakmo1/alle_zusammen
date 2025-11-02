#!/usr/bin/env python3
"""
Fast Order Decision Monitor - Optimized version for real-time tracking
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template_string, jsonify
import sqlite3
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import json

app = Flask(__name__)

def get_fast_signal_data():
    """Get recent signals with performance optimization"""
    try:
        conn = sqlite3.connect("trading_robot.db")
        
        # Get only the most recent 5 signals
        query = """
        SELECT timestamp, symbol, signal as action, confidence, entry_price as price, 
               stop_loss, take_profit
        FROM trading_signals 
        WHERE timestamp > datetime('now', '-1 hours')
        ORDER BY timestamp DESC 
        LIMIT 5
        """
        
        cursor = conn.cursor()
        cursor.execute(query)
        signals = cursor.fetchall()
        
        # Convert to list of dicts
        signal_data = []
        for signal in signals:
            signal_data.append({
                'timestamp': signal[0],
                'symbol': signal[1],
                'action': signal[2],
                'confidence': signal[3],  # Keep as decimal for correct comparison
                'confidence_percent': signal[3] * 100 if signal[3] <= 1 else signal[3],  # For display
                'price': signal[4],
                'stop_loss': signal[5],
                'take_profit': signal[6]
            })
        
        conn.close()
        return signal_data
        
    except Exception as e:
        print(f"Error getting signals: {e}")
        return []

def get_account_summary():
    """Get basic account info"""
    try:
        if not mt5.initialize():
            return None
            
        account_info = mt5.account_info()
        if account_info:
            margin_level = account_info.margin_level
            if margin_level == float('inf') or margin_level > 999999:
                margin_level = 999999  # Cap at a reasonable maximum
            return {
                'balance': account_info.balance,
                'equity': account_info.equity,
                'margin_level': margin_level
            }
    except:
        pass
    return None

@app.route('/api/signals')
def get_signals():
    """Fast API endpoint for recent signals"""
    signals = get_fast_signal_data()
    account = get_account_summary()
    
    return jsonify({
        'signals': signals,
        'account': account,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/fast')
def fast_dashboard():
    """Fast and simple decision dashboard"""
    template = """
<!DOCTYPE html>
<html>
<head>
    <title>Fast Order Monitor</title>
    <meta charset="utf-8">
    <style>
        body {
            font-family: 'Segoe UI', sans-serif;
            background: #0a0a0a;
            color: #00ff88;
            margin: 0;
            padding: 8px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 8px;
            padding: 8px;
            background: rgba(0, 255, 136, 0.1);
            border-radius: 5px;
            border: 1px solid #00ff88;
        }
        
        .card {
            background: rgba(0, 0, 0, 0.8);
            border: 1px solid #00ff88;
            border-radius: 5px;
            padding: 8px;
            margin-bottom: 8px;
        }
        
        .signal {
            background: rgba(0, 255, 136, 0.1);
            padding: 6px;
            margin: 4px 0;
            border-radius: 4px;
            border-left: 3px solid #00ff88;
        }
        
        .signal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;
        }
        
        .symbol {
            font-weight: bold;
            font-size: 1.1em;
            color: #ffffff;
        }
        
        .confidence-high {
            background: rgba(0, 255, 0, 0.3);
            color: #00ff00;
            padding: 2px 6px;
            border-radius: 3px;
        }
        
        .confidence-medium {
            background: rgba(255, 255, 0, 0.3);
            color: #ffff00;
            padding: 2px 6px;
            border-radius: 3px;
        }
        
        .confidence-low {
            background: rgba(255, 0, 0, 0.3);
            color: #ff6666;
            padding: 2px 6px;
            border-radius: 3px;
        }
        
        .details {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 6px;
            margin-top: 4px;
            font-size: 0.85em;
        }
        
        .status {
            text-align: center;
            padding: 4px;
            background: rgba(0, 255, 136, 0.1);
            border-radius: 3px;
        }
        
        .refresh-btn {
            position: fixed;
            top: 8px;
            right: 8px;
            background: #00ff88;
            color: #000;
            border: none;
            padding: 4px 8px;
            border-radius: 12px;
            cursor: pointer;
            font-weight: bold;
            font-size: 0.8em;
        }
        
        .timestamp {
            text-align: center;
            color: #888;
            margin-bottom: 8px;
            font-size: 0.8em;
        }
        
        .loading {
            text-align: center;
            color: #00ff88;
            font-size: 1.2em;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>⚡ FAST ORDER DECISION MONITOR</h1>
        <p>Optimierte Live-Verfolgung von Trading-Entscheidungen</p>
    </div>
    
    <button class="refresh-btn" onclick="loadData()">🔄 Refresh</button>
    
    <div class="timestamp" id="timestamp"></div>
    
    <div id="content" class="loading">
        Lade Daten...
    </div>

    <script>
        function loadData() {
            fetch('/api/signals')
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.text();
                })
                .then(text => {
                    try {
                        const data = JSON.parse(text);
                        renderData(data);
                    } catch (parseError) {
                        console.error('JSON Parse Error:', parseError);
                        console.error('Raw response:', text);
                        document.getElementById('content').innerHTML = `
                            <div class="loading">
                                ❌ JSON-Fehler beim Laden der Daten<br>
                                <small>Details in der Browser-Konsole (F12)</small><br>
                                <button onclick="loadData()" style="margin-top: 10px; padding: 5px 10px;">🔄 Erneut versuchen</button>
                            </div>
                        `;
                    }
                })
                .catch(error => {
                    console.error('Network Error:', error);
                    document.getElementById('content').innerHTML = `
                        <div class="loading">
                            ❌ Netzwerk-Fehler: ${error.message}<br>
                            <button onclick="loadData()" style="margin-top: 10px; padding: 5px 10px;">🔄 Erneut versuchen</button>
                        </div>
                    `;
                });
        }
        
        function renderData(data) {
            document.getElementById('timestamp').innerHTML = `Letzte Aktualisierung: ${new Date(data.timestamp).toLocaleString('de-DE')}`;
            
            let html = '';
            
            // Account Status
            if (data.account) {
                html += `
                    <div class="card">
                        <h3>💰 Account Status</h3>
                        <div class="details">
                            <div class="status">
                                <strong>Balance</strong><br>
                                ${data.account.balance ? data.account.balance.toFixed(2) : 'N/A'} USD
                            </div>
                            <div class="status">
                                <strong>Equity</strong><br>
                                ${data.account.equity ? data.account.equity.toFixed(2) : 'N/A'} USD
                            </div>
                            <div class="status">
                                <strong>Margin Level</strong><br>
                                ${data.account.margin_level ? data.account.margin_level.toFixed(1) + '%' : 'N/A'}
                            </div>
                        </div>
                    </div>
                `;
            }
            
            // Recent Signals
            html += '<div class="card"><h3>📊 Neueste Signale</h3>';
            
            if (data.signals && data.signals.length > 0) {
                data.signals.forEach(signal => {
                    const confidence = signal.confidence;
                    const confidence_display = signal.confidence_percent || (confidence * 100);
                    let confidenceClass = 'confidence-low';
                    if (confidence >= 0.70) confidenceClass = 'confidence-high';
                    else if (confidence >= 0.50) confidenceClass = 'confidence-medium';
                    
                    // Determine decision (using decimal values for comparison)
                    const decision = confidence >= 0.65 ? '✅ APPROVED' : '❌ REJECTED';
                    const reason = confidence >= 0.65 ? 'Alle Bedingungen erfüllt' : `Confidence ${confidence_display.toFixed(1)}% < 65% Minimum`;
                    
                    html += `
                        <div class="signal">
                            <div class="signal-header">
                                <span class="symbol">${signal.symbol}</span>
                                <span class="${confidenceClass}">${confidence_display.toFixed(1)}%</span>
                            </div>
                            <div class="details">
                                <div><strong>Action:</strong> ${signal.action}</div>
                                <div><strong>Price:</strong> ${signal.price}</div>
                                <div><strong>Decision:</strong> ${decision}</div>
                            </div>
                            <div style="margin-top: 4px; padding: 4px; background: rgba(0,0,0,0.3); border-radius: 3px; font-size: 0.75em;">
                                <strong>Grund:</strong> ${reason}<br>
                                <strong>Zeit:</strong> ${new Date(signal.timestamp).toLocaleString('de-DE')}
                            </div>
                        </div>
                    `;
                });
            } else {
                html += '<div class="status">Keine aktuellen Signale gefunden</div>';
            }
            
            html += '</div>';
            
            document.getElementById('content').innerHTML = html;
        }
        
        // Auto-refresh every 15 seconds
        setInterval(loadData, 15000);
        
        // Initial load
        loadData();
    </script>
</body>
</html>
    """
    return render_template_string(template)

if __name__ == '__main__':
    print("⚡ Fast Order Decision Monitor gestartet...")
    print("📊 Dashboard verfügbar unter: http://localhost:5006/fast")
    app.run(host='0.0.0.0', port=5006, debug=False)  # Debug off for better performance
