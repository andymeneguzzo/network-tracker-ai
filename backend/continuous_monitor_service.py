#!/usr/bin/env python3
"""
Continuous Network Monitoring Service

This service runs in the background and continuously monitors:
1. Network usage (bandwidth)
2. Number of connected devices
3. Overall connection quality

The service collects data every 1 second and displays real-time statistics
in the terminal. This data will later be saved to a SQLite database.

Usage:
    python continuous_monitor_service.py
"""

import threading
import time
import signal
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

# Add backend directory to path for imports
import sys
from pathlib import Path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from network_monitor import NetworkMonitor


@dataclass
class MonitoringSnapshot:
    """
    Data class representing a single monitoring snapshot.
    
    This structure contains all the monitoring metrics we collect
    and will be perfect for storing in our database later.
    """
    timestamp: str
    device_count: int
    devices: List[Dict[str, Any]]
    total_upload_mbps: float
    total_download_mbps: float
    total_usage_mb: float
    avg_latency_ms: float
    avg_packet_loss: float
    overall_quality: str
    active_interfaces: List[str]
    tested_device_ip: Optional[str] = None


class ContinuousNetworkMonitorService:
    """
    Background service for continuous network monitoring.
    
    This service demonstrates several important software engineering concepts:
    1. Background thread management
    2. Graceful shutdown handling
    3. Real-time data collection and processing
    4. Service-oriented architecture
    5. Data pipeline design
    6. Round-robin device testing for comprehensive coverage
    """
    
    def __init__(self, monitoring_interval: float = 1.0, quality_test_samples: int = 1):
        """
        Initialize the continuous monitoring service.
        
        Args:
            monitoring_interval: Time between monitoring cycles (seconds)
            quality_test_samples: Number of ping samples per device test
        """
        self.monitoring_interval = monitoring_interval
        self.quality_test_samples = quality_test_samples
        
        # Core monitoring components
        self.network_monitor = NetworkMonitor()
        
        # Service state management
        self.is_running = False
        self.monitor_thread = None
        self.start_time = None
        
        # Data collection and statistics
        self.snapshots: List[MonitoringSnapshot] = []
        self.device_cache: Dict[str, Dict[str, Any]] = {}
        self.measurement_count = 0
        self.successful_measurements = 0
        
        # Round-robin device testing
        self.device_test_index = 0
        self.tested_devices = set()
        
        # Thread safety for display
        self.display_lock = threading.Lock()
        self.last_display_length = 0
        self.suppress_quality_output = False
        
        # Setup graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signals gracefully."""
        print("\n🛑 Received shutdown signal...")
        self.stop()
        sys.exit(0)
    
    def _clear_line(self):
        """Clear the current terminal line completely."""
        # Get terminal width or use default
        try:
            terminal_width = os.get_terminal_size().columns
        except:
            terminal_width = 80
        
        # Clear the line by overwriting with spaces, then return to start
        print('\r' + ' ' * terminal_width + '\r', end='', flush=True)
    
    def _print_quality_message(self, message: str):
        """Print quality testing message without interfering with real-time display."""
        if not self.suppress_quality_output:
            with self.display_lock:
                self._clear_line()
                print(f"\n{message}")
    
    def start(self) -> bool:
        """
        Start the continuous monitoring service.
        
        Returns:
            True if service started successfully, False otherwise
        """
        if self.is_running:
            print("⚠️ Service is already running")
            return False
        
        print("🚀 Starting Continuous Network Monitoring Service")
        print("=" * 60)
        print(f"📡 Network range: {self.network_monitor.network_range}")
        print(f"⏱️  Monitoring interval: {self.monitoring_interval} seconds")
        print("💾 Data will be displayed in real-time terminal output")
        print("🔍 Connection quality testing: Enabled (Round-Robin)")
        print("🛑 Press Ctrl+C to stop monitoring")
        print("=" * 60)
        
        # Perform initial device discovery
        print("🔍 Performing initial device discovery...")
        initial_devices = self.network_monitor.discover_devices()
        
        if not initial_devices:
            print("❌ No devices found during initial discovery")
            print("💡 Check your network connection and try again")
            return False
        
        # Initialize device cache and round-robin
        self.device_cache = {dev['ip']: dev for dev in initial_devices}
        self.device_test_index = 0
        self.tested_devices.clear()
        
        print(f"✅ Initial discovery complete: {len(initial_devices)} devices found")
        
        # Get initial bandwidth baseline
        initial_bandwidth = self.network_monitor.get_bandwidth_stats()
        print("✅ Initial bandwidth baseline established")
        
        # Start monitoring thread
        self.is_running = True
        self.start_time = datetime.now()
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        print("\n📊 Real-time Monitoring Started:")
        
        return True
    
    def stop(self):
        """Stop the continuous monitoring service."""
        if not self.is_running:
            return
        
        print("\n🛑 Stopping monitoring service...")
        self.is_running = False
        
        # Wait for monitoring thread to finish
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
            print("✅ Monitor thread stopped cleanly")
        
        # Print final statistics
        self._print_final_stats()
    
    def _monitoring_loop(self):
        """
        Main monitoring loop that runs in a separate thread.
        
        This loop demonstrates:
        1. Continuous data collection
        2. Error handling and recovery
        3. Performance optimization
        4. Data aggregation and processing
        """
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.is_running:
            loop_start_time = time.time()
            
            try:
                # Collect monitoring snapshot
                snapshot = self._collect_monitoring_snapshot()
                
                if snapshot:
                    # Process and display the data
                    self._process_monitoring_data(snapshot)
                    consecutive_errors = 0  # Reset error counter on success
                else:
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"\n❌ Too many consecutive errors ({consecutive_errors}), stopping...")
                        self.is_running = False
                        break
                
            except Exception as e:
                consecutive_errors += 1
                print(f"\n⚠️ Monitoring error: {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    print(f"\n❌ Too many consecutive errors ({consecutive_errors}), stopping...")
                    self.is_running = False
                    break
            
            # Maintain precise timing
            loop_duration = time.time() - loop_start_time
            sleep_time = max(0, self.monitoring_interval - loop_duration)
            
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def _collect_monitoring_snapshot(self) -> Optional[MonitoringSnapshot]:
        """
        Collect a complete monitoring snapshot.
        
        This method demonstrates:
        1. Multi-source data collection
        2. Data validation and error handling
        3. Performance optimization
        4. Round-robin device testing strategy
        """
        try:
            snapshot_timestamp = datetime.now().isoformat()
            
            # 1. Device discovery (with caching for performance)
            devices = list(self.device_cache.values())  # Use cached devices primarily
            
            # Periodically refresh device list (every 30 seconds)
            if not hasattr(self, '_last_discovery') or \
               (datetime.now() - self._last_discovery).total_seconds() > 30:
                try:
                    fresh_devices = self.network_monitor.discover_devices()
                    if fresh_devices:
                        new_cache = {dev['ip']: dev for dev in fresh_devices}
                        
                        # Check if device list changed
                        if set(new_cache.keys()) != set(self.device_cache.keys()):
                            self._print_quality_message("🔄 Device list changed, resetting round-robin to first device")
                            self.device_test_index = 0
                            self.tested_devices.clear()
                        
                        self.device_cache = new_cache
                        devices = fresh_devices
                    self._last_discovery = datetime.now()
                except:
                    pass  # Use cached devices if discovery fails
            
            # 2. Bandwidth monitoring
            current_bandwidth_stats = self.network_monitor.get_bandwidth_stats()
            upload_mbps = current_bandwidth_stats.get('upload_mbps', 0.0)
            download_mbps = current_bandwidth_stats.get('download_mbps', 0.0)
            usage_mb = current_bandwidth_stats.get('total_usage_mb', 0.0)
            
            # 3. Round-robin connection quality testing
            tested_device_ip = None
            avg_latency = 0.0
            avg_packet_loss = 0.0
            
            if devices:
                # Select device for round-robin testing
                device_ips = list(self.device_cache.keys())
                if device_ips:
                    # Get current device for testing
                    current_device_ip = device_ips[self.device_test_index % len(device_ips)]
                    tested_device_ip = current_device_ip
                    
                    # Test connection quality for this device
                    latency_results = []
                    
                    self._print_quality_message(f"🔍 Testing connection quality to {current_device_ip} ({self.quality_test_samples} samples)...")
                    
                    for i in range(self.quality_test_samples):
                        try:
                            quality_result = self.network_monitor.monitor_device_connectivity(current_device_ip)
                            if quality_result and 'latency_ms' in quality_result:
                                latency_ms = quality_result['latency_ms']
                                latency_results.append(latency_ms)
                                self._print_quality_message(f"  Ping {i+1}: {latency_ms:.2f}ms")
                        except Exception as e:
                            self._print_quality_message(f"  Ping {i+1}: Failed ({e})")
                    
                    # Calculate averages
                    if latency_results:
                        avg_latency = sum(latency_results) / len(latency_results)
                        # Simple packet loss simulation (0% for successful pings)
                        successful_pings = len(latency_results)
                        total_pings = self.quality_test_samples
                        avg_packet_loss = ((total_pings - successful_pings) / total_pings) * 100
                    
                    # Add to tested devices set
                    self.tested_devices.add(current_device_ip)
                    
                    # Move to next device for next round
                    self.device_test_index += 1
            
            # 4. Overall quality assessment
            overall_quality = "Good"  # Default
            if avg_latency > 0:
                if avg_latency < 20 and avg_packet_loss < 1:
                    overall_quality = "Excellent"
                elif avg_latency < 50 and avg_packet_loss < 3:
                    overall_quality = "Good"
                elif avg_latency < 100 and avg_packet_loss < 10:
                    overall_quality = "Fair"
                else:
                    overall_quality = "Poor"
            else:
                # No active testing, base on device count
                if devices:
                    overall_quality = "Good" if len(devices) <= 10 else "Fair"
            
            # 5. Create snapshot with enhanced information
            snapshot = MonitoringSnapshot(
                timestamp=snapshot_timestamp,
                device_count=len(devices),
                devices=devices,
                total_upload_mbps=upload_mbps,
                total_download_mbps=download_mbps,
                total_usage_mb=usage_mb,
                avg_latency_ms=round(avg_latency, 2),
                avg_packet_loss=round(avg_packet_loss, 2),
                overall_quality=overall_quality,
                active_interfaces=current_bandwidth_stats.get('interfaces', []),
                tested_device_ip=tested_device_ip
            )
            
            return snapshot
            
        except Exception as e:
            return None
    
    def _calculate_overall_quality(self, avg_latency: float, avg_packet_loss: float, device_count: int) -> str:
        """
        Calculate overall network quality based on multiple factors.
        
        Uses industry-standard network quality metrics:
        - Excellent: <20ms latency, <1% loss, optimal device count
        - Good: <50ms latency, <3% loss, reasonable device count
        - Fair: <100ms latency, <10% loss, higher device count
        - Poor: >100ms latency or >10% loss or too many devices
        """
        # Base quality on latency and packet loss
        if avg_latency < 20 and avg_packet_loss < 1:
            base_quality = "Excellent"
        elif avg_latency < 50 and avg_packet_loss < 3:
            base_quality = "Good"
        elif avg_latency < 100 and avg_packet_loss < 10:
            base_quality = "Fair"
        else:
            base_quality = "Poor"
        
        # Adjust for device count (network congestion indicator)
        if device_count > 20:
            if base_quality == "Excellent":
                base_quality = "Good"
            elif base_quality == "Good":
                base_quality = "Fair"
        
        return base_quality
    
    def _process_monitoring_data(self, snapshot: MonitoringSnapshot):
        """
        Process and display monitoring data.
        
        This method demonstrates:
        1. Data processing and validation
        2. Real-time display management
        3. Statistics calculation
        4. Performance tracking
        """
        # Add to snapshots history
        self.snapshots.append(snapshot)
        self.measurement_count += 1
        
        # Determine if this was a successful measurement
        if snapshot.device_count > 0:
            self.successful_measurements += 1
        
        # Display real-time data
        self._display_realtime_data(snapshot)
    
    def _display_realtime_data(self, snapshot: MonitoringSnapshot):
        """Display real-time monitoring data in terminal."""
        with self.display_lock:
            # Calculate runtime and success rate
            runtime = datetime.now() - self.start_time
            success_rate = (self.successful_measurements / self.measurement_count * 100) if self.measurement_count > 0 else 0
            
            # Format runtime as HH:MM:SS
            total_seconds = int(runtime.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            uptime_str = f"{hours}:{minutes:02d}:{seconds:02d}"
            
            # Format tested device info
            tested_info = ""
            if snapshot.tested_device_ip:
                tested_info = f" [Testing: {snapshot.tested_device_ip}]"
            
            # Create status line
            timestamp = datetime.now().strftime("%H:%M:%S")
            status_line = (
                f"📊 {timestamp} | "
                f"Devices: {snapshot.device_count:2d} | "
                f"↑{snapshot.total_upload_mbps:6.2f} Mbps | "
                f"↓{snapshot.total_download_mbps:6.2f} Mbps | "
                f"Quality: {snapshot.overall_quality:9s} | "
                f"Latency: {snapshot.avg_latency_ms:5.1f}ms | "
                f"Loss: {snapshot.avg_packet_loss:4.1f}% | "
                f"Uptime: {uptime_str} | "
                f"Success: {success_rate:5.1f}%{tested_info}"
            )
            
            # Clear the line completely and display new status
            self._clear_line()
            print(f"\r{status_line}", end='', flush=True)
            
            # Store the length for future clearing
            self.last_display_length = len(status_line)
    
    def _print_final_stats(self):
        """Print final statistics when service stops."""
        if not self.snapshots:
            print("\n📊 No data collected during this session")
            return
        
        # Calculate session statistics
        total_runtime = datetime.now() - self.start_time
        success_rate = (self.successful_measurements / self.measurement_count * 100) if self.measurement_count > 0 else 0
        
        # Data analysis
        avg_devices = sum(s.device_count for s in self.snapshots) / len(self.snapshots)
        total_upload = sum(s.total_upload_mbps for s in self.snapshots)
        total_download = sum(s.total_download_mbps for s in self.snapshots)
        avg_latency = sum(s.avg_latency_ms for s in self.snapshots) / len(self.snapshots)
        
        print("\n\n📈 Final Session Statistics:")
        print("=" * 50)
        print(f"⏱️  Total runtime: {total_runtime}")
        print(f"📊 Total measurements: {self.measurement_count}")
        print(f"✅ Successful measurements: {self.successful_measurements}")
        print(f"📈 Success rate: {success_rate:.1f}%")
        print(f"📱 Average devices connected: {avg_devices:.1f}")
        print(f"⬆️  Total upload activity: {total_upload:.2f} Mbps-seconds")
        print(f"⬇️  Total download activity: {total_download:.2f} Mbps-seconds")
        print(f"🔍 Average network latency: {avg_latency:.1f}ms")
        print(f"🎯 Unique devices tested: {len(self.tested_devices)} devices")
        print(f"💾 Data snapshots collected: {len(self.snapshots)}")
        print("🗄️  Ready for database persistence!")
        
        if self.tested_devices:
            print("\n🔄 Round-robin tested devices:")
            for device_ip in sorted(self.tested_devices):
                print(f"   • {device_ip}")


def main():
    """
    Main entry point for the continuous monitoring service.
    
    This demonstrates:
    1. Service initialization and configuration
    2. Error handling and graceful shutdown
    3. User interaction and control
    """
    print("🌐 Network Monitoring Service")
    print("============================")
    
    # Create and configure the service
    service = ContinuousNetworkMonitorService(
        monitoring_interval=1.0,  # 1 second intervals
        quality_test_samples=1    # 1 ping per device test (faster)
    )
    
    try:
        # Start the service
        if not service.start():
            print("❌ Failed to start monitoring service")
            return 1
        
        # Keep the main thread alive while service runs
        try:
            while service.is_running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n🛑 Received interrupt signal...")
        
    except Exception as e:
        print(f"\n❌ Service error: {e}")
        return 1
    
    finally:
        # Ensure service is stopped
        service.stop()
    
    print("👋 Service stopped. Thank you for using Network Monitor!")
    return 0


if __name__ == "__main__":
    exit(main()) 