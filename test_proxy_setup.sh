#!/bin/bash

# Test proxy setup and rotation
echo "🔍 Testing proxy rotation setup..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please copy .env.example to .env and configure your proxy settings."
    echo "📋 Required variables:"
    echo "   WEBSHARE_API_KEY=your_api_key"
    echo "   WEBSHARE_PROXY_URL=https://proxy.webshare.io/api/v2/proxy/list/"
    exit 1
fi

# Check if proxy variables are set
source .env
if [ -z "$WEBSHARE_API_KEY" ] || [ -z "$WEBSHARE_PROXY_URL" ]; then
    echo "❌ Proxy configuration incomplete in .env file"
    echo "📋 Please set:"
    echo "   WEBSHARE_API_KEY=your_webshare_api_key"
    echo "   WEBSHARE_PROXY_URL=https://proxy.webshare.io/api/v2/proxy/list/"
    exit 1
fi

echo "✅ Proxy configuration found"
echo "🔗 API Key: ${WEBSHARE_API_KEY:0:10}..." 
echo "🔗 Proxy URL: $WEBSHARE_PROXY_URL"

# Test proxy connectivity (you can add actual HTTP test here)
echo "🚀 Ready to run scraper with proxy rotation!"
echo "💡 Run: go run cmd/scraper/main.go"

# Optional: Test actual proxy connection
echo ""
echo "🧪 Testing proxy API connection..."
curl -s -H "Authorization: Token $WEBSHARE_API_KEY" "$WEBSHARE_PROXY_URL" | head -c 200
echo ""
echo "✅ Proxy API test complete"
