#!/usr/bin/env python3
"""
SQLite Database Manager for Network Monitoring System

This module handles all database operations for storing network monitoring data.
It demonstrates:
1. Database schema design and management
2. Efficient data persistence patterns
3. Proper SQLite connection handling
4. Data integrity and relationship management
"""

import sqlite3
import threading
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
import contextlib

from dataclasses import dataclass

@dataclass
class MonitoringSession:
    """Represents a monitoring session in the database"""
    session_id: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    total_snapshots: int = 0
    avg_device_count: float = 0.0
    avg_quality_score: float = 0.0


class NetworkDatabaseManager:
    """
    Manages SQLite database for network monitoring data.
    
    This class demonstrates professional database management practices:
    1. Connection pooling and thread safety
    2. Proper schema versioning
    3. Transaction management
    4. Efficient query patterns
    5. Data integrity constraints
    """
    
    def __init__(self, db_path: str = "network_monitoring.db"):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.connection_lock = threading.Lock()
        self._init_database()
        
        print(f"📊 Database initialized: {self.db_path.absolute()}")
    
    def _init_database(self):
        """Initialize database schema with all required tables"""
        
        # SQL Schema - carefully designed for performance and relationships
        schema_sql = """
        -- Devices table: Master registry of all discovered network devices
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT UNIQUE NOT NULL,        -- Device IP (unique identifier)
            mac_address TEXT,                       -- MAC address (can be NULL for some devices)
            hostname TEXT,                          -- Resolved hostname
            device_type TEXT DEFAULT 'unknown',    -- Router, laptop, phone, etc.
            manufacturer TEXT,                      -- Based on MAC OUI lookup
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,           -- Whether device is currently active
            
            UNIQUE(ip_address)                      -- Prevent duplicate IPs
        );
        
        -- Monitoring sessions table: Track when monitoring started/stopped
        CREATE TABLE IF NOT EXISTS monitoring_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP NULL,                -- NULL while session is active
            total_snapshots INTEGER DEFAULT 0,
            avg_device_count REAL DEFAULT 0.0,
            avg_quality_score REAL DEFAULT 0.0,
            notes TEXT                              -- Optional session notes
        );
        
        -- Network snapshots: The heart of our monitoring data
        CREATE TABLE IF NOT EXISTS network_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- Device metrics
            device_count INTEGER NOT NULL,
            
            -- Bandwidth metrics (in Mbps and MB)
            total_upload_mbps REAL NOT NULL,
            total_download_mbps REAL NOT NULL,
            total_usage_mb REAL NOT NULL,
            
            -- Quality metrics
            avg_latency_ms REAL NOT NULL,
            avg_packet_loss REAL NOT NULL,
            overall_quality TEXT NOT NULL,          -- 'Excellent', 'Good', 'Fair', 'Poor'
            
            -- System info
            active_interfaces TEXT,                 -- JSON array of interface names
            tested_device_ip TEXT,                  -- Which device was tested this round
            
            FOREIGN KEY (session_id) REFERENCES monitoring_sessions(id)
        );
        
        -- Device quality tests: Individual device ping results
        CREATE TABLE IF NOT EXISTS device_quality_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id INTEGER NOT NULL,
            device_ip TEXT NOT NULL,
            test_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- Test results
            latency_ms REAL,                        -- NULL if ping failed
            packet_loss_percent REAL DEFAULT 0.0,
            response_time_ms REAL,                  -- Raw ping response time
            test_status TEXT DEFAULT 'success',    -- 'success', 'timeout', 'failed'
            
            FOREIGN KEY (snapshot_id) REFERENCES network_snapshots(id),
            FOREIGN KEY (device_ip) REFERENCES devices(ip_address)
        );
        
        -- Performance indexes for fast queries (crucial for AI later!)
        CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON network_snapshots(timestamp);
        CREATE INDEX IF NOT EXISTS idx_snapshots_session ON network_snapshots(session_id);
        CREATE INDEX IF NOT EXISTS idx_devices_active ON devices(is_active, last_seen);
        CREATE INDEX IF NOT EXISTS idx_quality_tests_device ON device_quality_tests(device_ip, test_timestamp);
        CREATE INDEX IF NOT EXISTS idx_sessions_time ON monitoring_sessions(start_time, end_time);
        
        -- Database metadata
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript(schema_sql)
            
            # Set schema version
            cursor.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (1)")
            conn.commit()
            
            print("✅ Database schema initialized successfully")
    
    @contextlib.contextmanager
    def _get_connection(self):
        """Thread-safe database connection context manager"""
        with self.connection_lock:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            try:
                yield conn
            finally:
                conn.close()
    
    def start_monitoring_session(self, notes: str = None) -> int:
        """
        Start a new monitoring session.
        
        Args:
            notes: Optional notes about this session
            
        Returns:
            Session ID for use in subsequent operations
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO monitoring_sessions (notes) 
                VALUES (?)
            """, (notes,))
            
            session_id = cursor.lastrowid
            conn.commit()
            
            print(f"🚀 Started monitoring session #{session_id}")
            return session_id
    
    def end_monitoring_session(self, session_id: int):
        """End a monitoring session and calculate summary statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Calculate session statistics
            cursor.execute("""
                UPDATE monitoring_sessions 
                SET 
                    end_time = CURRENT_TIMESTAMP,
                    total_snapshots = (
                        SELECT COUNT(*) FROM network_snapshots 
                        WHERE session_id = ?
                    ),
                    avg_device_count = (
                        SELECT AVG(device_count) FROM network_snapshots 
                        WHERE session_id = ?
                    ),
                    avg_quality_score = (
                        SELECT AVG(
                            CASE overall_quality
                                WHEN 'Excellent' THEN 4
                                WHEN 'Good' THEN 3
                                WHEN 'Fair' THEN 2
                                WHEN 'Poor' THEN 1
                                ELSE 0
                            END
                        ) FROM network_snapshots 
                        WHERE session_id = ?
                    )
                WHERE id = ?
            """, (session_id, session_id, session_id, session_id))
            
            conn.commit()
            print(f"🏁 Ended monitoring session #{session_id}")
    
    def save_device(self, device_data: Dict[str, Any]) -> int:
        """
        Save or update device information.
        
        Args:
            device_data: Device information from network discovery
            
        Returns:
            Device ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert or update device
            cursor.execute("""
                INSERT INTO devices (
                    ip_address, mac_address, hostname, last_seen, is_active
                ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, 1)
                ON CONFLICT(ip_address) DO UPDATE SET
                    mac_address = COALESCE(excluded.mac_address, mac_address),
                    hostname = COALESCE(excluded.hostname, hostname),
                    last_seen = CURRENT_TIMESTAMP,
                    is_active = 1
            """, (
                device_data['ip'],
                device_data.get('mac_address'),
                device_data.get('hostname')
            ))
            
            # Get the device ID
            cursor.execute("SELECT id FROM devices WHERE ip_address = ?", (device_data['ip'],))
            device_id = cursor.fetchone()[0]
            
            conn.commit()
            return device_id
    
    def save_network_snapshot(self, session_id: int, snapshot_data: Dict[str, Any]) -> int:
        """
        Save a network monitoring snapshot.
        
        Args:
            session_id: ID of the current monitoring session
            snapshot_data: Monitoring data from MonitoringSnapshot
            
        Returns:
            Snapshot ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO network_snapshots (
                    session_id, device_count, total_upload_mbps, total_download_mbps,
                    total_usage_mb, avg_latency_ms, avg_packet_loss, overall_quality,
                    active_interfaces, tested_device_ip
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                snapshot_data['device_count'],
                snapshot_data['total_upload_mbps'],
                snapshot_data['total_download_mbps'],
                snapshot_data['total_usage_mb'],
                snapshot_data['avg_latency_ms'],
                snapshot_data['avg_packet_loss'],
                snapshot_data['overall_quality'],
                json.dumps(snapshot_data['active_interfaces']),
                snapshot_data.get('tested_device_ip')
            ))
            
            snapshot_id = cursor.lastrowid
            conn.commit()
            return snapshot_id
    
    def save_device_quality_test(self, snapshot_id: int, device_ip: str, 
                                test_result: Dict[str, Any]):
        """Save individual device quality test results"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO device_quality_tests (
                    snapshot_id, device_ip, latency_ms, packet_loss_percent,
                    response_time_ms, test_status
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                snapshot_id,
                device_ip,
                test_result.get('latency_ms'),
                test_result.get('packet_loss_percent', 0.0),
                test_result.get('response_time_ms'),
                test_result.get('test_status', 'success')
            ))
            
            conn.commit()
    
    def get_recent_snapshots(self, limit: int = 100) -> List[Dict]:
        """Get recent network snapshots for analysis"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM network_snapshots 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_device_history(self, device_ip: str, hours: int = 24) -> List[Dict]:
        """Get quality test history for a specific device"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM device_quality_tests 
                WHERE device_ip = ? 
                    AND test_timestamp > datetime('now', '-{} hours')
                ORDER BY test_timestamp DESC
            """.format(hours), (device_ip,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_session_summary(self, session_id: int) -> Optional[Dict]:
        """Get summary statistics for a monitoring session"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    s.*,
                    COUNT(ns.id) as actual_snapshots,
                    MIN(ns.timestamp) as first_snapshot,
                    MAX(ns.timestamp) as last_snapshot
                FROM monitoring_sessions s
                LEFT JOIN network_snapshots ns ON s.id = ns.session_id
                WHERE s.id = ?
                GROUP BY s.id
            """, (session_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old monitoring data to keep database size manageable"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Delete old snapshots and related data
            cursor.execute("""
                DELETE FROM device_quality_tests 
                WHERE snapshot_id IN (
                    SELECT id FROM network_snapshots 
                    WHERE timestamp < datetime('now', '-{} days')
                )
            """.format(days_to_keep))
            
            cursor.execute("""
                DELETE FROM network_snapshots 
                WHERE timestamp < datetime('now', '-{} days')
            """.format(days_to_keep))
            
            deleted_snapshots = cursor.rowcount
            
            # Mark inactive devices
            cursor.execute("""
                UPDATE devices 
                SET is_active = 0 
                WHERE last_seen < datetime('now', '-{} days')
            """.format(days_to_keep))
            
            conn.commit()
            print(f"🧹 Cleaned up {deleted_snapshots} old snapshots")


# Utility functions for data analysis
def calculate_quality_score(latency_ms: float, packet_loss: float) -> str:
    """
    Calculate overall connection quality based on latency and packet loss.
    
    This uses industry-standard network quality metrics:
    - Excellent: <20ms latency, <1% loss
    - Good: <50ms latency, <3% loss  
    - Fair: <100ms latency, <10% loss
    - Poor: >100ms latency or >10% loss
    """
    if latency_ms < 20 and packet_loss < 1:
        return "Excellent"
    elif latency_ms < 50 and packet_loss < 3:
        return "Good"
    elif latency_ms < 100 and packet_loss < 10:
        return "Fair"
    else:
        return "Poor"


if __name__ == "__main__":
    # Quick test of database functionality
    print("🧪 Testing Database Manager...")
    
    db = NetworkDatabaseManager("test_network.db")
    
    # Start a test session
    session_id = db.start_monitoring_session("Test session")
    
    # Save some test data
    test_device = {
        'ip': '192.168.1.100',
        'mac_address': 'AA:BB:CC:DD:EE:FF',
        'hostname': 'test-device'
    }
    
    device_id = db.save_device(test_device)
    print(f"✅ Saved device ID: {device_id}")
    
    # Save test snapshot
    test_snapshot = {
        'device_count': 5,
        'total_upload_mbps': 10.5,
        'total_download_mbps': 50.2,
        'total_usage_mb': 1024.0,
        'avg_latency_ms': 25.5,
        'avg_packet_loss': 0.5,
        'overall_quality': 'Good',
        'active_interfaces': ['en0', 'wlan0'],
        'tested_device_ip': '192.168.1.100'
    }
    
    snapshot_id = db.save_network_snapshot(session_id, test_snapshot)
    print(f"✅ Saved snapshot ID: {snapshot_id}")
    
    # End session
    db.end_monitoring_session(session_id)
    
    # Get session summary
    summary = db.get_session_summary(session_id)
    print(f"📊 Session summary: {summary}")
    
    print("✅ Database Manager test completed!") 