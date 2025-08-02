#!/bin/bash

echo "🚀 Network Monitor Complete Setup"
echo "================================="

# Check current environment
echo "📍 Current environment: $CONDA_DEFAULT_ENV"
echo "🐍 Current Python: $(which python)"

# Create virtual environment
echo ""
echo "🔧 Creating virtual environment..."
python3 -m venv network_monitor_env

if [ $? -ne 0 ]; then
    echo "❌ Failed to create virtual environment"
    echo "💡 Try: python -m venv network_monitor_env"
    exit 1
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

# Install dependencies
echo ""
echo "📦 Installing required packages..."
pip install psutil ping3

# Verify installations
echo ""
echo "🔍 Verifying installations..."
python -c "import psutil; print('✅ psutil:', psutil.__version__)"
python -c "import ping3; print('✅ ping3: installed')"
python -c "import ipaddress; print('✅ ipaddress: built-in module')"

echo ""
echo "🎉 Setup complete! Running network monitor test..."
echo "=================================================="
python test_network_monitor.py

echo ""
echo "💡 To run again in the future:"
echo "   1. Activate environment: source network_monitor_env/bin/activate"
echo "   2. Run test: python test_network_monitor.py"
echo "   3. Deactivate when done: deactivate" 