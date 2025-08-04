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
from datetime import datetime
from typing import Dict, List, Optional
import statistics
from dataclasses import dataclass

# Import our existing NetworkMonitor
from network_monitor import NetworkMonitor


@dataclass
class MonitoringSnapshot:
    """
    Data structure for a single monitoring snapshot.
    This represents all network data collected at one moment in time.
    """
    timestamp: datetime
    device_count: int
    devices: List[Dict]
    total_upload_mbps: float
    total_download_mbps: float
    total_usage_mb: float
    avg_latency_ms: float
    avg_packet_loss: float
    overall_quality: str
    active_interfaces: List[str]
    tested_device_ip: Optional[str] = None  # NEW: Track which device was tested


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
    
    def __init__(self, monitor_interval: float = 1.0):
        """
        Initialize the continuous monitoring service.
        
        Args:
            monitor_interval: Time between measurements in seconds (default: 1.0)
        """
        self.monitor_interval = monitor_interval
        self.network_monitor = NetworkMonitor()
        
        # Service state management
        self.is_running = False
        self.monitor_thread = None
        self.shutdown_event = threading.Event()
        
        # Data tracking
        self.snapshots = []
        self.last_bandwidth_stats = None
        self.device_cache = {}
        self.measurement_count = 0
        self.successful_measurements = 0
        
        # Performance tracking
        self.start_time = None
        self.last_device_discovery = None
        
        # Quality testing configuration
        self.enable_quality_testing = monitor_interval >= 0.5  # Only test quality if interval is reasonable
        self.quality_test_interval = max(5.0, monitor_interval * 5)  # Test quality less frequently
        self.last_quality_test = None
        
        # NEW: Round-robin device testing state
        self.quality_test_device_index = 0  # Track which device to test next
        self.last_tested_device_list = []   # Remember the device list from last quality test
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
        self.stop()
        sys.exit(0)
    
    def start(self) -> bool:
        """
        Start the continuous monitoring service.
        
        Returns:
            bool: True if service started successfully, False otherwise
        """
        if self.is_running:
            print("⚠️  Service is already running!")
            return False
        
        print("🚀 Starting Continuous Network Monitoring Service")
        print("="*60)
        print(f"📡 Network range: {self.network_monitor.network_range}")
        print(f"⏱️  Monitoring interval: {self.monitor_interval} seconds")
        print(f"💾 Data will be displayed in real-time terminal output")
        print(f"🔍 Connection quality testing: {'Enabled (Round-Robin)' if self.enable_quality_testing else 'Disabled (fast mode)'}")
        print("🛑 Press Ctrl+C to stop monitoring")
        print("="*60)
        
        # Initialize service state
        self.is_running = True
        self.start_time = datetime.now()
        self.measurement_count = 0
        self.successful_measurements = 0
        
        # Perform initial device discovery
        print("🔍 Performing initial device discovery...")
        try:
            devices = self.network_monitor.discover_devices()
            self.device_cache = {dev['ip']: dev for dev in devices}
            print(f"✅ Initial discovery complete: {len(devices)} devices found")
            self.last_device_discovery = time.time()
        except Exception as e:
            print(f"⚠️  Initial device discovery failed: {e}")
            self.device_cache = {}
            self.last_device_discovery = time.time()
        
        # Get initial bandwidth stats
        try:
            self.last_bandwidth_stats = self.network_monitor.get_bandwidth_stats()
            print("✅ Initial bandwidth baseline established")
        except Exception as e:
            print(f"⚠️  Could not establish bandwidth baseline: {e}")
            self.last_bandwidth_stats = None
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        print("\n📊 Real-time Monitoring Started:")
        print("-" * 80)
        
        # Wait a moment for first measurement to ensure status check passes
        time.sleep(0.1)
        
        return True
    
    def stop(self) -> bool:
        """
        Stop the continuous monitoring service gracefully.
        
        Returns:
            bool: True if service stopped successfully, False otherwise
        """
        if not self.is_running:
            print("⚠️  Service is not running!")
            return False
        
        print("\n🛑 Stopping monitoring service...")
        
        # Signal shutdown
        self.is_running = False
        self.shutdown_event.set()
        
        # Wait for monitor thread to finish
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
            if self.monitor_thread.is_alive():
                print("⚠️  Monitor thread did not shut down cleanly")
            else:
                print("✅ Monitor thread stopped cleanly")
        
        # Print final statistics
        self._print_final_stats()
        
        return True
    
    def _monitor_loop(self):
        """
        Main monitoring loop that runs in background thread.
        
        This loop continuously collects network data and displays it in real-time.
        It demonstrates proper thread management and error handling.
        """
        while self.is_running and not self.shutdown_event.is_set():
            loop_start_time = time.time()
            
            try:
                # Collect monitoring snapshot
                snapshot = self._collect_snapshot()
                
                if snapshot:
                    # Store snapshot for later database persistence
                    self.snapshots.append(snapshot)
                    
                    # Keep only last 1000 snapshots in memory (prevent memory leak)
                    if len(self.snapshots) > 1000:
                        self.snapshots = self.snapshots[-1000:]
                    
                    # Display real-time data
                    self._display_realtime_data(snapshot)
                    
                    self.successful_measurements += 1
                else:
                    print(f"⚠️  Failed to collect snapshot at {datetime.now().strftime('%H:%M:%S')}")
                
                self.measurement_count += 1
                
            except Exception as e:
                print(f"❌ Error in monitoring loop: {e}")
                self.measurement_count += 1
            
            # Calculate exact sleep time and ensure minimum interval
            loop_duration = time.time() - loop_start_time
            sleep_time = max(0.05, self.monitor_interval - loop_duration)  # Minimum 50ms sleep
            
            # Use shutdown event for interruptible sleep
            if sleep_time > 0:
                self.shutdown_event.wait(sleep_time)
    
    def _get_next_device_for_quality_test(self, devices: List[Dict]) -> Optional[Dict]:
        """
        Get the next device for quality testing using round-robin approach.
        
        This function implements round-robin device selection:
        1. If device list changed, reset to first device
        2. Otherwise, move to next device in sequence
        3. Wrap around to beginning when we reach the end
        
        Args:
            devices: Current list of discovered devices
            
        Returns:
            Device dictionary to test, or None if no devices available
        """
        if not devices:
            return None
        
        # Create a stable device list sorted by IP for consistent ordering
        sorted_devices = sorted(devices, key=lambda d: d['ip'])
        
        # Check if device list has changed significantly
        current_ips = [d['ip'] for d in sorted_devices]
        last_ips = [d['ip'] for d in self.last_tested_device_list]
        
        # If device list changed, reset to first device
        if current_ips != last_ips:
            print(f"\n🔄 Device list changed, resetting round-robin to first device")
            self.quality_test_device_index = 0
            self.last_tested_device_list = sorted_devices.copy()
        
        # Ensure index is within bounds (safety check)
        if self.quality_test_device_index >= len(sorted_devices):
            self.quality_test_device_index = 0
        
        # Get the device to test
        device_to_test = sorted_devices[self.quality_test_device_index]
        
        # Move to next device for next time (round-robin)
        self.quality_test_device_index = (self.quality_test_device_index + 1) % len(sorted_devices)
        
        return device_to_test
    
    def _collect_snapshot(self) -> Optional[MonitoringSnapshot]:
        """
        Collect a complete network monitoring snapshot.
        
        Enhanced with round-robin device quality testing.
        
        Returns:
            MonitoringSnapshot: Complete network state, or None if collection failed
        """
        try:
            current_time = time.time()
            snapshot_timestamp = datetime.now()
            
            # 1. Update device list every 30 seconds (expensive operation)
            if (self.last_device_discovery is None or 
                current_time - self.last_device_discovery > 30):
                
                try:
                    devices = self.network_monitor.discover_devices()
                    self.device_cache = {dev['ip']: dev for dev in devices}
                    self.last_device_discovery = current_time
                except Exception as e:
                    # Use cached devices if discovery fails
                    devices = list(self.device_cache.values())
            else:
                devices = list(self.device_cache.values())
            
            # 2. Get current bandwidth statistics (this is fast)
            current_bandwidth_stats = self.network_monitor.get_bandwidth_stats()
            
            # 3. Calculate bandwidth usage (if we have previous stats)
            upload_mbps = download_mbps = usage_mb = 0.0
            if self.last_bandwidth_stats:
                try:
                    usage = self.network_monitor.calculate_bandwidth_usage(
                        self.last_bandwidth_stats, 
                        current_bandwidth_stats
                    )
                    upload_mbps = usage.get('upload_rate_mbps', 0.0)
                    download_mbps = usage.get('download_rate_mbps', 0.0)
                    usage_mb = usage.get('total_usage_mb', 0.0)
                except Exception as e:
                    pass  # Keep default values
            
            # Update bandwidth baseline
            self.last_bandwidth_stats = current_bandwidth_stats
            
            # 4. ENHANCED: Round-robin connection quality testing
            avg_latency = 0.0
            avg_packet_loss = 0.0
            overall_quality = "Unknown"
            tested_device_ip = None
            
            # Only test quality if enabled and enough time has passed
            if (self.enable_quality_testing and 
                (self.last_quality_test is None or 
                 current_time - self.last_quality_test > self.quality_test_interval)):
                
                # Get next device using round-robin
                device_to_test = self._get_next_device_for_quality_test(devices)
                
                if device_to_test:
                    try:
                        print(f"\n🔍 Round-robin testing device: {device_to_test['ip']} "
                              f"({device_to_test.get('hostname', 'Unknown')})")
                        
                        # Quick quality check (only 1 ping sample for speed)
                        quality = self.network_monitor.monitor_device_connectivity(
                            device_to_test['ip'], samples=1
                        )
                        
                        avg_latency = quality['avg_latency_ms']
                        avg_packet_loss = quality['packet_loss_percent']
                        tested_device_ip = device_to_test['ip']
                        self.last_quality_test = current_time
                        
                        print(f"   📊 Results: {avg_latency:.1f}ms latency, {avg_packet_loss:.1f}% loss")
                        
                    except Exception as e:
                        print(f"   ⚠️ Quality test failed for {device_to_test['ip']}: {e}")
                        # Move to next device anyway
                        pass
                
                # Determine overall quality based on tested device
                overall_quality = self._calculate_overall_quality(avg_latency, avg_packet_loss, len(devices))
            else:
                # Use cached quality or basic estimation when not testing
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
        
        Quality factors:
        1. Average latency across sampled devices
        2. Average packet loss
        3. Network load (device count)
        """
        if avg_latency == 0:  # No devices to sample
            return "Unknown"
        
        # Base quality on latency and packet loss
        if avg_packet_loss > 5 or avg_latency > 100:
            base_quality = "Poor"
        elif avg_packet_loss > 2 or avg_latency > 50:
            base_quality = "Fair"
        elif avg_packet_loss > 0.5 or avg_latency > 25:
            base_quality = "Good"
        else:
            base_quality = "Excellent"
        
        # Adjust for network load
        if device_count > 10:
            if base_quality == "Excellent":
                base_quality = "Good"
            elif base_quality == "Good":
                base_quality = "Fair"
        
        return base_quality
    
    def _display_realtime_data(self, snapshot: MonitoringSnapshot):
        """
        Display real-time monitoring data in a formatted terminal output.
        
        Enhanced to show which device was tested in round-robin.
        """
        # Calculate uptime
        uptime = datetime.now() - self.start_time
        uptime_str = str(uptime).split('.')[0]  # Remove microseconds
        
        # Calculate success rate
        success_rate = (self.successful_measurements / self.measurement_count * 100) if self.measurement_count > 0 else 0
        
        # Enhanced display with tested device info
        tested_info = f" [Testing: {snapshot.tested_device_ip}]" if snapshot.tested_device_ip else ""
        
        # Clear the previous line and display current stats
        print(f"\r📊 {snapshot.timestamp.strftime('%H:%M:%S')} | "
              f"Devices: {snapshot.device_count:2d} | "
              f"↑{snapshot.total_upload_mbps:6.2f} Mbps | "
              f"↓{snapshot.total_download_mbps:6.2f} Mbps | "
              f"Quality: {snapshot.overall_quality:9s} | "
              f"Latency: {snapshot.avg_latency_ms:5.1f}ms | "
              f"Loss: {snapshot.avg_packet_loss:4.1f}% | "
              f"Uptime: {uptime_str} | "
              f"Success: {success_rate:5.1f}%{tested_info}", end="", flush=True)
    
    def _print_final_stats(self):
        """Print final statistics when service stops."""
        if not self.snapshots:
            print("\n📊 No data collected during this session")
            return
        
        # Calculate session statistics
        total_runtime = datetime.now() - self.start_time
        success_rate = (self.successful_measurements / self.measurement_count * 100) if self.measurement_count > 0 else 0
        
        # Data analysis
        total_upload = sum(s.total_upload_mbps for s in self.snapshots)
        total_download = sum(s.total_download_mbps for s in self.snapshots)
        avg_devices = statistics.mean(s.device_count for s in self.snapshots)
        
        latencies = [s.avg_latency_ms for s in self.snapshots if s.avg_latency_ms > 0]
        avg_latency = statistics.mean(latencies) if latencies else 0
        
        # NEW: Round-robin testing summary
        tested_devices = set(s.tested_device_ip for s in self.snapshots if s.tested_device_ip)
        
        print(f"\n\n📈 Final Session Statistics:")
        print("="*50)
        print(f"⏱️  Total runtime: {str(total_runtime).split('.')[0]}")
        print(f"📊 Total measurements: {self.measurement_count}")
        print(f"✅ Successful measurements: {self.successful_measurements}")
        print(f"📈 Success rate: {success_rate:.1f}%")
        print(f"📱 Average devices connected: {avg_devices:.1f}")
        print(f"⬆️  Total upload activity: {total_upload:.2f} Mbps-seconds")
        print(f"⬇️  Total download activity: {total_download:.2f} Mbps-seconds")
        print(f"🔍 Average network latency: {avg_latency:.1f}ms")
        print(f"🎯 Unique devices tested: {len(tested_devices)} devices")
        print(f"💾 Data snapshots collected: {len(self.snapshots)}")
        print(f"🗄️  Ready for database persistence!")
        
        if tested_devices:
            print(f"\n🔄 Round-robin tested devices:")
            for ip in sorted(tested_devices):
                print(f"   • {ip}")
    
    def get_recent_snapshots(self, count: int = 10) -> List[MonitoringSnapshot]:
        """
        Get the most recent monitoring snapshots.
        
        Args:
            count: Number of recent snapshots to return
            
        Returns:
            List of recent MonitoringSnapshot objects
        """
        return self.snapshots[-count:] if self.snapshots else []
    
    def get_service_status(self) -> Dict:
        """
        Get current service status and statistics.
        
        Returns:
            Dictionary with service status information
        """
        return {
            'is_running': self.is_running,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'measurement_count': self.measurement_count,
            'successful_measurements': self.successful_measurements,
            'success_rate': (self.successful_measurements / self.measurement_count * 100) if self.measurement_count > 0 else 0,
            'snapshots_collected': len(self.snapshots),
            'network_range': self.network_monitor.network_range,
            'monitor_interval': self.monitor_interval,
            'quality_testing_enabled': self.enable_quality_testing,
            'current_device_index': self.quality_test_device_index,
            'devices_in_rotation': len(self.last_tested_device_list)
        }


def main():
    """
    Main function to run the continuous monitoring service.
    
    This provides a simple CLI interface to start the service.
    """
    print("🌐 Continuous Network Monitoring Service (Round-Robin Enhanced)")
    print("=" * 50)
    
    # Create and start the service
    service = ContinuousNetworkMonitorService(monitor_interval=1.0)
    
    try:
        if service.start():
            # Keep the main thread alive while service runs
            while service.is_running:
                time.sleep(1)
        else:
            print("❌ Failed to start monitoring service")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Keyboard interrupt received")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    finally:
        service.stop()


if __name__ == "__main__":
    main() 