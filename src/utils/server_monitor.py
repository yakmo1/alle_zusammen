#!/usr/bin/env python3
"""
Server Resource Monitor - Überwacht CPU, RAM, Disk und Netzwerk
"""

import psutil
import os
import time
from datetime import datetime
from typing import Dict, Optional

class ServerMonitor:
    """System-Ressourcen Monitor für Trading Server"""
    
    def __init__(self):
        self.start_time = time.time()
    
    def get_cpu_info(self) -> Dict:
        """Holt CPU-Informationen"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            load_avg = None
            try:
                # Windows hat kein load average, aber wir können es simulieren
                if hasattr(os, 'getloadavg'):
                    load_avg = os.getloadavg()
                else:
                    # Für Windows: CPU-Auslastung über 1 Minute simulieren
                    load_avg = [cpu_percent / 100 * cpu_count]
            except:
                load_avg = [0]
            
            return {
                'usage_percent': cpu_percent,
                'cores': cpu_count,
                'frequency_current': cpu_freq.current if cpu_freq else 0,
                'frequency_max': cpu_freq.max if cpu_freq else 0,
                'load_average_1min': load_avg[0] if load_avg else 0
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_memory_info(self) -> Dict:
        """Holt Speicher-Informationen"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return {
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'used_gb': round(memory.used / (1024**3), 2),
                'usage_percent': memory.percent,
                'swap_total_gb': round(swap.total / (1024**3), 2),
                'swap_used_gb': round(swap.used / (1024**3), 2),
                'swap_percent': swap.percent
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_disk_info(self) -> Dict:
        """Holt Festplatten-Informationen"""
        try:
            disk_usage = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            # Für Windows: C:\ Drive checken
            if os.name == 'nt':
                disk_usage = psutil.disk_usage('C:\\')
            
            return {
                'total_gb': round(disk_usage.total / (1024**3), 2),
                'used_gb': round(disk_usage.used / (1024**3), 2),
                'free_gb': round(disk_usage.free / (1024**3), 2),
                'usage_percent': round((disk_usage.used / disk_usage.total) * 100, 2),
                'read_mb': round(disk_io.read_bytes / (1024**2), 2) if disk_io else 0,
                'write_mb': round(disk_io.write_bytes / (1024**2), 2) if disk_io else 0
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_network_info(self) -> Dict:
        """Holt Netzwerk-Informationen"""
        try:
            net_io = psutil.net_io_counters()
            
            return {
                'bytes_sent_mb': round(net_io.bytes_sent / (1024**2), 2),
                'bytes_recv_mb': round(net_io.bytes_recv / (1024**2), 2),
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv,
                'errors_in': net_io.errin,
                'errors_out': net_io.errout
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_process_info(self) -> Dict:
        """Holt Prozess-Informationen für Trading-relevante Anwendungen"""
        try:
            processes = []
            trading_processes = ['python', 'terminal64', 'MetaTrader', 'postgres']
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'create_time']):
                try:
                    if any(tp.lower() in proc.info['name'].lower() for tp in trading_processes):
                        processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cpu_percent': proc.info['cpu_percent'],
                            'memory_percent': round(proc.info['memory_percent'], 2),
                            'uptime_hours': round((time.time() - proc.info['create_time']) / 3600, 1)
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                'total_processes': len(list(psutil.process_iter())),
                'trading_processes': processes[:10]  # Top 10
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_system_uptime(self) -> Dict:
        """Holt System-Uptime"""
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            
            return {
                'uptime_days': days,
                'uptime_hours': hours,
                'uptime_minutes': minutes,
                'uptime_string': f"{days}d {hours}h {minutes}m",
                'boot_time': datetime.fromtimestamp(boot_time).strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_comprehensive_status(self) -> Dict:
        """Holt alle System-Informationen"""
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'cpu': self.get_cpu_info(),
            'memory': self.get_memory_info(),
            'disk': self.get_disk_info(),
            'network': self.get_network_info(),
            'processes': self.get_process_info(),
            'uptime': self.get_system_uptime()
        }
    
    def get_alert_status(self) -> Dict:
        """Prüft kritische System-Zustände"""
        alerts = []
        
        # CPU-Warnung
        cpu_info = self.get_cpu_info()
        if cpu_info.get('usage_percent', 0) > 85:
            alerts.append(f"🔴 HIGH CPU: {cpu_info['usage_percent']:.1f}%")
        elif cpu_info.get('usage_percent', 0) > 70:
            alerts.append(f"🟡 MODERATE CPU: {cpu_info['usage_percent']:.1f}%")
        
        # Memory-Warnung
        memory_info = self.get_memory_info()
        if memory_info.get('usage_percent', 0) > 85:
            alerts.append(f"🔴 HIGH MEMORY: {memory_info['usage_percent']:.1f}%")
        elif memory_info.get('usage_percent', 0) > 70:
            alerts.append(f"🟡 MODERATE MEMORY: {memory_info['usage_percent']:.1f}%")
        
        # Disk-Warnung
        disk_info = self.get_disk_info()
        if disk_info.get('usage_percent', 0) > 90:
            alerts.append(f"🔴 LOW DISK SPACE: {disk_info['usage_percent']:.1f}%")
        elif disk_info.get('usage_percent', 0) > 80:
            alerts.append(f"🟡 MODERATE DISK USAGE: {disk_info['usage_percent']:.1f}%")
        
        return {
            'alerts': alerts,
            'status': 'CRITICAL' if any('🔴' in alert for alert in alerts) 
                     else 'WARNING' if alerts 
                     else 'HEALTHY'
        }


def test_server_monitor():
    """Test-Funktion für Server Monitor"""
    monitor = ServerMonitor()
    
    print("🔍 SYSTEM RESOURCE MONITOR TEST")
    print("=" * 50)
    
    status = monitor.get_comprehensive_status()
    alerts = monitor.get_alert_status()
    
    print(f"📅 Timestamp: {status['timestamp']}")
    print(f"⚠️  System Status: {alerts['status']}")
    
    if alerts['alerts']:
        print("\n🚨 ALERTS:")
        for alert in alerts['alerts']:
            print(f"   {alert}")
    
    print(f"\n💻 CPU: {status['cpu']['usage_percent']:.1f}% ({status['cpu']['cores']} cores)")
    print(f"🧠 Memory: {status['memory']['usage_percent']:.1f}% ({status['memory']['used_gb']:.1f}GB / {status['memory']['total_gb']:.1f}GB)")
    print(f"💾 Disk: {status['disk']['usage_percent']:.1f}% ({status['disk']['free_gb']:.1f}GB free)")
    print(f"🌐 Network: ↑{status['network']['bytes_sent_mb']:.1f}MB ↓{status['network']['bytes_recv_mb']:.1f}MB")
    print(f"⏱️  Uptime: {status['uptime']['uptime_string']}")
    
    if status['processes']['trading_processes']:
        print(f"\n🔄 Trading Processes ({len(status['processes']['trading_processes'])}):")
        for proc in status['processes']['trading_processes'][:5]:
            print(f"   {proc['name']} (PID: {proc['pid']}, CPU: {proc['cpu_percent']:.1f}%, RAM: {proc['memory_percent']:.1f}%)")


if __name__ == "__main__":
    test_server_monitor()
