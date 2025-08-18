#!/bin/bash
"""
CAPTCHA Solver Setup Script
Installs dependencies and configures the AI CAPTCHA solver
"""

echo "🤖 Setting up AI CAPTCHA Solver..."

# Create virtual environment for AI dependencies
echo "📦 Creating Python virtual environment..."
python3 -m venv ai_env

# Activate virtual environment
source ai_env/bin/activate

# Install Python dependencies
echo "📥 Installing Python packages..."
pip install --upgrade pip
pip install -r ai/requirements_ai.txt

# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
playwright install chromium

# Install system dependencies for OCR
echo "🔧 Installing system dependencies..."
if command -v apt-get &> /dev/null; then
    # Ubuntu/Debian
    sudo apt-get update
    sudo apt-get install -y tesseract-ocr tesseract-ocr-eng
elif command -v yum &> /dev/null; then
    # RHEL/CentOS
    sudo yum install -y tesseract tesseract-langpack-eng
elif command -v brew &> /dev/null; then
    # macOS
    brew install tesseract
else
    echo "⚠️  Please install tesseract-ocr manually for your system"
fi

# Create configuration file
echo "⚙️  Creating configuration file..."
cat > ai/captcha_config.py << EOF
"""
CAPTCHA Solver Configuration
Set your API keys here
"""

# 2captcha API key (get from https://2captcha.com)
API_KEY_2CAPTCHA = ""  # Set your API key here

# AntiCaptcha API key (get from https://anti-captcha.com)
API_KEY_ANTICAPTCHA = ""  # Set your API key here

# Local OCR settings
OCR_ENABLED = True
OCR_CONFIDENCE_THRESHOLD = 60

# Service settings
BRIDGE_HOST = "localhost"
BRIDGE_PORT = 5000
SOLVER_TIMEOUT = 300  # 5 minutes

print("📝 Configuration loaded")
if API_KEY_2CAPTCHA:
    print("✅ 2captcha API key configured")
else:
    print("⚠️  2captcha API key not set")

if API_KEY_ANTICAPTCHA:
    print("✅ AntiCaptcha API key configured")
else:
    print("⚠️  AntiCaptcha API key not set")
EOF

# Create startup script
echo "🚀 Creating startup scripts..."
cat > start_captcha_solver.sh << 'EOF'
#!/bin/bash
echo "🤖 Starting CAPTCHA Solver Service..."

# Activate virtual environment
source ai_env/bin/activate

# Start the service
python ai/captcha_bridge.py
EOF

chmod +x start_captcha_solver.sh

# Create test script
cat > test_captcha_solver.sh << 'EOF'
#!/bin/bash
echo "🧪 Testing CAPTCHA Solver..."

if [ -z "$1" ]; then
    echo "Usage: ./test_captcha_solver.sh <url>"
    echo "Example: ./test_captcha_solver.sh https://example.com/captcha"
    exit 1
fi

# Activate virtual environment
source ai_env/bin/activate

# Run test
python ai/captcha_bridge.py test "$1"
EOF

chmod +x test_captcha_solver.sh

echo ""
echo "✅ CAPTCHA Solver setup complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Set your API keys in ai/captcha_config.py"
echo "   - Get 2captcha key from: https://2captcha.com"
echo "   - Get AntiCaptcha key from: https://anti-captcha.com"
echo ""
echo "2. Start the CAPTCHA solver service:"
echo "   ./start_captcha_solver.sh"
echo ""
echo "3. Test the solver:"
echo "   ./test_captcha_solver.sh <url-with-captcha>"
echo ""
echo "4. The Go scraper will automatically use the solver when CAPTCHAs are detected"
echo ""
echo "💡 Tips:"
echo "- The solver works best with 2captcha API key"
echo "- Local OCR works for simple text CAPTCHAs"
echo "- Service runs on http://localhost:5000"
echo ""
