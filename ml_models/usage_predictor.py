#!/usr/bin/env python3
"""
Network Usage Pattern Predictor

This AI module analyzes historical network monitoring data to predict:
1. Busiest hours of the day
2. Peak usage patterns
3. Device activity forecasts
4. Network optimization recommendations

Uses time series analysis and pattern recognition to provide actionable insights.
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
import sys

# Add backend to path for database access
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

from database_manager import NetworkDatabaseManager

@dataclass
class UsageInsight:
    """Represents an AI-generated insight about network usage"""
    insight_type: str           # 'peak_hour', 'pattern', 'recommendation'
    title: str                  # Human-readable title
    description: str            # Detailed explanation
    confidence: float           # How confident AI is (0.0-1.0)
    data_points: int           # How much data this is based on
    time_period: str           # 'hourly', 'daily', 'weekly'
    supporting_data: Dict      # Charts, numbers, etc.

class NetworkUsagePredictor:
    """
    AI-powered network usage pattern analyzer.
    
    This class demonstrates several AI/ML concepts:
    1. Time series data analysis
    2. Pattern recognition in temporal data
    3. Statistical analysis for insights
    4. Data visualization for interpretation
    5. Predictive modeling for network optimization
    """
    
    def __init__(self, db_path: str = "network_monitoring.db"):
        """Initialize the predictor with database connection"""
        self.db_manager = NetworkDatabaseManager(db_path)
        self.insights_cache = []
        
    def analyze_hourly_patterns(self, days_back: int = 7) -> List[UsageInsight]:
        """
        Analyze network usage patterns by hour of day.
        
        This is like analyzing a restaurant's customer flow:
        - Which hours are consistently busy?
        - When do people use the most bandwidth?
        - What's the typical device count throughout the day?
        
        Args:
            days_back: How many days of history to analyze
            
        Returns:
            List of insights about hourly usage patterns
        """
        print(f"🔍 Analyzing hourly usage patterns (last {days_back} days)...")
        
        # Step 1: Get historical data from database
        data = self._fetch_hourly_aggregated_data(days_back)
        
        if len(data) < 24:  # Need at least 24 hours of data
            return [UsageInsight(
                insight_type="insufficient_data",
                title="Not Enough Data Yet",
                description=f"Need at least 24 hours of data, but only have {len(data)} data points. Keep monitoring!",
                confidence=1.0,
                data_points=len(data),
                time_period="hourly",
                supporting_data={}
            )]
        
        insights = []
        
        # Step 2: Find peak usage hours
        peak_insights = self._analyze_peak_hours(data)
        insights.extend(peak_insights)
        
        # Step 3: Identify usage patterns
        pattern_insights = self._analyze_usage_patterns(data)
        insights.extend(pattern_insights)
        
        # Step 4: Generate recommendations
        recommendation_insights = self._generate_optimization_recommendations(data)
        insights.extend(recommendation_insights)
        
        return insights
    
    def _fetch_hourly_aggregated_data(self, days_back: int) -> pd.DataFrame:
        """
        Fetch and aggregate monitoring data by hour.
        
        This transforms our second-by-second data into hourly summaries,
        making it easier to spot patterns and trends.
        """
        
        # Calculate the time range to analyze
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)
        
        # SQL query to get hourly aggregated data
        query = """
        SELECT 
            -- Time grouping: Convert timestamp to hour of day (0-23)
            CAST(strftime('%H', timestamp) AS INTEGER) as hour_of_day,
            DATE(timestamp) as date,
            
            -- Usage metrics (averaged per hour)
            AVG(device_count) as avg_devices,
            AVG(total_upload_mbps + total_download_mbps) as avg_total_mbps,
            AVG(total_usage_mb) as avg_usage_mb,
            
            -- Quality metrics
            AVG(avg_latency_ms) as avg_latency,
            AVG(avg_packet_loss) as avg_packet_loss,
            
            -- Count how many data points we have per hour
            COUNT(*) as sample_count,
            
            -- Time range for this hour
            MIN(timestamp) as hour_start,
            MAX(timestamp) as hour_end
            
        FROM network_snapshots 
        WHERE timestamp >= ? AND timestamp <= ?
        GROUP BY DATE(timestamp), CAST(strftime('%H', timestamp) AS INTEGER)
        ORDER BY date, hour_of_day
        """
        
        # Execute query and convert to pandas DataFrame
        with self.db_manager._get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=[
                start_time.isoformat(),
                end_time.isoformat()
            ])
        
        # Convert timestamp columns to datetime
        df['hour_start'] = pd.to_datetime(df['hour_start'])
        df['hour_end'] = pd.to_datetime(df['hour_end'])
        df['date'] = pd.to_datetime(df['date'])
        
        print(f"📊 Fetched {len(df)} hourly data points for analysis")
        return df
    
    def _analyze_peak_hours(self, data: pd.DataFrame) -> List[UsageInsight]:
        """
        Identify the busiest hours based on bandwidth usage and device count.
        
        Like finding rush hour at a subway station - when do most people
        use the network and consume the most bandwidth?
        """
        insights = []
        
        # Group by hour of day and calculate averages
        hourly_summary = data.groupby('hour_of_day').agg({
            'avg_total_mbps': 'mean',
            'avg_devices': 'mean',
            'avg_usage_mb': 'mean',
            'sample_count': 'sum'
        }).round(2)
        
        # Find top 3 busiest hours by bandwidth
        top_bandwidth_hours = hourly_summary.nlargest(3, 'avg_total_mbps')
        
        # Find top 3 busiest hours by device count
        top_device_hours = hourly_summary.nlargest(3, 'avg_devices')
        
        # Generate bandwidth peak insight
        peak_hours_bandwidth = []
        for hour, row in top_bandwidth_hours.iterrows():
            time_str = f"{hour:02d}:00-{hour+1:02d}:00"
            peak_hours_bandwidth.append(f"{time_str} ({row['avg_total_mbps']:.1f} Mbps)")
        
        bandwidth_insight = UsageInsight(
            insight_type="peak_hour",
            title="🚀 Peak Bandwidth Hours Identified",
            description=f"Your network's busiest hours for data usage are: {', '.join(peak_hours_bandwidth)}. "
                       f"During these times, you typically see {top_bandwidth_hours.iloc[0]['avg_total_mbps']:.1f} Mbps "
                       f"of total network activity.",
            confidence=min(0.95, len(data) / 168),  # More confidence with more data
            data_points=len(data),
            time_period="hourly",
            supporting_data={
                "top_bandwidth_hours": top_bandwidth_hours.to_dict(),
                "hourly_bandwidth_chart": hourly_summary['avg_total_mbps'].to_dict()
            }
        )
        insights.append(bandwidth_insight)
        
        # Generate device count peak insight
        peak_hours_devices = []
        for hour, row in top_device_hours.iterrows():
            time_str = f"{hour:02d}:00-{hour+1:02d}:00"
            peak_hours_devices.append(f"{time_str} ({row['avg_devices']:.1f} devices)")
        
        device_insight = UsageInsight(
            insight_type="peak_hour",
            title="📱 Peak Device Connection Hours",
            description=f"Most devices connect during: {', '.join(peak_hours_devices)}. "
                       f"Peak time averages {top_device_hours.iloc[0]['avg_devices']:.1f} connected devices.",
            confidence=min(0.95, len(data) / 168),
            data_points=len(data),
            time_period="hourly",
            supporting_data={
                "top_device_hours": top_device_hours.to_dict(),
                "hourly_device_chart": hourly_summary['avg_devices'].to_dict()
            }
        )
        insights.append(device_insight)
        
        return insights
    
    def _analyze_usage_patterns(self, data: pd.DataFrame) -> List[UsageInsight]:
        """
        Detect recurring patterns in network usage.
        
        Like recognizing that a coffee shop is busy in the morning
        and evening but quiet in the afternoon.
        """
        insights = []
        
        hourly_summary = data.groupby('hour_of_day').agg({
            'avg_total_mbps': 'mean',
            'avg_devices': 'mean'
        }).round(2)
        
        # Classify hours into usage periods
        max_bandwidth = hourly_summary['avg_total_mbps'].max()
        threshold_high = max_bandwidth * 0.7
        threshold_low = max_bandwidth * 0.3
        
        high_usage_hours = hourly_summary[hourly_summary['avg_total_mbps'] >= threshold_high].index.tolist()
        low_usage_hours = hourly_summary[hourly_summary['avg_total_mbps'] <= threshold_low].index.tolist()
        
        # Create human-readable time ranges
        def hours_to_ranges(hours):
            if not hours:
                return []
            hours = sorted(hours)
            ranges = []
            start = hours[0]
            prev = hours[0]
            
            for hour in hours[1:]:
                if hour != prev + 1:  # Gap found
                    ranges.append(f"{start:02d}:00-{prev+1:02d}:00")
                    start = hour
                prev = hour
            ranges.append(f"{start:02d}:00-{prev+1:02d}:00")
            return ranges
        
        high_ranges = hours_to_ranges(high_usage_hours)
        low_ranges = hours_to_ranges(low_usage_hours)
        
        pattern_insight = UsageInsight(
            insight_type="pattern",
            title="⏰ Daily Usage Pattern Detected",
            description=f"High usage periods: {', '.join(high_ranges) if high_ranges else 'None detected'}. "
                       f"Low usage periods: {', '.join(low_ranges) if low_ranges else 'None detected'}. "
                       f"This pattern suggests {'typical home usage with peak evening activity' if any(h >= 18 for h in high_usage_hours) else 'consistent usage throughout the day'}.",
            confidence=0.85,
            data_points=len(data),
            time_period="daily",
            supporting_data={
                "high_usage_hours": high_usage_hours,
                "low_usage_hours": low_usage_hours,
                "usage_classification": {
                    "high_threshold_mbps": threshold_high,
                    "low_threshold_mbps": threshold_low
                }
            }
        )
        insights.append(pattern_insight)
        
        return insights
    
    def _generate_optimization_recommendations(self, data: pd.DataFrame) -> List[UsageInsight]:
        """
        Generate AI-powered recommendations for network optimization.
        
        Like a consultant analyzing business patterns and suggesting
        improvements based on data trends.
        """
        insights = []
        
        hourly_summary = data.groupby('hour_of_day').agg({
            'avg_total_mbps': 'mean',
            'avg_devices': 'mean',
            'avg_latency': 'mean'
        }).round(2)
        
        # Find potential optimization opportunities
        max_bandwidth = hourly_summary['avg_total_mbps'].max()
        min_bandwidth = hourly_summary['avg_total_mbps'].min()
        
        # Check for high latency during peak hours
        peak_hours = hourly_summary.nlargest(3, 'avg_total_mbps').index
        peak_latency = hourly_summary.loc[peak_hours, 'avg_latency'].mean()
        
        recommendations = []
        
        if peak_latency > 50:  # High latency during peak
            recommendations.append(
                "Consider upgrading your internet plan or optimizing device priorities during peak hours"
            )
        
        if max_bandwidth / min_bandwidth > 3:  # High variance in usage
            recommendations.append(
                "Your network has significant usage variation - consider scheduling heavy downloads during low-usage periods"
            )
        
        # Device density recommendation
        max_devices = hourly_summary['avg_devices'].max()
        if max_devices > 8:
            recommendations.append(
                "With 8+ devices during peak times, consider a mesh network or additional access points for better coverage"
            )
        
        if recommendations:
            rec_insight = UsageInsight(
                insight_type="recommendation",
                title="💡 AI-Powered Optimization Recommendations",
                description=f"Based on your usage patterns, here are {len(recommendations)} recommendations: " + 
                           "; ".join(recommendations),
                confidence=0.75,
                data_points=len(data),
                time_period="overall",
                supporting_data={
                    "peak_latency_ms": peak_latency,
                    "usage_variance_ratio": max_bandwidth / min_bandwidth,
                    "max_concurrent_devices": max_devices,
                    "recommendations": recommendations
                }
            )
            insights.append(rec_insight)
        
        return insights
    
    def generate_usage_report(self, days_back: int = 7) -> str:
        """
        Generate a comprehensive human-readable report of network usage insights.
        
        This creates a beautiful report that you can show to recruiters
        to demonstrate your AI integration capabilities.
        """
        print("🤖 Generating AI-powered network usage report...")
        
        insights = self.analyze_hourly_patterns(days_back)
        
        report_lines = [
            "=" * 60,
            "🤖 AI-POWERED NETWORK USAGE INSIGHTS REPORT",
            "=" * 60,
            f"📅 Analysis Period: Last {days_back} days",
            f"🕐 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]
        
        for i, insight in enumerate(insights, 1):
            report_lines.extend([
                f"{i}. {insight.title}",
                "-" * len(f"{i}. {insight.title}"),
                f"📊 Confidence: {insight.confidence:.1%}",
                f"📈 Data Points: {insight.data_points:,}",
                f"⏱️  Period: {insight.time_period}",
                "",
                insight.description,
                "",
            ])
        
        report_lines.extend([
            "=" * 60,
            "🎯 Next Steps:",
            "• Continue monitoring to improve AI accuracy",
            "• Implement recommendations for better performance", 
            "• Check back in a few days for updated insights",
            "=" * 60,
        ])
        
        return "\n".join(report_lines)

if __name__ == "__main__":
    # Demo the AI predictor
    predictor = NetworkUsagePredictor()
    
    print("🚀 Testing AI Network Usage Predictor")
    print("=" * 50)
    
    # Generate and display insights
    report = predictor.generate_usage_report(days_back=7)
    print(report) 