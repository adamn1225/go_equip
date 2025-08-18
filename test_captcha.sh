#!/bin/bash
# Test CAPTCHA Integration

echo "🧪 Testing CAPTCHA Integration..."

# 1. Test Python bridge health
echo "1️⃣ Testing Python CAPTCHA bridge..."
curl -s http://localhost:5000/health | jq . || echo "❌ Python bridge not running"

# 2. Test Go CAPTCHA client
echo "2️⃣ Testing Go CAPTCHA client..."
cd cmd/scraper
go run -c 'package main; import "scraper"; client := scraper.NewCAPTCHASolverClient(""); println(client.IsHealthy())' || echo "❌ Go client test failed"

# 3. Test full integration with a known CAPTCHA page
echo "3️⃣ Testing with sample CAPTCHA page..."
python ai/captcha_bridge.py test https://www.google.com/recaptcha/api2/demo

echo "✅ CAPTCHA integration test complete!"
