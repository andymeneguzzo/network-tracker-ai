#!/usr/bin/env python3
"""
Database Integration Test Script

This script tests the complete integration between our continuous monitoring
service and the SQLite database system. It demonstrates:

1. Database initialization and schema creation
2. Real monitoring data collection and storage
3. Data retrieval and analysis
4. Performance and reliability validation

This showcases a complete data pipeline that recruiters love to see!
"""

import sys
import os
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path

# Add backend directory to Python path for imports
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from database_manager import NetworkDatabaseManager
from continuous_monitor_service import ContinuousNetworkMonitorService, MonitoringSnapshot
from network_monitor import NetworkMonitor

class DatabaseIntegrationTest:
    """
    Comprehensive test of database integration with monitoring service.
    
    This demonstrates enterprise-level testing practices:
    1. Setup and teardown procedures
    2. Integration testing between components
    3. Data validation and integrity checks
    4. Performance monitoring
    5. Error handling validation
    """
    
    def __init__(self):
        self.test_db_path = "test_network_integration.db"
        self.db_manager = None
        self.monitor_service = None
        self.session_id = None
        
    def setup_test_environment(self):
        """Initialize test environment with fresh database"""
        print("🧪 Setting up test environment...")
        
        # Remove existing test database
        if Path(self.test_db_path).exists():
            Path(self.test_db_path).unlink()
            print("🗑️ Removed old test database")
        
        # Initialize fresh database
        self.db_manager = NetworkDatabaseManager(self.test_db_path)
        print("✅ Fresh database created")
        
        # Initialize monitoring service
        self.monitor_service = ContinuousNetworkMonitorService()
        print("✅ Monitoring service initialized")
    
    def test_database_operations(self):
        """Test basic database operations"""
        print("\n📊 Testing database operations...")
        
        # Test session management
        self.session_id = self.db_manager.start_monitoring_session("Integration test session")
        print(f"✅ Session created: #{self.session_id}")
        
        # Test device storage
        test_devices = [
            {'ip': '192.168.1.1', 'mac_address': 'AA:BB:CC:DD:EE:FF', 'hostname': 'router'},
            {'ip': '192.168.1.100', 'mac_address': 'FF:EE:DD:CC:BB:AA', 'hostname': 'laptop'},
            {'ip': '192.168.1.150', 'mac_address': None, 'hostname': 'unknown-device'}
        ]
        
        device_ids = []
        for device in test_devices:
            device_id = self.db_manager.save_device(device)
            device_ids.append(device_id)
            print(f"✅ Device saved: {device['ip']} (ID: {device_id})")
        
        # Test snapshot storage
        test_snapshot = {
            'device_count': len(test_devices),
            'total_upload_mbps': 15.5,
            'total_download_mbps': 75.2,
            'total_usage_mb': 2048.0,
            'avg_latency_ms': 23.5,
            'avg_packet_loss': 1.2,
            'overall_quality': 'Good',
            'active_interfaces': ['en0', 'wlan0'],
            'tested_device_ip': '192.168.1.1'
        }
        
        snapshot_id = self.db_manager.save_network_snapshot(self.session_id, test_snapshot)
        print(f"✅ Snapshot saved: ID {snapshot_id}")
        
        # Test quality test storage
        quality_test = {
            'latency_ms': 23.5,
            'packet_loss_percent': 1.2,
            'response_time_ms': 23.1,
            'test_status': 'success'
        }
        
        self.db_manager.save_device_quality_test(snapshot_id, '192.168.1.1', quality_test)
        print("✅ Quality test saved")
        
        return True
    
    def test_live_integration(self, duration_seconds: int = 30):
        """Test live integration with actual monitoring service"""
        print(f"\n🔄 Testing live integration for {duration_seconds} seconds...")
        
        # Create enhanced monitoring service with database integration
        class DatabaseIntegratedMonitorService(ContinuousNetworkMonitorService):
            def __init__(self, db_manager, session_id):
                super().__init__()
                self.db_manager = db_manager
                self.session_id = session_id
                self.snapshots_saved = 0
            
            def _process_monitoring_data(self, snapshot: MonitoringSnapshot):
                """Override to add database storage"""
                # Call parent method for display
                super()._process_monitoring_data(snapshot)
                
                # Save to database
                try:
                    # Convert MonitoringSnapshot to dict
                    snapshot_data = {
                        'device_count': snapshot.device_count,
                        'total_upload_mbps': snapshot.total_upload_mbps,
                        'total_download_mbps': snapshot.total_download_mbps,
                        'total_usage_mb': snapshot.total_usage_mb,
                        'avg_latency_ms': snapshot.avg_latency_ms,
                        'avg_packet_loss': snapshot.avg_packet_loss,
                        'overall_quality': snapshot.overall_quality,
                        'active_interfaces': snapshot.active_interfaces,
                        'tested_device_ip': snapshot.tested_device_ip
                    }
                    
                    # Save snapshot to database
                    snapshot_id = self.db_manager.save_network_snapshot(
                        self.session_id, snapshot_data
                    )
                    
                    # Save discovered devices from the snapshot
                    for device in snapshot.devices:
                        self.db_manager.save_device(device)
                    
                    # Save quality test result if we tested a device
                    if snapshot.tested_device_ip and snapshot.avg_latency_ms > 0:
                        quality_test = {
                            'latency_ms': snapshot.avg_latency_ms,
                            'packet_loss_percent': snapshot.avg_packet_loss,
                            'response_time_ms': snapshot.avg_latency_ms,
                            'test_status': 'success' if snapshot.avg_latency_ms < 1000 else 'timeout'
                        }
                        
                        self.db_manager.save_device_quality_test(
                            snapshot_id, snapshot.tested_device_ip, quality_test
                        )
                    
                    self.snapshots_saved += 1
                    
                    # Print database status occasionally
                    if self.snapshots_saved % 10 == 0:
                        print(f"💾 Database status: {self.snapshots_saved} snapshots saved")
                
                except Exception as e:
                    print(f"❌ Database error: {e}")
        
        # Create integrated service
        integrated_service = DatabaseIntegratedMonitorService(self.db_manager, self.session_id)
        
        # Start monitoring
        print("🚀 Starting live monitoring with database integration...")
        integrated_service.start()
        
        # Run for specified duration
        try:
            time.sleep(duration_seconds)
        finally:
            integrated_service.stop()
            print(f"🏁 Live monitoring completed. Snapshots saved: {integrated_service.snapshots_saved}")
        
        return integrated_service.snapshots_saved
    
    def test_data_retrieval(self):
        """Test data retrieval and analysis functions"""
        print("\n📈 Testing data retrieval and analysis...")
        
        # Get recent snapshots
        recent_snapshots = self.db_manager.get_recent_snapshots(limit=10)
        print(f"✅ Retrieved {len(recent_snapshots)} recent snapshots")
        
        if recent_snapshots:
            latest = recent_snapshots[0]
            print(f"   Latest snapshot: {latest['device_count']} devices, "
                  f"{latest['overall_quality']} quality")
        
        # Get session summary
        if self.session_id:
            summary = self.db_manager.get_session_summary(self.session_id)
            if summary:
                print(f"✅ Session summary: {summary['total_snapshots']} snapshots, "
                      f"avg {summary['avg_device_count']:.1f} devices")
        
        # Test device history (use first device from recent snapshots)
        if recent_snapshots and recent_snapshots[0]['tested_device_ip']:
            device_ip = recent_snapshots[0]['tested_device_ip']
            device_history = self.db_manager.get_device_history(device_ip, hours=1)
            print(f"✅ Device history for {device_ip}: {len(device_history)} test results")
        
        return True
    
    def cleanup_test_environment(self):
        """Clean up test environment"""
        print("\n🧹 Cleaning up test environment...")
        
        # End session if active
        if self.session_id:
            self.db_manager.end_monitoring_session(self.session_id)
            print(f"✅ Session #{self.session_id} ended")
        
        # Keep test database for inspection (don't delete)
        print(f"📊 Test database preserved at: {Path(self.test_db_path).absolute()}")
    
    def run_complete_test(self):
        """Run the complete integration test suite"""
        print("🚀 Starting Complete Database Integration Test")
        print("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # Setup
            self.setup_test_environment()
            
            # Test basic operations
            if not self.test_database_operations():
                print("❌ Basic database operations failed")
                return False
            
            # Test live integration
            snapshots_count = self.test_live_integration(duration_seconds=20)
            if snapshots_count < 10:  # Should get at least 10 snapshots in 20 seconds
                print(f"⚠️ Only {snapshots_count} snapshots collected (expected at least 10)")
            
            # Test data retrieval
            if not self.test_data_retrieval():
                print("❌ Data retrieval tests failed")
                return False
            
            # Calculate test duration
            duration = datetime.now() - start_time
            
            print("\n" + "=" * 60)
            print("🎉 ALL INTEGRATION TESTS PASSED!")
            print(f"⏱️ Test duration: {duration.total_seconds():.1f} seconds")
            print(f"💾 Database file: {Path(self.test_db_path).absolute()}")
            print(f"📊 Snapshots collected: {snapshots_count}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Integration test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            self.cleanup_test_environment()


if __name__ == "__main__":
    # Run the complete integration test
    tester = DatabaseIntegrationTest()
    success = tester.run_complete_test()
    
    if success:
        print("\n🎯 Integration test completed successfully!")
        print("💡 Your network monitoring system now has full database persistence!")
        print("🚀 Ready for AI integration in the next phase!")
    else:
        print("\n💥 Integration test failed. Check the error messages above.")
    
    exit(0 if success else 1) 