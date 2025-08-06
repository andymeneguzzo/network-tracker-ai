#!/bin/bash

echo "🚀 Database Integration Test Setup"
echo "=================================="

# Check current environment
echo "📍 Current environment: $CONDA_DEFAULT_ENV"
echo "🐍 Current Python: $(which python)"

# Check if virtual environment already exists
if [ -d "network_monitor_env" ]; then
    echo "✅ Virtual environment already exists"
else
    # Create virtual environment
    echo ""
    echo "🔧 Creating virtual environment..."
    python3 -m venv network_monitor_env
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment"
        echo "💡 Try: python -m venv network_monitor_env"
        exit 1
    fi
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source network_monitor_env/bin/activate

# Confirm activation
echo "✅ Virtual environment activated"
echo "🐍 New Python path: $(which python)"
echo "📦 Pip path: $(which pip)"

# Upgrade pip
echo ""
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies for database integration
echo ""
echo "📦 Installing required packages for database integration..."
pip install psutil ping3

# Additional packages that might be useful for database work
echo "📦 Installing optional database utilities..."
pip install --quiet sqlite-utils 2>/dev/null || echo "📝 Note: sqlite-utils not installed (optional)"

# Verify installations
echo ""
echo "🔍 Verifying installations..."
python -c "import psutil; print('✅ psutil:', psutil.__version__)"
python -c "import ping3; print('✅ ping3: installed')"
python -c "import sqlite3; print('✅ sqlite3:', sqlite3.sqlite_version)"
python -c "import threading; print('✅ threading: built-in module')"
python -c "import json; print('✅ json: built-in module')"
python -c "import pathlib; print('✅ pathlib: built-in module')"
python -c "import contextlib; print('✅ contextlib: built-in module')"

# Check Python version for dataclasses
echo ""
echo "🔍 Checking Python version compatibility..."
python -c "
import sys
print(f'✅ Python version: {sys.version}')
if sys.version_info >= (3, 7):
    import dataclasses
    print('✅ dataclasses: built-in module (Python 3.7+)')
else:
    print('⚠️  Python 3.7+ required for dataclasses')
    print('💡 Consider upgrading Python or installing dataclasses package')
"

# Check if backend directory exists
if [ ! -d "backend" ]; then
    echo "📁 Creating backend directory..."
    mkdir backend
fi

# Check if all required files exist
echo ""
echo "🔍 Checking required files..."

MISSING_FILES=0

if [ ! -f "backend/network_monitor.py" ]; then
    echo "❌ backend/network_monitor.py not found!"
    MISSING_FILES=1
fi

if [ ! -f "backend/continuous_monitor_service.py" ]; then
    echo "❌ backend/continuous_monitor_service.py not found!"
    MISSING_FILES=1
fi

if [ ! -f "backend/database_manager.py" ]; then
    echo "❌ backend/database_manager.py not found!"
    MISSING_FILES=1
fi

if [ ! -f "test_database_integration.py" ]; then
    echo "❌ test_database_integration.py not found!"
    MISSING_FILES=1
fi

if [ $MISSING_FILES -eq 1 ]; then
    echo ""
    echo "🔍 Current project structure:"
    echo "📁 Backend directory contents:"
    ls -la backend/ 2>/dev/null || echo "   (backend directory is empty or doesn't exist)"
    echo "📁 Root directory contents:"
    ls -la *.py 2>/dev/null || echo "   (no Python files in root)"
    echo ""
    echo "❌ Cannot proceed without all required files"
    echo "💡 Please ensure all necessary files are created first"
    exit 1
fi

echo "✅ All required files found"

# Test basic imports using current working directory
echo ""
echo "🧪 Testing database integration imports..."
python -c "
import sys
import os

# Add backend directory to Python path using current working directory
current_dir = os.getcwd()
backend_path = os.path.join(current_dir, 'backend')
sys.path.insert(0, backend_path)

print(f'📁 Current directory: {current_dir}')
print(f'📂 Backend path: {backend_path}')
print(f'🔍 Backend exists: {os.path.exists(backend_path)}')

# Test core networking imports
try:
    from network_monitor import NetworkMonitor
    print('✅ NetworkMonitor imported successfully')
except ImportError as e:
    print(f'❌ Failed to import NetworkMonitor: {e}')
    exit(1)

try:
    from continuous_monitor_service import ContinuousNetworkMonitorService, MonitoringSnapshot
    print('✅ ContinuousNetworkMonitorService imported successfully')
    print('✅ MonitoringSnapshot imported successfully')
except ImportError as e:
    print(f'❌ Failed to import continuous monitor service: {e}')
    exit(1)

# Test database imports
try:
    from database_manager import NetworkDatabaseManager
    print('✅ NetworkDatabaseManager imported successfully')
except ImportError as e:
    print(f'❌ Failed to import NetworkDatabaseManager: {e}')
    exit(1)

# Test database integration test imports
sys.path.insert(0, current_dir)  # Add root directory for test file
try:
    from test_database_integration import DatabaseIntegrationTest
    print('✅ DatabaseIntegrationTest imported successfully')
