#!/bin/bash
"""
Quick Start CAPTCHA Solver
Uses lightweight version with minimal dependencies
"""

echo "🤖 Starting Lightweight CAPTCHA Solver..."
echo ""

# Check if 2captcha API key is set
if [ -z "$CAPTCHA_API_KEY_2CAPTCHA" ]; then
    echo "⚠️  2captcha API key not set!"
    echo ""
    echo "📋 To configure:"
    echo "1. Sign up at: https://2captcha.com"
    echo "2. Add funds to your account ($5 minimum)"
    echo "3. Get your API key from the dashboard"
    echo "4. Set environment variable:"
    echo "   export CAPTCHA_API_KEY_2CAPTCHA='your_api_key_here'"
    echo ""
    echo "🚀 Starting without API key (health check only)..."
    echo ""
else
    echo "✅ 2captcha API key configured!"
    echo ""
fi

# Start the lightweight solver
echo "📡 CAPTCHA Solver will be available at: http://localhost:5000"
echo "💡 Test with: curl http://localhost:5000/health"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python3 ai/lightweight_captcha_solver.py --port 5000
