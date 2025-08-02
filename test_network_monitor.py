#!/usr/bin/env python3
"""
Network Monitor Testing Script

This script comprehensively tests the NetworkMonitor class with detailed logging
to show exactly what's happening during network discovery and monitoring operations.

Usage: 
1. Activate virtual environment: source network_monitor_env/bin/activate
2. Run: python test_network_monitor.py
"""

import sys
import os
import time
import logging
from datetime import datetime
import traceback

# Add the backend directory to Python path so we can import our module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from network_monitor import NetworkMonitor
except ImportError as e:
    print(f"❌ Error importing NetworkMonitor: {e}")
    print("Make sure you're running this from the project root directory")
    print("and that you've activated the virtual environment:")
    print("  source network_monitor_env/bin/activate")
    sys.exit(1)

# Configure logging for detailed output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class NetworkMonitorTester:
    """
    Comprehensive testing class for NetworkMonitor functionality.
    
    This class tests all major features with detailed logging so you can
    see exactly what's happening at each step of the network monitoring process.
    """
    
    def __init__(self):
        self.monitor = None
        self.test_results = {
            'initialization': False,
            'device_discovery': False,
            'bandwidth_monitoring': False,
            'connection_quality': False
        }
    
    def print_header(self, title: str):
        """Print a formatted header for test sections."""
        print("\n" + "="*80)
        print(f"🧪 {title}")
        print("="*80)
        logger.info(f"Starting test: {title}")
    
    def print_step(self, step: str):
        """Print a formatted step description."""
        print(f"\n📋 Step: {step}")
        logger.info(f"Executing step: {step}")
    
    def print_result(self, success: bool, message: str):
        """Print test result with appropriate emoji."""
        emoji = "✅" if success else "❌"
        print(f"{emoji} {message}")
        if success:
            logger.info(f"SUCCESS: {message}")
        else:
            logger.error(f"FAILURE: {message}")
    
    def check_virtual_environment(self):
        """Check if we're running in a virtual environment."""
        print("🔍 Environment Check:")
        
        # Check if we're in a virtual environment
        in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        
        if in_venv:
            print("   ✅ Running in virtual environment")
            print(f"   📁 Virtual env path: {sys.prefix}")
        else:
            print("   ⚠️  Not running in virtual environment")
            print("   💡 Consider activating virtual environment: source network_monitor_env/bin/activate")
        
        print(f"   🐍 Python executable: {sys.executable}")
        print(f"   📊 Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    def test_initialization(self) -> bool:
        """
        Test NetworkMonitor initialization and network detection.
        
        This tests:
        1. Class instantiation
        2. Automatic network range detection
        3. Network configuration validation
        """
        self.print_header("Network Monitor Initialization")
        
        try:
            self.print_step("Creating NetworkMonitor instance")
            self.monitor = NetworkMonitor()
            
            print(f"🌐 Detected network range: {self.monitor.network_range}")
            print(f"📊 Device storage initialized: {len(self.monitor.devices)} devices")
            print(f"🔄 Monitoring status: {'Active' if self.monitor.monitoring else 'Inactive'}")
            
            # Validate network range format
            import ipaddress
            network = ipaddress.IPv4Network(self.monitor.network_range)
            
            print(f"📍 Network details:")
            print(f"   • Network address: {network.network_address}")
            print(f"   • Broadcast address: {network.broadcast_address}")
            print(f"   • Available host IPs: {network.num_addresses - 2}")
            print(f"   • Subnet mask: {network.netmask}")
            
            self.test_results['initialization'] = True
            self.print_result(True, "NetworkMonitor initialized successfully")
            return True
            
        except Exception as e:
            self.print_result(False, f"Initialization failed: {str(e)}")
            logger.error(f"Initialization error: {traceback.format_exc()}")
            return False
    
    def test_device_discovery(self) -> bool:
        """
        Test network device discovery functionality.
        
        This tests:
        1. Network ping sweep
        2. ARP table parsing
        3. Hostname resolution
        4. MAC address discovery
        5. Device information compilation
        """
        self.print_header("Device Discovery Testing")
        
        if not self.monitor:
            self.print_result(False, "NetworkMonitor not initialized")
            return False
        
        try:
            self.print_step("Starting network device discovery")
            print(f"🔍 Scanning network range: {self.monitor.network_range}")
            print("⏱️  This may take 30-60 seconds depending on network size...")
            print("💡 Make sure other devices are connected to your WiFi for better results!")
            
            # Time the discovery process
            start_time = time.time()
            devices = self.monitor.discover_devices()
            discovery_time = time.time() - start_time
            
            print(f"\n📊 Discovery Results (completed in {discovery_time:.2f} seconds):")
            print(f"   • Total devices found: {len(devices)}")
            
            if devices:
                print(f"   • Device details:")
                for i, device in enumerate(devices, 1):
                    print(f"\n     Device #{i}:")
                    print(f"       IP Address: {device['ip']}")
                    print(f"       Hostname: {device.get('hostname', 'Unknown')}")
                    print(f"       MAC Address: {device.get('mac_address', 'Unknown')}")
                    print(f"       Latency: {device.get('latency_ms', 'N/A')}ms")
                    print(f"       Status: {device.get('status', 'Unknown')}")
                    print(f"       Last Seen: {device.get('last_seen', 'Unknown')}")
                
                # Analyze device types based on MAC addresses
                mac_vendors = self._analyze_device_types(devices)
                if mac_vendors:
                    print(f"\n🏷️  Device Type Analysis:")
                    for vendor, count in mac_vendors.items():
                        print(f"       {vendor}: {count} device(s)")
                
                self.test_results['device_discovery'] = True
                self.print_result(True, f"Successfully discovered {len(devices)} devices")
                return True
            else:
                print("   💡 No devices found. This could be because:")
                print("      • Your network uses a different IP range")
                print("      • Devices have ping disabled")
                print("      • You're on a restricted network")
                print("      • Only your computer is connected")
                self.test_results['device_discovery'] = True
                self.print_result(True, "Discovery completed (no devices found, but that's okay)")
                return True
                
        except Exception as e:
            self.print_result(False, f"Device discovery failed: {str(e)}")
            logger.error(f"Discovery error: {traceback.format_exc()}")
            return False
    
    def test_bandwidth_monitoring(self) -> bool:
        """Test bandwidth monitoring with user-friendly explanations."""
        self.print_header("Bandwidth Monitoring Testing")
        
        if not self.monitor:
            self.print_result(False, "NetworkMonitor not initialized")
            return False
        
        try:
            self.print_step("Getting initial network interface statistics")
            
            # Get initial stats
            initial_stats = self.monitor.get_bandwidth_stats()
            
            print(f"📊 Network Interface Overview:")
            print(f"   • Monitoring all interfaces: {initial_stats.get('interfaces', [])}")
            print(f"   • Total bytes sent: {initial_stats['bytes_sent']:,} bytes")
            print(f"   • Total bytes received: {initial_stats['bytes_recv']:,} bytes")
            print(f"   • Total packets sent: {initial_stats['packets_sent']:,}")
            print(f"   • Total packets received: {initial_stats['packets_recv']:,}")
            
            self.print_step("Measuring bandwidth usage over time")
            print("⏱️  Taking measurements over 8 seconds...")
            print("💡 Try opening a website or streaming a video to see activity!")
            
            # Take measurements over time
            measurements = []
            measurement_interval = 2  # seconds
            total_measurement_time = 8
            
            for i in range(total_measurement_time // measurement_interval):
                print(f"   📏 Measurement {i+1}/{total_measurement_time // measurement_interval} "
                      f"(waiting {measurement_interval}s...)")
                time.sleep(measurement_interval)
                
                current_stats = self.monitor.get_bandwidth_stats()
                if i > 0:  # Skip first measurement (no previous data)
                    usage = self.monitor.calculate_bandwidth_usage(
                        measurements[-1], current_stats
                    )
                    
                    print(f"      ⬆️  Upload: {usage['upload_rate_mbps']} Mbps")
                    print(f"      ⬇️  Download: {usage['download_rate_mbps']} Mbps")
                    print(f"      📊 Data transferred: {usage['total_usage_mb']} MB")
                
                measurements.append(current_stats)
            
            # Calculate overall statistics
            if len(measurements) >= 2:
                overall_usage = self.monitor.calculate_bandwidth_usage(
                    measurements[0], measurements[-1]
                )
                
                print(f"\n📈 Overall Bandwidth Summary ({total_measurement_time} seconds):")
                print(f"   • Average upload rate: {overall_usage['upload_rate_mbps']} Mbps")
                print(f"   • Average download rate: {overall_usage['download_rate_mbps']} Mbps")
                print(f"   • Total data transferred: {overall_usage['total_usage_mb']} MB")
                
                self.test_results['bandwidth_monitoring'] = True
                self.print_result(True, "Bandwidth monitoring completed successfully")
                return True
            else:
                self.print_result(False, "Insufficient measurements for bandwidth calculation")
                return False
                
        except Exception as e:
            self.print_result(False, f"Bandwidth monitoring failed: {str(e)}")
            logger.error(f"Bandwidth monitoring error: {traceback.format_exc()}")
            return False
    
    def test_connection_quality(self) -> bool:
        """Test connection quality monitoring for discovered devices."""
        self.print_header("Connection Quality Testing")
        
        if not self.monitor or not self.monitor.devices:
            # If no devices found, test with common gateway addresses
            print("   💡 No devices discovered, testing connection to common gateways...")
            test_ips = ['8.8.8.8', '1.1.1.1']  # Google DNS and Cloudflare DNS
            
            try:
                for ip in test_ips:
                    print(f"\n🔍 Testing connection quality to {ip}")
                    quality = self.monitor.monitor_device_connectivity(ip, samples=5)
                    
                    print(f"   📋 Results for {ip}:")
                    print(f"      • Quality Rating: {quality['quality_rating']} ⭐")
                    print(f"      • Average Latency: {quality['avg_latency_ms']}ms")
                    print(f"      • Packet Loss: {quality['packet_loss_percent']}%")
                    print(f"      • Jitter: {quality['jitter_ms']}ms")
                
                self.test_results['connection_quality'] = True
                self.print_result(True, "Connection quality testing completed")
                return True
                
            except Exception as e:
                self.print_result(False, f"Connection quality testing failed: {str(e)}")
                return False
        
        try:
            devices_to_test = list(self.monitor.devices.keys())[:2]  # Test up to 2 devices
            
            self.print_step(f"Testing connection quality to {len(devices_to_test)} devices")
            
            for ip in devices_to_test:
                device_info = self.monitor.devices[ip]
                hostname = device_info.get('hostname', 'Unknown')
                
                print(f"\n🔍 Testing device: {ip} ({hostname})")
                
                # Test with fewer samples for faster execution
                quality = self.monitor.monitor_device_connectivity(ip, samples=5)
                
                print(f"   📋 Results for {ip}:")
                print(f"      • Quality Rating: {quality['quality_rating']} ⭐")
                print(f"      • Average Latency: {quality['avg_latency_ms']}ms")
                print(f"      • Packet Loss: {quality['packet_loss_percent']}%")
                print(f"      • Jitter: {quality['jitter_ms']}ms")
            
            self.test_results['connection_quality'] = True
            self.print_result(True, f"Connection quality testing completed for {len(devices_to_test)} devices")
            return True
            
        except Exception as e:
            self.print_result(False, f"Connection quality testing failed: {str(e)}")
            logger.error(f"Connection quality error: {traceback.format_exc()}")
            return False
    
    def _analyze_device_types(self, devices: list) -> dict:
        """Analyze device types based on MAC address prefixes (OUI)."""
        vendor_map = {
            '00:50:56': 'VMware Virtual',
            '08:00:27': 'VirtualBox Virtual',
            '00:1B:63': 'Apple Device',
            '00:25:00': 'Apple Device',
            '28:CF:E9': 'Apple Device',
            '00:23:DF': 'Apple Device',
            '00:0C:29': 'VMware Virtual',
            '52:54:00': 'QEMU Virtual',
            'DC:A6:32': 'Raspberry Pi',
            'B8:27:EB': 'Raspberry Pi',
        }
        
        vendors = {}
        for device in devices:
            mac = device.get('mac_address')
            if mac:
                prefix = mac[:8]  # First 3 octets
                vendor = vendor_map.get(prefix, 'Unknown Device')
                vendors[vendor] = vendors.get(vendor, 0) + 1
        
        return vendors
    
    def run_all_tests(self):
        """Run all network monitoring tests with comprehensive logging."""
        print("🚀 Starting Comprehensive Network Monitor Testing")
        print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("💡 This will test all major functionality of the network monitoring system")
        
        # Check environment and system requirements
        self.check_virtual_environment()
        self.check_system_requirements()
        
        # Run all tests
        tests = [
            ('Initialization', self.test_initialization),
            ('Device Discovery', self.test_device_discovery),
            ('Bandwidth Monitoring', self.test_bandwidth_monitoring),
            ('Connection Quality', self.test_connection_quality)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed_tests += 1
            except KeyboardInterrupt:
                print("\n⚠️  Test interrupted by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error in {test_name}: {e}")
        
        # Final summary
        self.print_header("Test Summary")
        print(f"📊 Tests passed: {passed_tests}/{total_tests}")
        print(f"⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name}: {status}")
        
        if passed_tests == total_tests:
            print("\n🎉 All tests passed! Your network monitor is working correctly.")
            print("\n💡 Next steps for your portfolio project:")
            print("   • Add a web dashboard (React/Vue.js frontend)")
            print("   • Implement AI prediction models")
            print("   • Add data persistence with a database")
            print("   • Create REST APIs for the frontend")
        else:
            print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Check the logs above for details.")
        
        return passed_tests == total_tests
    
    def check_system_requirements(self):
        """Check if system has required dependencies and permissions."""
        print("\n🔍 Checking System Requirements:")
        
        # Check required modules
        required_modules = ['psutil', 'ping3', 'ipaddress']
        for module in required_modules:
            try:
                __import__(module)
                print(f"   ✅ {module}: Available")
            except ImportError:
                print(f"   ❌ {module}: Missing")
                print(f"      💡 Install with: pip install {module}")
        
        # Check platform
        import platform
        print(f"   💻 Operating System: {platform.system()} {platform.release()}")
        
        # Check network interfaces
        try:
            import psutil
            interfaces = psutil.net_if_addrs()
            print(f"   🌐 Network interfaces: {len(interfaces)} detected")
        except Exception as e:
            print(f"   ⚠️  Could not check network interfaces: {e}")

if __name__ == "__main__":
    """
    Main testing entry point.
    
    This script will run comprehensive tests of the NetworkMonitor class
    with detailed logging to show exactly what's happening during execution.
    """
    
    print("🌐 Network Monitor Testing Suite")
    print("This will test all network monitoring functionality with detailed logging")
    print("=" * 80)
    
    # Create and run tester
    tester = NetworkMonitorTester()
    
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Testing interrupted by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error during testing: {e}")
        logger.error(f"Unexpected testing error: {traceback.format_exc()}")
        sys.exit(1) 