#!/bin/bash

# Anti-Ban Scraper Recovery Script
# This script helps recover from IP bans by cycling through different techniques

echo "🛡️  Anti-Ban Recovery System"
echo "=========================="

# Function to check current IP
check_ip() {
    echo "🔍 Checking current IP address..."
    curl -s https://ipinfo.io/ip 2>/dev/null || curl -s https://api.ipify.org
}

# Function to test site accessibility
test_site() {
    echo "🌐 Testing MachineryTrader accessibility..."
    response=$(curl -s -I "https://www.machinerytrader.com" | head -n 1)
    if [[ $response == *"200"* ]]; then
        echo "✅ Site accessible"
        return 0
    elif [[ $response == *"403"* ]] || [[ $response == *"404"* ]]; then
        echo "❌ Site blocked/banned"
        return 1
    else
        echo "⚠️  Unknown response: $response"
        return 2
    fi
}

# Main recovery sequence
main() {
    echo "Current IP:"
    check_ip
    echo ""
    
    test_site
    site_status=$?
    
    if [ $site_status -eq 0 ]; then
        echo "✅ No ban detected - safe to scrape"
        echo "💡 Recommendations:"
        echo "   - Use longer delays (5-10 seconds between pages)"
        echo "   - Rotate proxies more frequently"
        echo "   - Enable headless mode: false for manual CAPTCHA solving"
    else
        echo "🚫 Ban/block detected"
        echo "💡 Recovery options:"
        echo "   1. Wait 30-60 minutes before retrying"
        echo "   2. Use different proxy pool"
        echo "   3. Implement longer delays"
        echo "   4. Check proxy health in Webshare dashboard"
    fi
    
    echo ""
    echo "🔄 Proxy rotation recommendations:"
    echo "   - Rotate proxy every 1-5 pages"
    echo "   - Use residential proxies if available"
    echo "   - Monitor success rates closely"
}

main
