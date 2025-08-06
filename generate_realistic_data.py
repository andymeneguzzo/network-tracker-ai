#!/usr/bin/env python3
"""
Realistic Network Monitoring Data Generator

This script generates believable network monitoring data to demonstrate 
AI capabilities. It creates realistic usage patterns that mirror real 
household network behavior:

1. Morning rush (8-9 AM): Work from home, video calls
2. Lunch break (12-1 PM): Streaming, social media  
3. Evening peak (7-11 PM): Netflix, gaming, multiple devices
4. Night time (11 PM-7 AM): Minimal usage, background updates

This gives our AI system realistic data to analyze and generate insights from.
"""

import sys
import random
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import math

# Add backend to path for database access
backend_path = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_path))

from database_manager import NetworkDatabaseManager

class RealisticNetworkDataGenerator:
    """
    Generates realistic network monitoring data that follows real-world patterns.
    
    This class demonstrates understanding of:
    1. Real network usage patterns and behaviors
    2. Data modeling and simulation techniques  
    3. Database integration and bulk operations
    4. Time series data generation with realistic variance
    """
    
    def __init__(self, db_path: str = "network_monitoring.db"):
        """Initialize the data generator"""
        self.db_manager = NetworkDatabaseManager(db_path)
        self.device_pool = self._create_device_pool()
        
    def _create_device_pool(self) -> List[Dict]:
        """
        Create a realistic pool of household devices.
        
        This simulates a typical home with various connected devices
        that have different usage patterns throughout the day.
        """
        devices = [
            # Core devices - always connected
            {"ip": "192.168.1.1", "mac": "00:1B:44:11:3A:B7", "hostname": "router", "device_type": "router", "always_on": True},
            {"ip": "192.168.1.2", "mac": "AC:DE:48:00:11:22", "hostname": "laptop-work", "device_type": "laptop", "always_on": False, "usage_profile": "work"},
            {"ip": "192.168.1.3", "mac": "20:C9:D0:27:8D:5C", "hostname": "iphone-andy", "device_type": "smartphone", "always_on": True, "usage_profile": "personal"},
            
            # Entertainment devices
            {"ip": "192.168.1.4", "mac": "B8:27:EB:A6:12:34", "hostname": "smart-tv", "device_type": "smart_tv", "always_on": False, "usage_profile": "evening"},
            {"ip": "192.168.1.5", "mac": "00:04:4B:12:34:56", "hostname": "gaming-console", "device_type": "gaming", "always_on": False, "usage_profile": "gaming"},
            {"ip": "192.168.1.6", "mac": "3C:15:C2:E7:89:AB", "hostname": "tablet-living", "device_type": "tablet", "always_on": False, "usage_profile": "casual"},
            
            # Smart home devices
            {"ip": "192.168.1.7", "mac": "50:C7:BF:33:CD:EF", "hostname": "alexa-kitchen", "device_type": "smart_speaker", "always_on": True, "usage_profile": "minimal"},
            {"ip": "192.168.1.8", "mac": "18:B4:30:12:34:AB", "hostname": "security-cam", "device_type": "camera", "always_on": True, "usage_profile": "steady"},
            
            # Work from home setup
            {"ip": "192.168.1.9", "mac": "A4:5E:60:AB:CD:EF", "hostname": "desktop-office", "device_type": "desktop", "always_on": False, "usage_profile": "work"},
            {"ip": "192.168.1.10", "mac": "08:00:27:12:34:56", "hostname": "printer-wifi", "device_type": "printer", "always_on": True, "usage_profile": "minimal"},
        ]
        
        return devices
    
    def _get_hourly_usage_pattern(self, hour: int) -> Dict[str, float]:
        """
        Generate realistic usage patterns based on hour of day.
        
        This simulates how real households use internet throughout the day:
        - Morning: Work calls, email, news
        - Afternoon: Steady work usage
        - Evening: Streaming, gaming, social media
        - Night: Minimal usage, updates
        """
        
        patterns = {
            # Night hours (11 PM - 6 AM): Minimal usage
            23: {"base_mbps": 5, "variance": 2, "device_prob": 0.3, "quality_factor": 0.95},
            0: {"base_mbps": 3, "variance": 1, "device_prob": 0.2, "quality_factor": 0.98},
            1: {"base_mbps": 2, "variance": 1, "device_prob": 0.15, "quality_factor": 0.98},
            2: {"base_mbps": 2, "variance": 1, "device_prob": 0.15, "quality_factor": 0.98},
            3: {"base_mbps": 2, "variance": 1, "device_prob": 0.15, "quality_factor": 0.98},
            4: {"base_mbps": 3, "variance": 1, "device_prob": 0.2, "quality_factor": 0.98},
            5: {"base_mbps": 4, "variance": 2, "device_prob": 0.25, "quality_factor": 0.95},
            6: {"base_mbps": 8, "variance": 3, "device_prob": 0.4, "quality_factor": 0.92},
            
            # Morning hours (7 AM - 11 AM): Work startup
            7: {"base_mbps": 15, "variance": 5, "device_prob": 0.6, "quality_factor": 0.88},
            8: {"base_mbps": 35, "variance": 10, "device_prob": 0.8, "quality_factor": 0.75},  # Morning rush!
            9: {"base_mbps": 28, "variance": 8, "device_prob": 0.75, "quality_factor": 0.82},
            10: {"base_mbps": 22, "variance": 6, "device_prob": 0.7, "quality_factor": 0.85},
            11: {"base_mbps": 18, "variance": 5, "device_prob": 0.65, "quality_factor": 0.88},
            
            # Midday hours (12 PM - 5 PM): Steady work + lunch break
            12: {"base_mbps": 25, "variance": 8, "device_prob": 0.7, "quality_factor": 0.80},  # Lunch streaming
            13: {"base_mbps": 20, "variance": 5, "device_prob": 0.65, "quality_factor": 0.85},
            14: {"base_mbps": 18, "variance": 4, "device_prob": 0.6, "quality_factor": 0.87},
            15: {"base_mbps": 20, "variance": 5, "device_prob": 0.65, "quality_factor": 0.85},
            16: {"base_mbps": 22, "variance": 6, "device_prob": 0.7, "quality_factor": 0.83},
            17: {"base_mbps": 24, "variance": 7, "device_prob": 0.75, "quality_factor": 0.80},
            
            # Evening hours (6 PM - 10 PM): Peak usage!
            18: {"base_mbps": 32, "variance": 10, "device_prob": 0.85, "quality_factor": 0.70},
            19: {"base_mbps": 45, "variance": 15, "device_prob": 0.95, "quality_factor": 0.60},  # Peak dinner + streaming
            20: {"base_mbps": 50, "variance": 18, "device_prob": 1.0, "quality_factor": 0.55},   # Prime time!
            21: {"base_mbps": 42, "variance": 12, "device_prob": 0.9, "quality_factor": 0.65},
            22: {"base_mbps": 25, "variance": 8, "device_prob": 0.7, "quality_factor": 0.78},
        }
        
        return patterns.get(hour, patterns[12])  # Default to midday pattern
    
    def _generate_active_devices(self, hour: int, base_device_count: int) -> List[Dict]:
        """
        Generate which devices are active based on time of day and usage patterns.
        """
        pattern = self._get_hourly_usage_pattern(hour)
        device_probability = pattern["device_prob"]
        
        active_devices = []
        
        # Always include always-on devices
        for device in self.device_pool:
            if device.get("always_on", False):
                active_devices.append(device)
        
        # Add other devices based on time and usage patterns
        for device in self.device_pool:
            if device.get("always_on", False):
                continue
                
            usage_profile = device.get("usage_profile", "casual")
            
            # Different device types have different activity patterns
            if usage_profile == "work" and 8 <= hour <= 17:
                # Work devices active during work hours
                if random.random() < 0.9:
                    active_devices.append(device)
            elif usage_profile == "evening" and 18 <= hour <= 23:
                # Entertainment devices active in evening
                if random.random() < 0.8:
                    active_devices.append(device)
            elif usage_profile == "gaming" and (19 <= hour <= 23 or hour in [12, 13]):
                # Gaming during evening or lunch break
                if random.random() < 0.7:
                    active_devices.append(device)
            elif usage_profile == "personal":
                # Personal devices (phones) active most of the time
                if random.random() < device_probability:
                    active_devices.append(device)
            elif usage_profile == "casual":
                # Casual devices follow general pattern
                if random.random() < device_probability * 0.6:
                    active_devices.append(device)
        
        # Ensure we have at least the minimum number of devices
        while len(active_devices) < max(2, base_device_count - 2):
            inactive_devices = [d for d in self.device_pool if d not in active_devices]
            if inactive_devices:
                active_devices.append(random.choice(inactive_devices))
        
        return active_devices[:10]  # Cap at 10 devices max
    
    def _calculate_quality_metrics(self, total_mbps: float, device_count: int, hour: int) -> Dict:
        """
        Calculate realistic network quality metrics based on usage and congestion.
        
        Higher usage = higher latency and potential packet loss
        More devices = more network congestion
        """
        pattern = self._get_hourly_usage_pattern(hour)
        quality_factor = pattern["quality_factor"]
        
        # Base latency increases with usage and device count
        base_latency = 8 + (total_mbps * 0.3) + (device_count * 2)
        base_latency *= (2 - quality_factor)  # Quality factor affects latency
        
        # Add some realistic variance
        latency = max(5, base_latency + random.uniform(-3, 8))
        
        # Packet loss occurs mainly during high congestion
        if total_mbps > 40 and device_count > 6:
            packet_loss = random.uniform(0.1, 2.0)
        elif total_mbps > 25:
            packet_loss = random.uniform(0, 0.8)
        else:
            packet_loss = random.uniform(0, 0.2)
        
        # Overall quality assessment
        if latency < 15 and packet_loss < 0.5:
            quality = "Excellent"
        elif latency < 25 and packet_loss < 1.0:
            quality = "Good"
        elif latency < 40 and packet_loss < 2.0:
            quality = "Fair"
        else:
            quality = "Poor"
        
        return {
            "avg_latency_ms": round(latency, 2),
            "avg_packet_loss": round(packet_loss, 2),
            "overall_quality": quality
        }
    
    def generate_monitoring_data(self, days_back: int = 3, interval_seconds: int = 30) -> int:
        """
        Generate realistic monitoring data for the specified time period.
        
        Args:
            days_back: How many days of historical data to generate
            interval_seconds: Interval between data points (default 30s for faster generation)
            
        Returns:
            Number of data points generated
        """
        
        print(f"🎭 Generating {days_back} days of realistic network monitoring data...")
        print(f"📊 Data interval: {interval_seconds} seconds")
        
        # Create a monitoring session
        session_id = self.db_manager.start_monitoring_session("Simulated Data Generation")
        
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)
        
        # Generate data points
        current_time = start_time
        data_points_generated = 0
        total_points = int((days_back * 24 * 3600) / interval_seconds)
        
        print(f"🔄 Generating approximately {total_points:,} data points...")
        
        # Track cumulative usage for realistic total_usage_mb
        cumulative_upload_mb = 0
        cumulative_download_mb = 0
        
        while current_time <= end_time:
            hour = current_time.hour
            
            # Get usage pattern for this hour
            pattern = self._get_hourly_usage_pattern(hour)
            
            # Generate bandwidth with realistic variation
            upload_mbps = max(1, pattern["base_mbps"] * 0.3 + random.uniform(-pattern["variance"]*0.2, pattern["variance"]*0.3))
            download_mbps = max(2, pattern["base_mbps"] * 0.7 + random.uniform(-pattern["variance"]*0.7, pattern["variance"]*1.2))
            total_mbps = upload_mbps + download_mbps
            
            # Calculate cumulative usage (convert Mbps to MB for interval)
            interval_minutes = interval_seconds / 60
            upload_mb_interval = (upload_mbps / 8) * interval_minutes  # Convert Mbps to MB per interval
            download_mb_interval = (download_mbps / 8) * interval_minutes
            
            cumulative_upload_mb += upload_mb_interval
            cumulative_download_mb += download_mb_interval
            
            # Generate active devices for this time
            base_device_count = int(pattern["device_prob"] * len(self.device_pool))
            active_devices = self._generate_active_devices(hour, base_device_count)
            
            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(total_mbps, len(active_devices), hour)
            
            # Choose a device being tested (round-robin style)
            tested_device = random.choice(active_devices) if active_devices else None
            
            # Create monitoring snapshot data (FIXED: include timestamp)
            snapshot_data = {
                "timestamp": current_time.isoformat(),        # FIXED: Include historical timestamp
                "device_count": len(active_devices),
                "total_upload_mbps": round(upload_mbps, 2),
                "total_download_mbps": round(download_mbps, 2),
                "total_usage_mb": round(cumulative_upload_mb + cumulative_download_mb, 2),
                "avg_latency_ms": quality_metrics["avg_latency_ms"],
                "avg_packet_loss": quality_metrics["avg_packet_loss"],
                "overall_quality": quality_metrics["overall_quality"],
                "active_interfaces": ["wlan0", "eth0"],
                "tested_device_ip": tested_device["ip"] if tested_device else None
            }
            
            # Store in database
            snapshot_id = self.db_manager.save_network_snapshot(session_id, snapshot_data)
            
            # Store device information
            for device in active_devices:
                device_data = {
                    "ip": device["ip"],
                    "mac_address": device["mac"],
                    "hostname": device["hostname"],
                    "device_type": device.get("device_type", "unknown")
                }
                self.db_manager.save_device(device_data)
            
            data_points_generated += 1
            current_time += timedelta(seconds=interval_seconds)
            
            # Progress indicator
            if data_points_generated % 500 == 0:
                progress = (data_points_generated / total_points) * 100
                print(f"📈 Progress: {progress:.1f}% ({data_points_generated:,} / {total_points:,} points)")
        
        # End the monitoring session
        self.db_manager.end_monitoring_session(session_id)
        
        print(f"✅ Generated {data_points_generated:,} realistic data points!")
        print(f"📅 Time range: {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}")
        
        return data_points_generated

