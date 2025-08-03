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


class ContinuousNetworkMonitorService:
    """
    Background service for continuous network monitoring.
    
    This service demonstrates several important software engineering concepts:
    1. Background thread management
    2. Graceful shutdown handling
    3. Real-time data collection and processing
    4. Service-oriented architecture
    5. Data pipeline design
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
            
            # Calculate sleep time to maintain consistent interval
            loop_duration = time.time() - loop_start_time
            sleep_time = max(0, self.monitor_interval - loop_duration)
            
            # Use shutdown event for interruptible sleep
            if sleep_time > 0:
                self.shutdown_event.wait(sleep_time)
    
    def _collect_snapshot(self) -> Optional[MonitoringSnapshot]:
        """
        Collect a complete network monitoring snapshot.
        
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
            
            # 2. Get current bandwidth statistics
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
            
            # 4. Calculate connection quality (sample 2 devices max for performance)
            latencies = []
            packet_losses = []
            
            sample_devices = devices[:2] if devices else []
            for device in sample_devices:
                try:
                    # Quick quality check (only 2 ping samples for speed)
                    quality = self.network_monitor.monitor_device_connectivity(
                        device['ip'], samples=2
                    )
                    latencies.append(quality['avg_latency_ms'])
                    packet_losses.append(quality['packet_loss_percent'])
                except Exception:
                    # Skip devices that can't be reached quickly
                    continue
            
            # Calculate averages
            avg_latency = statistics.mean(latencies) if latencies else 0.0
            avg_packet_loss = statistics.mean(packet_losses) if packet_losses else 0.0
            
            # Determine overall quality
            overall_quality = self._calculate_overall_quality(avg_latency, avg_packet_loss, len(devices))
            
            # 5. Create snapshot
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
                active_interfaces=current_bandwidth_stats.get('interfaces', [])
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
        
        This creates a user-friendly dashboard that updates every second.
        """
        # Calculate uptime
        uptime = datetime.now() - self.start_time
        uptime_str = str(uptime).split('.')[0]  # Remove microseconds
        
        # Calculate success rate
        success_rate = (self.successful_measurements / self.measurement_count * 100) if self.measurement_count > 0 else 0
        
        # Clear the previous line and display current stats
        print(f"\r📊 {snapshot.timestamp.strftime('%H:%M:%S')} | "
              f"Devices: {snapshot.device_count:2d} | "
              f"↑{snapshot.total_upload_mbps:6.2f} Mbps | "
              f"↓{snapshot.total_download_mbps:6.2f} Mbps | "
              f"Quality: {snapshot.overall_quality:9s} | "
              f"Latency: {snapshot.avg_latency_ms:5.1f}ms | "
              f"Loss: {snapshot.avg_packet_loss:4.1f}% | "
              f"Uptime: {uptime_str} | "
              f"Success: {success_rate:5.1f}%", end="", flush=True)
    
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
        print(f"💾 Data snapshots collected: {len(self.snapshots)}")
        print(f"🗄️  Ready for database persistence!")
    
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
            'monitor_interval': self.monitor_interval
        }


def main():
    """
    Main function to run the continuous monitoring service.
    
    This provides a simple CLI interface to start the service.
    """
    print("🌐 Continuous Network Monitoring Service")
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