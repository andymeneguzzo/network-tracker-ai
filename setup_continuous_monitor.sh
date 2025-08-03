#!/bin/bash

echo "🚀 Continuous Network Monitor Service Setup"
echo "============================================"

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

# Install dependencies for continuous monitoring
echo ""
echo "📦 Installing required packages..."
pip install psutil ping3

# Verify installations
echo ""
echo "🔍 Verifying installations..."
python -c "import psutil; print('✅ psutil:', psutil.__version__)"
python -c "import ping3; print('✅ ping3: installed')"
python -c "import ipaddress; print('✅ ipaddress: built-in module')"
python -c "import threading; print('✅ threading: built-in module')"
python -c "import signal; print('✅ signal: built-in module')"

# Check if backend directory exists
if [ ! -d "backend" ]; then
    echo "📁 Creating backend directory..."
    mkdir backend
fi

# Check if continuous monitor service exists
if [ ! -f "backend/continuous_monitor_service.py" ]; then
    echo "⚠️  Continuous monitor service not found!"
    echo "💡 Please ensure backend/continuous_monitor_service.py exists"
    echo "💡 Also ensure backend/network_monitor.py exists"
    echo ""
    echo "🔍 Current backend directory contents:"
    ls -la backend/ 2>/dev/null || echo "   (backend directory is empty or doesn't exist)"
    echo ""
    echo "❌ Cannot proceed without the continuous monitor service file"
    exit 1
fi

# Check if network monitor exists
if [ ! -f "backend/network_monitor.py" ]; then
    echo "⚠️  Network monitor base class not found!"
    echo "💡 Please ensure backend/network_monitor.py exists"
    echo "❌ Cannot proceed without the base network monitor"
    exit 1
fi

# Test basic imports
echo ""
echo "🧪 Testing basic imports..."
python -c "
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from network_monitor import NetworkMonitor
    print('✅ NetworkMonitor imported successfully')
except ImportError as e:
    print(f'❌ Failed to import NetworkMonitor: {e}')
    exit(1)

try:
    from continuous_monitor_service import ContinuousNetworkMonitorService
    print('✅ ContinuousNetworkMonitorService imported successfully')
except ImportError as e:
    print(f'❌ Failed to import ContinuousNetworkMonitorService: {e}')
    exit(1)

print('✅ All imports successful!')
"

if [ $? -ne 0 ]; then
    echo "❌ Import tests failed"
    exit 1
fi

# Check if test file exists
if [ ! -f "test_continuous_monitor.py" ]; then
    echo "⚠️  Test file not found!"
    echo "💡 Please ensure test_continuous_monitor.py exists"
    echo "❌ Cannot run tests without the test file"
    exit 1
fi

echo ""
echo "🎉 Setup complete! Running continuous monitor tests..."
echo "======================================================"
echo "💡 This will test the background monitoring service"
echo "⏱️  Tests will run for about 1-2 minutes"
echo "🛑 You can interrupt with Ctrl+C if needed"
echo ""

# Run the continuous monitor tests
python test_continuous_monitor.py

TEST_EXIT_CODE=$?

echo ""
echo "📊 Test Results Summary:"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All tests passed! Continuous monitoring service is working perfectly."
    echo ""
    echo "🚀 Ready for next steps:"
    echo "   • Add SQLite database persistence"
    echo "   • Implement data analytics"
    echo "   • Build AI prediction models"
else
    echo "❌ Some tests failed. Please review the output above."
    echo ""
    echo "🔧 Troubleshooting tips:"
    echo "   • Check network connectivity"
    echo "   • Ensure you have admin permissions for network monitoring"
    echo "   • Try running tests again"
fi

echo ""
echo "💡 To run continuous monitoring manually:"
echo "   1. Activate environment: source network_monitor_env/bin/activate"
echo "   2. Start service: python backend/continuous_monitor_service.py"
echo "   3. Run tests: python test_continuous_monitor.py"
echo "   4. Deactivate when done: deactivate"

echo ""
echo "🎯 Next Phase: Database Integration"
echo "   Ready to implement SQLite persistence for collected data!"

exit $TEST_EXIT_CODE 