except ImportError as e:
    print(f'❌ Failed to import DatabaseIntegrationTest: {e}')
    exit(1)

print('✅ All database integration imports successful!')
"

if [ $? -ne 0 ]; then
    echo "❌ Import tests failed"
    echo ""
    echo "🔧 Debugging information:"
    echo "📁 Current directory: $(pwd)"
    echo "📂 Backend directory exists: $([ -d backend ] && echo 'Yes' || echo 'No')"
    echo "📄 Files in backend:"
    ls -la backend/ 2>/dev/null || echo "   (No files or directory doesn't exist)"
    echo "📄 Root Python files:"
    ls -la *.py 2>/dev/null || echo "   (No Python files in root)"
    exit 1
fi

# Test database manager standalone functionality
echo ""
echo "🧪 Testing database manager standalone functionality..."
python -c "
import sys
import os

# Setup paths
current_dir = os.getcwd()
backend_path = os.path.join(current_dir, 'backend')
sys.path.insert(0, backend_path)

# Test basic database operations
try:
    from database_manager import NetworkDatabaseManager
    
    # Test database creation
    db = NetworkDatabaseManager('test_setup_verification.db')
    print('✅ Database manager initialization successful')
    
    # Test session creation
    session_id = db.start_monitoring_session('Setup verification test')
    print(f'✅ Session creation successful (ID: {session_id})')
    
    # Test device storage
    test_device = {
        'ip': '192.168.1.99',
        'mac_address': 'TEST:MAC:ADDRESS',
        'hostname': 'test-setup-device'
    }
    device_id = db.save_device(test_device)
    print(f'✅ Device storage successful (ID: {device_id})')
    
    # Clean up test
    db.end_monitoring_session(session_id)
    print('✅ Session cleanup successful')
    
    # Remove test database
    import os
    if os.path.exists('test_setup_verification.db'):
        os.remove('test_setup_verification.db')
        print('✅ Test database cleaned up')
    
    print('✅ Database manager standalone test passed!')
    
except Exception as e:
    print(f'❌ Database manager test failed: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Database manager standalone test failed"
    echo "💡 Check for SQLite permissions or disk space issues"
    exit 1
fi

echo ""
echo "🎉 Setup complete! Running database integration tests..."
echo "======================================================"
echo "💡 This will test the complete integration between:"
echo "   • Network monitoring service"
echo "   • SQLite database persistence"
echo "   • Data retrieval and analysis"
echo ""
echo "⏱️  Tests will run for about 2-3 minutes"
echo "📊 You'll see live monitoring data being saved to database"
echo "🛑 You can interrupt with Ctrl+C if needed"
echo ""

# Run the database integration tests
python test_database_integration.py

TEST_EXIT_CODE=$?

echo ""
echo "📊 Database Integration Test Results:"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All tests passed! Database integration is working perfectly."
    echo ""
    echo "🎯 What was accomplished:"
    echo "   ✅ SQLite database schema created"
    echo "   ✅ Real-time monitoring data stored"
    echo "   ✅ Device information persisted"
    echo "   ✅ Network snapshots saved"
    echo "   ✅ Quality test results recorded"
    echo "   ✅ Data retrieval and analysis working"
    echo ""
    echo "🚀 Your system now has:"
    echo "   📊 Complete data persistence"
    echo "   🔍 Historical network analysis capability"
    echo "   📈 Analytics-ready dataset"
    echo "   🤖 Perfect foundation for AI integration"
    echo ""
    echo "🔮 Ready for next steps:"
    echo "   • AI prediction models (scikit-learn)"
    echo "   • Web dashboard (React)"
    echo "   • Advanced analytics"
    echo "   • Real-time alerts"
else
    echo "❌ Some tests failed. Please review the output above."
    echo ""
    echo "🔧 Troubleshooting tips:"
    echo "   • Check SQLite permissions"
    echo "   • Ensure sufficient disk space"
    echo "   • Verify network connectivity"
    echo "   • Check Python version (3.7+ recommended)"
    echo "   • Try running tests again"
fi

echo ""
echo "📊 Database Files Created:"
if [ -f "test_network_integration.db" ]; then
    echo "   📁 test_network_integration.db ($(du -h test_network_integration.db | cut -f1))"
    echo "💡 You can inspect this database with:"
    echo "     sqlite3 test_network_integration.db"
    echo "     .tables"
    echo "     .schema"
fi

echo ""
echo "💡 Manual testing commands:"
echo "   1. Activate environment: source network_monitor_env/bin/activate"
echo "   2. Test database manager: python backend/database_manager.py"
echo "   3. Run integration test: python test_database_integration.py"
echo "   4. Start monitoring with DB: python backend/continuous_monitor_service.py"
echo "   5. Deactivate when done: deactivate"

echo ""

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "🎯 Phase 2 COMPLETE: Data Persistence ✅"
    echo "🔮 Next Phase: AI Integration"
    echo "   Ready to implement predictive analytics and optimization!"
else
    echo "🔄 Phase 2: Data Persistence - Needs attention"
    echo "   Review errors and re-run setup"
fi

exit $TEST_EXIT_CODE 