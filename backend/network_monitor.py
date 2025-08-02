import subprocess
import socket
import threading
import time
import json
from datetime import datetime
from typing import List, Dict, Optional
import ipaddress
import psutil
import ping3

class NetworkMonitor:
    """
    Core network monitoring class that handles device discovery and bandwidth tracking.
    
    This class implements several networking concepts:
    1. Network discovery through ping sweeps and ARP table analysis
    2. Bandwidth monitoring through system network interface statistics
    3. Connection quality measurement through ping latency testing
    """
    
    def __init__(self, network_range: str = None):
        """
        Initialize the network monitor.
        
        Args:
            network_range: Network CIDR (e.g., '192.168.1.0/24'). 
                          If None, will auto-detect local network.
        """
        self.network_range = network_range or self._get_local_network()
        self.devices = {}  # Store discovered devices
        self.monitoring = False
        self.monitoring_thread = None
        
    def _get_local_network(self) -> str:
        """
        Auto-detect the local network range.
        
        How this works:
        1. Get the default gateway (your router's IP)
        2. Get your device's IP address
        3. Calculate the network range (usually /24 for home networks)
        
        Returns:
            Network CIDR string (e.g., '192.168.1.0/24')
        """
        try:
            # Get default gateway (router IP)
            result = subprocess.run(['ip', 'route', 'show', 'default'], 
                                  capture_output=True, text=True)
            gateway = result.stdout.split()[2]
            
            # Get local IP
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect((gateway, 80))
            local_ip = sock.getsockname()[0]
            sock.close()
            
            # Calculate network (assuming /24 subnet)
            network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
            return str(network.network_address) + "/24"
            
        except Exception as e:
            # Fallback to common home network range
            print(f"Could not auto-detect network, using default: {e}")
            return "192.168.1.0/24"
    
    def discover_devices(self) -> List[Dict]:
        """
        Discover devices on the network using multiple methods.
        
        This implements a multi-pronged approach:
        1. Ping sweep: Tests connectivity to all IPs in range
        2. ARP table analysis: Checks which devices router knows about
        3. Port scanning: Identifies device types by open ports
        
        Returns:
            List of device dictionaries with IP, MAC, hostname, etc.
        """
        print(f"🔍 Scanning network range: {self.network_range}")
        discovered_devices = []
        
        # Method 1: Ping sweep
        network = ipaddress.IPv4Network(self.network_range)
        
        # Use threading for faster scanning
        threads = []
        results = []
        
        def ping_host(ip):
            """
            Ping a single host and collect info if responsive.
            
            Why ping works:
            - Every networked device responds to ICMP ping by default
            - Measures both connectivity and latency
            - Non-intrusive method that doesn't require special permissions
            """
            try:
                # ping3 returns response time in seconds, None if unreachable
                response_time = ping3.ping(str(ip), timeout=1)
                if response_time is not None:
                    device_info = {
                        'ip': str(ip),
                        'latency_ms': round(response_time * 1000, 2),
                        'status': 'online',
                        'last_seen': datetime.now().isoformat(),
                        'hostname': self._get_hostname(str(ip)),
                        'mac_address': self._get_mac_address(str(ip))
                    }
                    results.append(device_info)
                    print(f"✅ Found device: {ip} (latency: {device_info['latency_ms']}ms)")
            except Exception as e:
                pass  # Device not reachable
        
        # Create threads for parallel scanning (much faster than sequential)
        for ip in network.hosts():
            thread = threading.Thread(target=ping_host, args=(ip,))
            threads.append(thread)
            thread.start()
        
        # Wait for all ping threads to complete
        for thread in threads:
            thread.join(timeout=2)  # Don't wait forever
        
        discovered_devices.extend(results)
        
        # Method 2: ARP table analysis (gets MAC addresses of recently active devices)
        arp_devices = self._parse_arp_table()
        
        # Merge ARP data with ping results
        for device in discovered_devices:
            for arp_device in arp_devices:
                if device['ip'] == arp_device['ip']:
                    device.update(arp_device)
                    break
        
        self.devices = {dev['ip']: dev for dev in discovered_devices}
        print(f"🎯 Discovery complete: Found {len(discovered_devices)} devices")
        
        return discovered_devices
    
    def _get_hostname(self, ip: str) -> Optional[str]:
        """
        Try to resolve hostname from IP address.
        
        How DNS reverse lookup works:
        1. Queries DNS server for PTR record
        2. PTR records map IP addresses back to hostnames
        3. Many devices register hostnames like "iPhone-John" or "LAPTOP-ABC123"
        """
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except (socket.herror, socket.gaierror):
            return None
    
    def _get_mac_address(self, ip: str) -> Optional[str]:
        """
        Get MAC address for an IP using ARP protocol.
        
        ARP (Address Resolution Protocol) explanation:
        - Maps IP addresses to MAC (hardware) addresses
        - Your router maintains an ARP table of IP -> MAC mappings
        - MAC addresses are unique hardware identifiers
        - Useful for device identification and tracking
        """
        try:
            # Use system ARP command
            result = subprocess.run(['arp', '-n', ip], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if ip in line and 'incomplete' not in line:
                        parts = line.split()
                        # MAC address is typically in format xx:xx:xx:xx:xx:xx
                        for part in parts:
                            if ':' in part and len(part) == 17:
                                return part.upper()
        except Exception:
            pass
        return None
    
    def _parse_arp_table(self) -> List[Dict]:
        """
        Parse the system ARP table for device information.
        
        The ARP table contains:
        - IP addresses of recently communicated devices
        - Their corresponding MAC addresses
        - Interface information
        - Whether entries are complete or incomplete
        """
        devices = []
        try:
            result = subprocess.run(['arp', '-a'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if '(' in line and ')' in line and 'incomplete' not in line:
                    # Parse format: hostname (ip) at mac_address [ether] on interface
                    parts = line.split()
                    if len(parts) >= 4:
                        ip = parts[1].strip('()')
                        mac = parts[3] if len(parts) > 3 else None
                        hostname = parts[0] if parts[0] != '?' else None
                        
                        devices.append({
                            'ip': ip,
                            'mac_address': mac.upper() if mac else None,
                            'hostname': hostname,
                            'source': 'arp_table'
                        })
        except Exception as e:
            print(f"⚠️ Could not parse ARP table: {e}")
        
        return devices
    
    def get_bandwidth_stats(self, interface: str = None) -> Dict:
        """
        Get current bandwidth statistics for network interfaces.
        
        How bandwidth monitoring works:
        1. Read network interface statistics from the OS
        2. Track bytes sent/received over time
        3. Calculate rates by comparing measurements
        4. Monitor both individual interfaces and total network usage
        
        Args:
            interface: Specific interface to monitor (e.g., 'wlan0', 'eth0')
                      If None, monitors all interfaces
        
        Returns:
            Dictionary with bandwidth statistics
        """
        stats = psutil.net_io_counters(pernic=True)
        
        if interface and interface in stats:
            stat = stats[interface]
            return {
                'interface': interface,
                'bytes_sent': stat.bytes_sent,
                'bytes_recv': stat.bytes_recv,
                'packets_sent': stat.packets_sent,
                'packets_recv': stat.packets_recv,
                'errors_in': stat.errin,
                'errors_out': stat.errout,
                'drops_in': stat.dropin,
                'drops_out': stat.dropout,
                'timestamp': time.time()
            }
        else:
            # Return aggregated stats for all interfaces
            total_sent = sum(stat.bytes_sent for stat in stats.values())
            total_recv = sum(stat.bytes_recv for stat in stats.values())
            total_packets_sent = sum(stat.packets_sent for stat in stats.values())
            total_packets_recv = sum(stat.packets_recv for stat in stats.values())
            
            return {
                'interface': 'all',
                'bytes_sent': total_sent,
                'bytes_recv': total_recv,
                'packets_sent': total_packets_sent,
                'packets_recv': total_packets_recv,
                'timestamp': time.time(),
                'interfaces': list(stats.keys())
            }
    
    def calculate_bandwidth_usage(self, previous_stats: Dict, current_stats: Dict) -> Dict:
        """
        Calculate bandwidth usage rate between two measurements.
        
        Rate calculation explanation:
        1. Take two snapshots of network statistics
        2. Calculate the difference in bytes transferred
        3. Divide by time elapsed to get rate (bytes per second)
        4. Convert to human-readable units (Mbps, etc.)
        
        This is how most network monitoring tools work!
        """
        time_diff = current_stats['timestamp'] - previous_stats['timestamp']
        
        if time_diff <= 0:
            return {'error': 'Invalid time difference'}
        
        bytes_sent_diff = current_stats['bytes_sent'] - previous_stats['bytes_sent']
        bytes_recv_diff = current_stats['bytes_recv'] - previous_stats['bytes_recv']
        
        # Calculate rates in bytes per second
        upload_rate_bps = bytes_sent_diff / time_diff
        download_rate_bps = bytes_recv_diff / time_diff
        
        # Convert to more readable units
        upload_rate_mbps = (upload_rate_bps * 8) / (1024 * 1024)  # Convert to Mbps
        download_rate_mbps = (download_rate_bps * 8) / (1024 * 1024)
        
        return {
            'upload_rate_mbps': round(upload_rate_mbps, 2),
            'download_rate_mbps': round(download_rate_mbps, 2),
            'upload_rate_bps': round(upload_rate_bps, 2),
            'download_rate_bps': round(download_rate_bps, 2),
            'time_period_seconds': round(time_diff, 2),
            'total_usage_mb': round((bytes_sent_diff + bytes_recv_diff) / (1024 * 1024), 2)
        }
    
    def monitor_device_connectivity(self, ip: str, samples: int = 5) -> Dict:
        """
        Monitor connection quality to a specific device.
        
        Connection quality metrics:
        1. Latency: How long packets take to reach the device
        2. Packet loss: Percentage of packets that don't get responses
        3. Jitter: Variation in latency (important for real-time apps)
        
        These metrics help identify network problems and optimize performance.
        """
        latencies = []
        successful_pings = 0
        
        print(f"🔍 Testing connection quality to {ip} ({samples} samples)...")
        
        for i in range(samples):
            try:
                response_time = ping3.ping(ip, timeout=2)
                if response_time is not None:
                    latency_ms = response_time * 1000
                    latencies.append(latency_ms)
                    successful_pings += 1
                    print(f"  Ping {i+1}: {latency_ms:.2f}ms")
                else:
                    print(f"  Ping {i+1}: Timeout")
                time.sleep(0.5)  # Brief pause between pings
            except Exception as e:
                print(f"  Ping {i+1}: Error - {e}")
        
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            # Jitter calculation: standard deviation of latencies
            jitter = (sum((x - avg_latency) ** 2 for x in latencies) / len(latencies)) ** 0.5
        else:
            avg_latency = min_latency = max_latency = jitter = 0
        
        packet_loss = ((samples - successful_pings) / samples) * 100
        
        quality_rating = self._calculate_quality_rating(avg_latency, packet_loss, jitter)
        
        return {
            'ip': ip,
            'samples_sent': samples,
            'successful_pings': successful_pings,
            'packet_loss_percent': round(packet_loss, 2),
            'avg_latency_ms': round(avg_latency, 2),
            'min_latency_ms': round(min_latency, 2),
            'max_latency_ms': round(max_latency, 2),
            'jitter_ms': round(jitter, 2),
            'quality_rating': quality_rating,
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_quality_rating(self, latency: float, packet_loss: float, jitter: float) -> str:
        """
        Calculate a quality rating based on network metrics.
        
        Rating criteria (industry standard thresholds):
        - Excellent: <20ms latency, <1% loss, <5ms jitter
        - Good: <50ms latency, <3% loss, <10ms jitter  
        - Fair: <100ms latency, <5% loss, <20ms jitter
        - Poor: >100ms latency, >5% loss, >20ms jitter
        """
        if packet_loss > 5 or latency > 100 or jitter > 20:
            return "Poor"
        elif packet_loss > 3 or latency > 50 or jitter > 10:
            return "Fair"
        elif packet_loss > 1 or latency > 20 or jitter > 5:
            return "Good"
        else:
            return "Excellent"

# Example usage and testing functions
if __name__ == "__main__":
    """
    Demonstration of network monitoring capabilities.
    This shows how to use the NetworkMonitor class for basic operations.
    """
    
    print("🚀 Starting Network Monitor Demo")
    print("=" * 50)
    
    # Initialize the monitor
    monitor = NetworkMonitor()
    print(f"📡 Monitoring network: {monitor.network_range}")
    
    # Discover devices on the network
    devices = monitor.discover_devices()
    
    # Display discovered devices
    print("\n📱 Discovered Devices:")
    for device in devices:
        print(f"  IP: {device['ip']}")
        print(f"  Hostname: {device.get('hostname', 'Unknown')}")
        print(f"  MAC: {device.get('mac_address', 'Unknown')}")
        print(f"  Latency: {device.get('latency_ms', 'N/A')}ms")
        print("-" * 30)
    
    # Get initial bandwidth stats
    print("\n📊 Network Interface Statistics:")
    initial_stats = monitor.get_bandwidth_stats()
    print(f"  Total bytes sent: {initial_stats['bytes_sent']:,}")
    print(f"  Total bytes received: {initial_stats['bytes_recv']:,}")
    
    # Wait and get another measurement for rate calculation
    print("\n⏱️  Waiting 5 seconds for bandwidth measurement...")
    time.sleep(5)
    
    current_stats = monitor.get_bandwidth_stats()
    usage = monitor.calculate_bandwidth_usage(initial_stats, current_stats)
    
    print("📈 Bandwidth Usage (last 5 seconds):")
    print(f"  Upload rate: {usage['upload_rate_mbps']} Mbps")
    print(f"  Download rate: {usage['download_rate_mbps']} Mbps")
    print(f"  Total usage: {usage['total_usage_mb']} MB")
    
    # Test connection quality to first discovered device
    if devices:
        test_ip = devices[0]['ip']
        print(f"\n🔍 Testing connection quality to {test_ip}...")
        quality = monitor.monitor_device_connectivity(test_ip, samples=3)
        print(f"  Quality Rating: {quality['quality_rating']}")
        print(f"  Average Latency: {quality['avg_latency_ms']}ms")
        print(f"  Packet Loss: {quality['packet_loss_percent']}%")
        print(f"  Jitter: {quality['jitter_ms']}ms")
    
    
