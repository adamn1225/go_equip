#!/usr/bin/env python3
"""
🚀 AI System Integration Demo
Shows how both OpenAI and 2captcha API keys work together
"""

import os
import requests
import json

def test_openai_integration():
    """Test OpenAI API integration"""
    print("🧠 Testing OpenAI Integration...")
    
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("❌ OPENAI_API_KEY not set")
        return False
    
    if openai_key.startswith('sk-proj-'):
        print("✅ OpenAI API key detected (Project-based)")
        print(f"🔑 Key preview: {openai_key[:15]}...{openai_key[-8:]}")
        
        # Test with a simple API call
        try:
            import openai
            openai.api_key = openai_key
            
            # Simple test prompt
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": "Say 'AI integration successful!' in exactly those words."}
                ],
                max_tokens=10
            )
            
            result = response.choices[0].message.content.strip()
            if "successful" in result.lower():
                print("🎉 OpenAI API working perfectly!")
                return True
            else:
                print(f"⚠️  Unexpected response: {result}")
                return False
                
        except Exception as e:
            print(f"❌ OpenAI API error: {str(e)}")
            return False
    else:
        print("⚠️  Key format doesn't match OpenAI pattern")
        return False

def test_captcha_solver():
    """Test CAPTCHA solver integration"""
    print("\n🤖 Testing CAPTCHA Solver Integration...")
    
    try:
        response = requests.get("http://localhost:5000/health", timeout=3)
        if response.status_code == 200:
            data = response.json()
            print("✅ CAPTCHA Solver: Online")
            print(f"📊 Status: {data.get('status', 'unknown')}")
            
            # Check 2captcha API key
            captcha_key = os.getenv('CAPTCHA_API_KEY_2CAPTCHA')
            if captcha_key:
                print(f"🔑 2captcha API key: {captcha_key[:8]}...{captcha_key[-4:]}")
                if data.get('api_keys_configured', {}).get('2captcha', False):
                    print("🎯 2captcha API: Ready for solving!")
                else:
                    print("⚠️  2captcha API key detected but not validated")
            else:
                print("❌ CAPTCHA_API_KEY_2CAPTCHA not set")
            
            return True
        else:
            print(f"❌ CAPTCHA Solver returned status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ CAPTCHA Solver offline - run ./start_captcha_solver_lite.sh")
        return False
    except Exception as e:
        print(f"❌ Error connecting to CAPTCHA solver: {e}")
        return False

def test_2captcha_format():
    """Check if 2captcha API key format is correct"""
    print("\n🔍 Checking 2captcha API Key Format...")
    
    captcha_key = os.getenv('CAPTCHA_API_KEY_2CAPTCHA')
    if not captcha_key:
        print("❌ No 2captcha API key set")
        print("\n📝 To get a 2captcha API key:")
        print("1. Visit: https://2captcha.com/enterpage")
        print("2. Create account and add funds ($5 minimum)")
        print("3. Go to your dashboard and copy your API key")
        print("4. Run: export CAPTCHA_API_KEY_2CAPTCHA='your_32_char_key'")
        return False
    
    # 2captcha keys are typically 32 characters of letters/numbers
    if len(captcha_key) == 32 and captcha_key.isalnum():
        print("✅ 2captcha API key format looks correct")
        print(f"🔑 Key preview: {captcha_key[:8]}...{captcha_key[-4:]}")
        return True
    else:
        print("⚠️  API key format doesn't match 2captcha pattern")
        print(f"   Expected: 32 alphanumeric characters")
        print(f"   Got: {len(captcha_key)} characters")
        print("\n💡 Note: The key you provided looks like an OpenAI key!")
        return False

def show_integration_status():
    """Show complete system integration status"""
    print("\n" + "="*60)
    print("🎯 AI-ENHANCED SCRAPING SYSTEM STATUS")
    print("="*60)
    
    # Test all components
    openai_ok = test_openai_integration()
    captcha_solver_ok = test_captcha_solver()
    captcha_key_ok = test_2captcha_format()
    
    print("\n" + "="*60)
    print("📊 INTEGRATION SUMMARY")
    print("="*60)
    
    components = [
        ("🧠 OpenAI API (AI Insights)", openai_ok),
        ("🤖 CAPTCHA Solver Service", captcha_solver_ok), 
        ("🔓 2captcha API Key", captcha_key_ok)
    ]
    
    for component, status in components:
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {component}")
    
    # Overall status
    all_ok = openai_ok and captcha_solver_ok and captcha_key_ok
    
    print(f"\n🎯 Overall Status: {'🟢 FULLY OPERATIONAL' if all_ok else '🟡 PARTIAL FUNCTIONALITY'}")
    
    if all_ok:
        print("\n🚀 NEXT STEPS:")
        print("1. Run: streamlit run ai_dashboard.py")
        print("2. Access AI-enhanced dashboard with full CAPTCHA solving")
        print("3. Your scraper will automatically bypass CAPTCHAs!")
    else:
        print("\n🔧 TO FIX:")
        if not captcha_key_ok:
            print("• Get your 2captcha API key from: https://2captcha.com")
        if not captcha_solver_ok:
            print("• Run: ./start_captcha_solver_lite.sh")
        if not openai_ok:
            print("• Your OpenAI key is already set - check connection")

if __name__ == "__main__":
    show_integration_status()
