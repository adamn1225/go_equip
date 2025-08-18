#!/usr/bin/env python3
"""
CAPTCHA Solver Bridge for Go Scraper
Provides HTTP API endpoint for Go scraper to solve CAPTCHAs
"""

import json
import sys
import logging
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
from captcha_solver import CAPTCHASolver, integrate_with_scraper

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global CAPTCHA solver instance
captcha_solver = CAPTCHASolver()

# Set your API keys here - IMPORTANT!
# captcha_solver.api_key_2captcha = "YOUR_2CAPTCHA_KEY"  # Get from https://2captcha.com
# captcha_solver.api_key_anticaptcha = "YOUR_ANTICAPTCHA_KEY"  # Get from https://anti-captcha.com

@app.route('/solve-captcha', methods=['POST'])
def solve_captcha_endpoint():
    """
    HTTP endpoint for Go scraper to request CAPTCHA solving
    
    Expected JSON payload:
    {
        "url": "https://example.com/page-with-captcha",
        "screenshot_path": "/path/to/page/screenshot.png",
        "user_agent": "Mozilla/5.0...",
        "viewport": {"width": 1920, "height": 1080}
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: url'
            }), 400
        
        url = data['url']
        screenshot_path = data.get('screenshot_path')
        user_agent = data.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        viewport = data.get('viewport', {'width': 1920, 'height': 1080})
        
        logger.info(f"Attempting to solve CAPTCHA for: {url}")
        
        # Use Playwright to solve CAPTCHA
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
            )
            
            context = browser.new_context(
                user_agent=user_agent,
                viewport=viewport
            )
            
            page = context.new_page()
            
            # Add stealth scripts
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                window.chrome = {
                    runtime: {},
                };
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
            """)
            
            # Navigate to page
            page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Wait a moment for any dynamic content
            page.wait_for_timeout(2000)
            
            # Try to solve CAPTCHA
            success = captcha_solver.solve_captcha(page)
            
            if success:
                # Wait for any form submission or page changes
                page.wait_for_timeout(3000)
                
                # Get current page info
                final_url = page.url
                page_title = page.title()
                
                # Take final screenshot if path provided
                if screenshot_path:
                    page.screenshot(path=screenshot_path.replace('.png', '_solved.png'))
                
                browser.close()
                
                return jsonify({
                    'success': True,
                    'message': 'CAPTCHA solved successfully',
                    'final_url': final_url,
                    'page_title': page_title
                })
            else:
                browser.close()
                
                return jsonify({
                    'success': False,
                    'error': 'Failed to solve CAPTCHA'
                }), 400
                
    except Exception as e:
        logger.error(f"CAPTCHA solving error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'captcha_solver': 'ready',
        'api_keys_configured': {
            '2captcha': captcha_solver.api_key_2captcha is not None,
            'anticaptcha': captcha_solver.api_key_anticaptcha is not None
        }
    })

@app.route('/config', methods=['POST'])
def update_config():
    """Update CAPTCHA solver configuration"""
    try:
        data = request.get_json()
        
        if 'api_key_2captcha' in data:
            captcha_solver.api_key_2captcha = data['api_key_2captcha']
            logger.info("2captcha API key updated")
        
        if 'api_key_anticaptcha' in data:
            captcha_solver.api_key_anticaptcha = data['api_key_anticaptcha']
            logger.info("AntiCaptcha API key updated")
        
        return jsonify({'success': True, 'message': 'Configuration updated'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Command line interface for testing
def test_captcha_solver():
    """Test CAPTCHA solver from command line"""
    if len(sys.argv) < 2:
        print("Usage: python captcha_bridge.py <url>")
        print("Example: python captcha_bridge.py https://example.com/captcha-page")
        return
    
    url = sys.argv[1]
    print(f"🤖 Testing CAPTCHA solver on: {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Visible for testing
        context = browser.new_context()
        page = context.new_page()
        
        page.goto(url)
        input("Press Enter when page is loaded...")
        
        success = captcha_solver.solve_captcha(page)
        
        if success:
            print("✅ CAPTCHA solved successfully!")
            input("Press Enter to continue...")
        else:
            print("❌ Failed to solve CAPTCHA")
        
        browser.close()

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_captcha_solver()
    else:
        print("🚀 Starting CAPTCHA Solver Bridge...")
        print("📡 API will be available at: http://localhost:5000")
        print("🔧 Configure API keys in the script before use")
        print("💡 Test endpoint: GET /health")
        
        # Start Flask server
        app.run(host='0.0.0.0', port=5000, debug=False)
