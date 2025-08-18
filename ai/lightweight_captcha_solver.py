#!/usr/bin/env python3
"""
Lightweight CAPTCHA Solver
Works with just basic dependencies for quick setup
"""

import json
import sys
import logging
import requests
import time
from typing import Optional, Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LightweightCAPTCHASolver:
    """Lightweight CAPTCHA solver using external APIs"""
    
    def __init__(self, api_key_2captcha: str = None):
        self.api_key_2captcha = api_key_2captcha
        
    def solve_captcha(self, site_url: str, site_key: str = None, captcha_type: str = "recaptcha") -> Optional[str]:
        """
        Solve CAPTCHA using 2captcha service
        
        Args:
            site_url: URL of the page with CAPTCHA
            site_key: Site key for reCAPTCHA/hCaptcha
            captcha_type: Type of CAPTCHA (recaptcha, hcaptcha, image)
            
        Returns:
            str: CAPTCHA solution token or None if failed
        """
        if not self.api_key_2captcha:
            logger.error("2captcha API key not configured")
            return None
            
        try:
            if captcha_type == "recaptcha" and site_key:
                return self._solve_recaptcha_v2(site_url, site_key)
            else:
                logger.warning(f"Unsupported CAPTCHA type: {captcha_type}")
                return None
                
        except Exception as e:
            logger.error(f"CAPTCHA solving failed: {e}")
            return None
    
    def _solve_recaptcha_v2(self, page_url: str, site_key: str) -> Optional[str]:
        """Solve reCAPTCHA v2 using 2captcha"""
        try:
            # Submit CAPTCHA to 2captcha
            submit_response = requests.post(
                "http://2captcha.com/in.php",
                data={
                    'key': self.api_key_2captcha,
                    'method': 'userrecaptcha',
                    'googlekey': site_key,
                    'pageurl': page_url
                },
                timeout=30
            )
            
            if not submit_response.text.startswith('OK|'):
                logger.error(f"2captcha submission failed: {submit_response.text}")
                return None
            
            captcha_id = submit_response.text.split('|')[1]
            logger.info(f"CAPTCHA submitted to 2captcha with ID: {captcha_id}")
            
            # Poll for solution
            max_attempts = 24  # 2 minutes with 5-second intervals
            for attempt in range(max_attempts):
                time.sleep(5)
                
                result_response = requests.get(
                    "http://2captcha.com/res.php",
                    params={
                        'key': self.api_key_2captcha,
                        'action': 'get',
                        'id': captcha_id
                    },
                    timeout=10
                )
                
                if result_response.text == 'CAPCHA_NOT_READY':
                    logger.info(f"CAPTCHA solving in progress... (attempt {attempt + 1}/{max_attempts})")
                    continue
                elif result_response.text.startswith('OK|'):
                    solution = result_response.text.split('|')[1]
                    logger.info("reCAPTCHA solved successfully!")
                    return solution
                else:
                    logger.error(f"2captcha error: {result_response.text}")
                    return None
            
            logger.error("2captcha timeout - solution not received in time")
            return None
            
        except requests.RequestException as e:
            logger.error(f"Network error during reCAPTCHA solving: {e}")
            return None
        except Exception as e:
            logger.error(f"reCAPTCHA solving failed: {e}")
            return None

# Simple Flask-like HTTP server using built-in modules
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import json

class CAPTCHARequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for CAPTCHA solving API"""
    
    def do_POST(self):
        if self.path == '/solve-captcha':
            self._handle_solve_captcha()
        else:
            self._send_error(404, "Not Found")
    
    def do_GET(self):
        if self.path == '/health':
            self._handle_health_check()
        else:
            self._send_error(404, "Not Found")
    
    def _handle_solve_captcha(self):
        try:
            # Read request body
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            # Validate request
            if 'url' not in data:
                self._send_json_response({
                    'success': False,
                    'error': 'Missing required field: url'
                }, 400)
                return
            
            # Get CAPTCHA solver instance
            solver = getattr(self.server, 'captcha_solver', None)
            if not solver:
                self._send_json_response({
                    'success': False,
                    'error': 'CAPTCHA solver not initialized'
                }, 500)
                return
            
            # Extract parameters
            url = data['url']
            site_key = data.get('site_key', '')
            captcha_type = data.get('captcha_type', 'recaptcha')
            
            # Solve CAPTCHA
            solution = solver.solve_captcha(url, site_key, captcha_type)
            
            if solution:
                self._send_json_response({
                    'success': True,
                    'solution': solution,
                    'message': 'CAPTCHA solved successfully'
                })
            else:
                self._send_json_response({
                    'success': False,
                    'error': 'Failed to solve CAPTCHA'
                }, 400)
                
        except json.JSONDecodeError:
            self._send_json_response({
                'success': False,
                'error': 'Invalid JSON in request body'
            }, 400)
        except Exception as e:
            self._send_json_response({
                'success': False,
                'error': str(e)
            }, 500)
    
    def _handle_health_check(self):
        solver = getattr(self.server, 'captcha_solver', None)
        self._send_json_response({
            'status': 'healthy',
            'captcha_solver': 'ready' if solver else 'not_initialized',
            'api_keys_configured': {
                '2captcha': solver.api_key_2captcha is not None if solver else False
            }
        })
    
    def _send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def _send_error(self, status, message):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        error_data = {'error': message, 'status': status}
        self.wfile.write(json.dumps(error_data).encode('utf-8'))
    
    def log_message(self, format, *args):
        # Custom logging to avoid spam
        logger.info(f"{self.address_string()} - {format % args}")

def start_captcha_server(api_key_2captcha: str = None, port: int = 5000):
    """Start the lightweight CAPTCHA solver server"""
    
    # Initialize CAPTCHA solver
    captcha_solver = LightweightCAPTCHASolver(api_key_2captcha)
    
    # Create HTTP server
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, CAPTCHARequestHandler)
    
    # Attach CAPTCHA solver to server
    httpd.captcha_solver = captcha_solver
    
    logger.info(f"🚀 CAPTCHA Solver started on http://localhost:{port}")
    logger.info(f"📡 Health check: http://localhost:{port}/health")
    
    if api_key_2captcha:
        logger.info("✅ 2captcha API key configured")
    else:
        logger.warning("⚠️  2captcha API key not set - add via environment variable")
        logger.info("   export CAPTCHA_API_KEY_2CAPTCHA='your_api_key'")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("🛑 CAPTCHA Solver shutting down...")
        httpd.shutdown()

# Command line interface
def main():
    """Main entry point"""
    import os
    import argparse
    
    parser = argparse.ArgumentParser(description='Lightweight CAPTCHA Solver')
    parser.add_argument('--port', type=int, default=5000, help='Server port')
    parser.add_argument('--api-key', type=str, help='2captcha API key')
    parser.add_argument('--test', type=str, help='Test CAPTCHA solving on URL')
    
    args = parser.parse_args()
    
    # Get API key from argument or environment
    api_key = args.api_key or os.getenv('CAPTCHA_API_KEY_2CAPTCHA')
    
    if args.test:
        # Test mode
        if not api_key:
            print("❌ API key required for testing. Set --api-key or CAPTCHA_API_KEY_2CAPTCHA")
            return
            
        solver = LightweightCAPTCHASolver(api_key)
        print(f"🧪 Testing CAPTCHA solver on: {args.test}")
        
        # For testing, we'd need to extract site key from the page
        print("⚠️  Manual testing requires site key. Use the HTTP API for full functionality.")
        
    else:
        # Server mode
        start_captcha_server(api_key, args.port)

if __name__ == '__main__':
    main()
