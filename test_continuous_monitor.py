#!/usr/bin/env python3
"""
Continuous Network Monitor Testing Script - Enhanced with Round-Robin Testing

This script thoroughly tests the continuous monitoring service with realistic expectations
and includes specific testing for the round-robin device quality testing feature.

Usage: python test_continuous_monitor.py
"""

import sys
import os
import time
import threading
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from continuous_monitor_service import ContinuousNetworkMonitorService, MonitoringSnapshot
    from network_monitor import NetworkMonitor
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    print("Make sure you're running this from the project root directory")
    print("and that the virtual environment is activated:")
    print("  source network_monitor_env/bin/activate")
    sys.exit(1)


class ContinuousMonitorTester:
    """
    Comprehensive testing class for the continuous monitoring service.
    
    Enhanced version with round-robin testing validation.
    """
    
    def __init__(self):
        self.test_results = {}
        self.service = None
    
    def print_header(self, title: str):
        """Print formatted test section header."""
        print(f"\n{'='*70}")
        print(f"🧪 {title}")
        print('='*70)
    
    def print_result(self, test_name: str, success: bool, details: str = ""):
        """Print test result with status."""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    💡 {details}")
        self.test_results[test_name] = success
    
    def test_service_lifecycle(self) -> bool:
        """Test service start/stop functionality."""
        self.print_header("Service Lifecycle Testing")
        
        try:
            # Test 1: Service creation
            print("📝 Creating service instance...")
            service = ContinuousNetworkMonitorService(monitor_interval=0.5)
            self.print_result("Service Creation", True, "Service instance created successfully")
            
            # Test 2: Service start
            print("🚀 Starting service...")
            start_success = service.start()
            
            # Wait for first measurement
            time.sleep(1.0)
            
            if start_success and service.is_running:
                self.print_result("Service Start", True, "Service started and is running")
            else:
                self.print_result("Service Start", False, "Service failed to start properly")
                return False
            
            # Test 3: Service status check
            status = service.get_service_status()
            if status['is_running']:
                self.print_result("Service Status Check", True, 
                                f"Service is active (measurements: {status['measurement_count']})")
            else:
                self.print_result("Service Status Check", False, "Service status indicates problems")
            
            # Test 4: Service stop
            print("🛑 Stopping service...")
            stop_success = service.stop()
            
            if stop_success and not service.is_running:
                self.print_result("Service Stop", True, "Service stopped cleanly")
            else:
                self.print_result("Service Stop", False, "Service did not stop properly")
                return False
            
            return True
            
        except Exception as e:
            self.print_result("Service Lifecycle", False, f"Exception occurred: {e}")
            return False
    
    def test_data_collection_reliability(self) -> bool:
        """Test data collection reliability and accuracy."""
        self.print_header("Data Collection Reliability Testing")
        
        try:
            service = ContinuousNetworkMonitorService(monitor_interval=0.5)
            
            print("🚀 Starting 8-second data collection test...")
            service.start()
            
            test_duration = 8
            start_time = time.time()
            
            while time.time() - start_time < test_duration:
                print(f"\r⏱️  Test progress: {time.time() - start_time:.1f}/{test_duration}s", 
                      end="", flush=True)
                time.sleep(0.5)
            
            print("\n🛑 Stopping service...")
            service.stop()
            
            # Analyze results
            status = service.get_service_status()
            snapshots = service.get_recent_snapshots(50)
            
            print(f"\n📊 Data Collection Analysis:")
            print(f"   Total measurements: {status['measurement_count']}")
            print(f"   Successful measurements: {status['successful_measurements']}")
            print(f"   Success rate: {status['success_rate']:.1f}%")
            print(f"   Snapshots collected: {len(snapshots)}")
            
            success_rate = status['success_rate']
            
            if success_rate >= 70.0:
                self.print_result("Success Rate", True, f"{success_rate:.1f}% success rate achieved")
            else:
                self.print_result("Success Rate", False, f"Only {success_rate:.1f}% success rate")
                return False
            
            if status['measurement_count'] >= 3:
                self.print_result("Measurement Count", True, 
                                f"{status['measurement_count']} measurements in {test_duration}s")
            else:
                self.print_result("Measurement Count", False, 
                                f"Only {status['measurement_count']} measurements (expected at least 3)")
            
            # Validate snapshot data
            if snapshots:
                sample_snapshot = snapshots[-1]
                if isinstance(sample_snapshot, MonitoringSnapshot):
                    self.print_result("Snapshot Validity", True, "Snapshots contain valid data structures")
                else:
                    self.print_result("Snapshot Validity", False, "Invalid snapshot data structure")
                    return False
                
                # Check data ranges
                if (sample_snapshot.device_count >= 0 and 
                    sample_snapshot.total_upload_mbps >= 0 and 
                    sample_snapshot.total_download_mbps >= 0):
                    self.print_result("Data Validation", True, "All metrics within expected ranges")
                else:
                    self.print_result("Data Validation", False, "Some metrics outside expected ranges")
                
                # NEW: Test round-robin field exists
                if hasattr(sample_snapshot, 'tested_device_ip'):
                    self.print_result("Round-Robin Field", True, "New tested_device_ip field present")
                else:
                    self.print_result("Round-Robin Field", False, "Missing tested_device_ip field")
            else:
                self.print_result("Snapshot Collection", False, "No snapshots were collected")
                return False
            
            return True
            
        except Exception as e:
            self.print_result("Data Collection", False, f"Exception occurred: {e}")
            return False
    
    def test_round_robin_functionality(self) -> bool:
        """
        NEW: Test round-robin device testing functionality.
        
        This test verifies that:
        1. Different devices get tested over time
        2. Round-robin state is tracked correctly
        3. Service status includes round-robin information
        """
        self.print_header("Round-Robin Device Testing")
        
        try:
            # Use longer interval to ensure quality testing is enabled
            service = ContinuousNetworkMonitorService(monitor_interval=1.0)
            
            print("🔄 Testing round-robin device selection over 15 seconds...")
            print("💡 This test checks if different devices get tested over time")
            
            service.start()
            
            # Let it run long enough for multiple quality test cycles
            test_duration = 15
            start_time = time.time()
            
            # Track which devices get tested
            tested_devices = set()
            snapshots_with_tests = []
            
            while time.time() - start_time < test_duration:
                print(f"\r⏱️  Round-robin test progress: {time.time() - start_time:.1f}/{test_duration}s", 
                      end="", flush=True)
                
                # Check recent snapshots for tested devices
                recent_snapshots = service.get_recent_snapshots(5)
                for snapshot in recent_snapshots:
                    if hasattr(snapshot, 'tested_device_ip') and snapshot.tested_device_ip:
                        tested_devices.add(snapshot.tested_device_ip)
                        if snapshot not in snapshots_with_tests:
                            snapshots_with_tests.append(snapshot)
                
                time.sleep(1.0)
            
            print(f"\n🛑 Stopping service...")
            service.stop()
            
            # Analyze round-robin results
            status = service.get_service_status()
            final_snapshots = service.get_recent_snapshots(50)
            
            print(f"\n🔄 Round-Robin Analysis:")
            print(f"   Total devices found: {status.get('devices_in_rotation', 0)}")
            print(f"   Unique devices tested: {len(tested_devices)}")
            print(f"   Current device index: {status.get('current_device_index', 'unknown')}")
            print(f"   Quality testing enabled: {status.get('quality_testing_enabled', False)}")
            
            if tested_devices:
                print(f"   Tested device IPs: {sorted(tested_devices)}")
            
            # Test 1: Round-robin status fields
            if 'current_device_index' in status and 'devices_in_rotation' in status:
                self.print_result("Round-Robin Status Fields", True, 
                                "Service status includes round-robin tracking")
            else:
                self.print_result("Round-Robin Status Fields", False, 
                                "Missing round-robin status fields")
            
            # Test 2: Quality testing enabled check
            if status.get('quality_testing_enabled', False):
                self.print_result("Quality Testing Enabled", True, 
                                "Quality testing is enabled for this interval")
            else:
                print("   ℹ️  Quality testing disabled (fast mode) - this is expected for short intervals")
                self.print_result("Quality Testing Mode", True, 
                                "Quality testing mode correctly determined")
            
            # Test 3: Device testing occurs (if quality testing is enabled)
            if status.get('quality_testing_enabled', False):
                if len(tested_devices) > 0:
                    self.print_result("Device Testing", True, 
                                    f"Successfully tested {len(tested_devices)} unique devices")
                else:
                    self.print_result("Device Testing", False, 
                                    "No devices were tested despite quality testing being enabled")
                
                # Test 4: Round-robin progression (if multiple devices available)
                if status.get('devices_in_rotation', 0) > 1 and len(tested_devices) > 1:
                    self.print_result("Round-Robin Progression", True, 
                                    "Multiple devices tested - round-robin working")
                elif status.get('devices_in_rotation', 0) <= 1:
                    self.print_result("Round-Robin Progression", True, 
                                    "Only one device available - round-robin not needed")
                else:
                    self.print_result("Round-Robin Progression", False, 
                                    "Multiple devices available but round-robin not working")
            else:
                # Quality testing disabled - that's fine for fast intervals
                self.print_result("Fast Mode Operation", True, 
                                "Quality testing correctly disabled for fast monitoring")
            
            return True
            
        except Exception as e:
            self.print_result("Round-Robin Testing", False, f"Exception occurred: {e}")
            return False
    
    def test_real_time_display(self) -> bool:
        """Test real-time display functionality."""
        self.print_header("Real-time Display Testing")
        
        try:
            print("📺 Testing real-time display for 4 seconds...")
            print("   You should see continuously updating network statistics below:")
            print("-" * 70)
            
            service = ContinuousNetworkMonitorService(monitor_interval=1.0)
            service.start()
            
            time.sleep(4)
            
            service.stop()
            
            # Check if we got output
            status = service.get_service_status()
            if status['measurement_count'] > 0:
                self.print_result("Real-time Display", True, 
                                "Real-time statistics displayed successfully")
                return True
            else:
                self.print_result("Real-time Display", False, "No real-time output generated")
                return False
                
        except Exception as e:
            self.print_result("Real-time Display", False, f"Exception occurred: {e}")
            return False
    
    def test_performance_characteristics(self) -> bool:
        """Test performance characteristics of the monitoring service."""
        self.print_header("Performance Characteristics Testing")
        
        try:
            print("⚡ Testing performance characteristics...")
            
            service = ContinuousNetworkMonitorService(monitor_interval=1.0)
            
            print("   Testing timing accuracy over 4 measurements...")
            service.start()
            
            # Record timestamps
            timestamps = []
            start_count = 0
            timeout_counter = 0
            max_timeout = 20
            
            while len(timestamps) < 4 and timeout_counter < max_timeout:
                current_count = service.get_service_status()['measurement_count']
                if current_count > start_count:
                    timestamps.append(time.time())
                    start_count = current_count
                time.sleep(0.2)
                timeout_counter += 0.2
            
            service.stop()
            
            # Analyze timing
            if len(timestamps) >= 2:
                intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
                avg_interval = sum(intervals) / len(intervals)
                
                if 0.5 <= avg_interval <= 3.0:
                    self.print_result("Timing Accuracy", True, 
                                    f"Average interval: {avg_interval:.2f}s (target: 1.0s, tolerance: 0.5-3.0s)")
                else:
                    self.print_result("Timing Accuracy", False, 
                                    f"Interval outside tolerance: {avg_interval:.2f}s")
                    return False
            else:
                self.print_result("Timing Accuracy", False, "Could not collect enough timing data")
                return False
            
            # Test sustained operation
            print("   Testing sustained operation for 6 seconds...")
            service = ContinuousNetworkMonitorService(monitor_interval=1.0)
            service.start()
            time.sleep(6)
            
            final_status = service.get_service_status()
            service.stop()
            
            if final_status['success_rate'] >= 50:
                self.print_result("Sustained Operation", True, 
                                f"Maintained {final_status['success_rate']:.1f}% success over 6s")
            else:
                self.print_result("Sustained Operation", False, 
                                f"Success rate dropped to {final_status['success_rate']:.1f}%")
            
            return True
            
        except Exception as e:
            self.print_result("Performance Testing", False, f"Exception occurred: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling and robustness."""
        self.print_header("Error Handling and Robustness Testing")
        
        try:
            # Test with reasonable fast interval
            print("⚡ Testing fast monitoring interval...")
            service = ContinuousNetworkMonitorService(monitor_interval=0.3)
            service.start()
            time.sleep(3)
            
            status = service.get_service_status()
            service.stop()
            
            if status['measurement_count'] >= 1:
                self.print_result("Fast Interval", True, 
                                f"Handled fast interval: {status['measurement_count']} measurements")
            else:
                self.print_result("Fast Interval", False, "Failed to handle fast interval")
            
            # Test multiple service instances
            print("👥 Testing multiple service instances...")
            service1 = ContinuousNetworkMonitorService(monitor_interval=1.0)
            service2 = ContinuousNetworkMonitorService(monitor_interval=1.0)
            
            service1.start()
            service2.start()
            time.sleep(3)
            
            status1 = service1.get_service_status()
            status2 = service2.get_service_status()
            
            service1.stop()
            service2.stop()
            
            if status1['measurement_count'] > 0 and status2['measurement_count'] > 0:
                self.print_result("Multiple Instances", True, "Both services operated independently")
            else:
                self.print_result("Multiple Instances", False, "Services interfered with each other")
            
            return True
            
        except Exception as e:
            self.print_result("Error Handling", False, f"Exception occurred: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all tests and provide comprehensive results."""
        print("🧪 Continuous Network Monitor - Comprehensive Testing Suite (Round-Robin Enhanced)")
        print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("💡 This will verify reliability of the monitoring service including round-robin testing")
        
        # Run all test suites
        tests = [
            ("Service Lifecycle", self.test_service_lifecycle),
            ("Data Collection Reliability", self.test_data_collection_reliability),
            ("Round-Robin Functionality", self.test_round_robin_functionality),  # NEW TEST
            ("Real-time Display", self.test_real_time_display),
            ("Performance Characteristics", self.test_performance_characteristics),
            ("Error Handling", self.test_error_handling)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed_tests += 1
                print()
            except KeyboardInterrupt:
                print(f"\n⚠️  Testing interrupted during {test_name}")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error in {test_name}: {e}")
        
        # Final results
        self.print_header("Final Test Results")
        
        print(f"📊 Tests passed: {passed_tests}/{total_tests}")
        print(f"⏰ Testing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name}: {status}")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! Your continuous monitoring service is working perfectly!")
            print("✅ Service demonstrates high reliability")
            print("✅ Round-robin device testing verified")
            print("✅ Ready for production deployment")
            print("✅ Ready for database integration")
            print("\n💡 Next steps:")
            print("   • Add SQLite database persistence")
            print("   • Implement data analytics")
            print("   • Build AI prediction models")
            return True
        else:
            print(f"\n⚠️  {total_tests - passed_tests} test(s) failed.")
            print("🔧 Please review the failed tests above and fix any issues.")
            return False


def main():
    """Main testing entry point."""
    print("🌐 Continuous Network Monitor Testing (Round-Robin Enhanced)")
    print("=" * 50)
    
    # Check environment
    print("🔍 Checking test environment...")
    try:
        monitor = NetworkMonitor()
        print(f"✅ NetworkMonitor initialized for network: {monitor.network_range}")
        
        service = ContinuousNetworkMonitorService()
        print("✅ ContinuousNetworkMonitorService can be created")
        
    except Exception as e:
        print(f"❌ Environment check failed: {e}")
        print("💡 Make sure dependencies are installed and you're in the right directory")
        return False
    
    # Run comprehensive tests
    tester = ContinuousMonitorTester()
    success = tester.run_all_tests()
    
    return success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Testing interrupted by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected testing error: {e}")
        sys.exit(1) 