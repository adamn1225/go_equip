#!/bin/bash
"""
🚀 AI-Enhanced Scraping System Startup
Launches CAPTCHA solver with OpenAI integration support
"""

echo "🚀 Starting AI-Enhanced Scraping System..."
echo ""

# Check 2captcha API key
if [ -z "$CAPTCHA_API_KEY_2CAPTCHA" ]; then
    echo "⚠️  2captcha API key not set!"
    echo ""
    echo "📋 To configure CAPTCHA solving:"
    echo "1. Sign up at: https://2captcha.com"
    echo "2. Add funds to your account ($5 minimum)"
    echo "3. Get your API key from the dashboard"
    echo "4. Set environment variable:"
    echo "   export CAPTCHA_API_KEY_2CAPTCHA='your_api_key_here'"
    echo ""
else
    echo "✅ 2captcha API key configured!"
    echo ""
fi

# Check OpenAI API key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "💡 OpenAI API key not set - AI insights disabled"
    echo ""
    echo "🧠 To enable AI dashboard features:"
    echo "   export OPENAI_API_KEY='sk-proj-your_key_here'"
    echo ""
else
    echo "✅ OpenAI API key configured - AI insights enabled!"
    echo ""
fi

# Start the CAPTCHA solver service
echo "📡 CAPTCHA Solver will be available at: http://localhost:5000"
echo "🎯 AI Dashboard: streamlit run ai_dashboard.py"
echo "💡 Test with: curl http://localhost:5000/health"
echo ""
echo "🚀 Starting services... Press Ctrl+C to stop"
echo ""

# Launch CAPTCHA solver in background for dashboard integration
python3 ai/lightweight_captcha_solver.py --port 5000 &
CAPTCHA_PID=$!

echo "🤖 CAPTCHA Solver started (PID: $CAPTCHA_PID)"
echo ""
echo "🎨 Quick Commands:"
echo "   Start AI Dashboard: streamlit run ai_dashboard.py"
echo "   Health Check: curl http://localhost:5000/health"
echo "   Stop Service: kill $CAPTCHA_PID"
echo ""

# Keep script running
wait $CAPTCHA_PID
