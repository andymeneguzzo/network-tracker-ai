#!/bin/bash

echo "🎭 Realistic Network Data Generation Setup"
echo "=========================================="

# Check current environment
echo "📍 Current environment: $CONDA_DEFAULT_ENV"
echo "🐍 Current Python: $(which python)"

# Check if virtual environment already exists
if [ -d "network_monitor_env" ]; then
    echo "✅ Virtual environment already exists"
else
    echo "❌ Virtual environment not found"
    echo "💡 Please run the AI setup first:"
    echo "   ./setup_ai_insights.sh"
    exit 1
fi

# Activate virtual environment
echo ""
echo "🔌 Activating virtual environment..."
source network_monitor_env/bin/activate

if [ $? -ne 0 ]; then
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

echo "✅ Virtual environment activated"

# Test database connectivity
echo ""
echo "🗄️  Testing database connectivity..."

python -c "
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))

try:
    from database_manager import NetworkDatabaseManager
    
    # Test connection
    db = NetworkDatabaseManager()
    print('✅ Database connection successful')
    
    # Check current data
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM network_snapshots')
        count = cursor.fetchone()[0]
        print(f'📊 Current data points: {count:,}')
        
        if count > 0:
            cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM network_snapshots')
            time_range = cursor.fetchone()
            print(f'📅 Time range: {time_range[0]} to {time_range[1]}')
    
except Exception as e:
    print(f'❌ Database test failed: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Database connectivity test failed"
    exit 1
fi

# Ask user about existing data
echo ""
echo "⚠️  DATA GENERATION WARNING"
echo "=========================="
echo "This script will generate realistic network monitoring data."
echo ""
echo "🔍 Options:"
echo "1. Generate NEW data (recommended for testing)"
echo "2. ADD to existing data"
echo "3. CLEAR existing data and start fresh"
echo ""
read -p "Choose option (1-3): " choice

case $choice in
    1)
        echo "✅ Will generate new data alongside existing data"
        ;;
    2)
        echo "✅ Will add to existing data"
        ;;
    3)
        echo "🗑️  Clearing existing data..."
        python -c "
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))
from database_manager import NetworkDatabaseManager

db = NetworkDatabaseManager()
with db._get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute('DELETE FROM device_quality_tests')
    cursor.execute('DELETE FROM network_snapshots') 
    cursor.execute('DELETE FROM monitoring_sessions')
    cursor.execute('DELETE FROM devices')
    conn.commit()
    print('✅ Database cleared successfully')
"
        ;;
    *)
        echo "❌ Invalid choice. Exiting."
        exit 1
        ;;
esac

# Run data generation
echo ""
echo "🎭 Running realistic data generation..."
echo "======================================"

python generate_realistic_data.py

generation_result=$?

echo ""
echo "📊 Data Generation Complete!"
echo "============================"

if [ $generation_result -eq 0 ]; then
    echo "✅ Realistic data generation completed successfully!"
    echo ""
    echo "🎯 What was generated:"
    echo "   • 3 days of realistic network monitoring data"
    echo "   • ~8,640 data points (30-second intervals)"
    echo "   • Morning work patterns"
    echo "   • Lunch break streaming spikes"
    echo "   • Evening entertainment peaks"
    echo "   • Realistic device connections"
    echo "   • Quality metrics with congestion effects"
    echo ""
    echo "🤖 Ready for AI analysis!"
    echo "========================"
    echo "Your AI now has realistic data to demonstrate:"
    echo "   📊 Peak usage hour detection"
    echo "   🔍 Pattern recognition capabilities"
    echo "   💡 Intelligent recommendations"
    echo "   📈 Professional insights generation"
    echo ""
    echo "🚀 Next step - Run AI analysis:"
    echo "   ./setup_ai_insights.sh"
    echo ""
    echo "💼 Perfect for showing:"
    echo "   • Data simulation and modeling skills"
    echo "   • Understanding of real-world network patterns"
    echo "   • Professional AI testing methodology"
    
else
    echo "❌ Data generation encountered issues"
    echo ""
    echo "🔧 Troubleshooting:"
    echo "   1. Check database permissions"
    echo "   2. Ensure virtual environment is properly activated"
    echo "   3. Verify all dependencies are installed"
fi

# Show final database status (FIXED: correct column names)
echo ""
echo "📈 Final Database Status:"
python -c "
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))
from database_manager import NetworkDatabaseManager

try:
    db = NetworkDatabaseManager()
    with db._get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM network_snapshots')
        snapshots = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT ip_address) FROM devices WHERE is_active = 1')
        devices = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM monitoring_sessions')
        sessions = cursor.fetchone()[0]
        
        print(f'📊 Network snapshots: {snapshots:,}')
        print(f'📱 Active devices: {devices}')
        print(f'🕐 Monitoring sessions: {sessions}')
        
        if snapshots > 0:
            cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM network_snapshots')
            time_range = cursor.fetchone()
            print(f'📅 Data range: {time_range[0]} to {time_range[1]}')

except Exception as e:
    print(f'❌ Could not read database status: {e}')
"

# Deactivate virtual environment
deactivate

echo ""
echo "🎓 Skills Demonstrated:"
echo "   ✅ Realistic data modeling and simulation"
echo "   ✅ Understanding of network usage patterns"  
echo "   ✅ Database integration and bulk operations"
echo "   ✅ Professional testing data generation"
echo "   ✅ Time series data creation with variance" 