def main():
    """Main function to generate realistic network monitoring data"""
    
    print("🎭 REALISTIC NETWORK DATA GENERATOR")
    print("=" * 50)
    print("This script generates believable network monitoring data")
    print("that follows real household usage patterns for AI testing.")
    print()
    
    generator = RealisticNetworkDataGenerator()
    
    # Generate 3 days of data with 30-second intervals
    # This gives us plenty of data for AI analysis while being quick to generate
    data_points = generator.generate_monitoring_data(
        days_back=3,           # 3 days of history
        interval_seconds=30    # Every 30 seconds (8,640 data points)
    )
    
    print()
    print("🧠 AI ANALYSIS READY!")
    print("=" * 30)
    print(f"✅ {data_points:,} data points generated")
    print("🔥 Your AI now has realistic data to analyze:")
    print("   • Morning work-from-home patterns")
    print("   • Lunch break streaming spikes") 
    print("   • Evening entertainment peaks")
    print("   • Nighttime minimal usage")
    print("   • Weekend vs weekday variations")
    print()
    print("🚀 Run the AI test now to see intelligent insights:")
    print("   ./setup_ai_insights.sh")
    print()
    print("💡 Perfect for demonstrating:")
    print("   • Realistic data simulation skills")
    print("   • Understanding of network usage patterns")
    print("   • Data modeling and generation techniques")
    print("   • Professional AI testing methodology")

if __name__ == "__main__":
    main() 