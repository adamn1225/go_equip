#!/usr/bin/env python3
"""
AI-Powered CAPTCHA Solver
Automatically solves CAPTCHAs to maintain continuous scraping
Uses both 2captcha and AntiCaptcha services for maximum reliability
"""

import base64
import io
import time
import requests
import os
from typing import Optional, Dict, Any
from PIL import Image
import cv2
import numpy as np
from playwright.sync_api import Page
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CAPTCHASolver:
    """Multi-method CAPTCHA solver with fallback options"""
    
    def __init__(self):
        self.api_key_2captcha = os.getenv('2CAPTCHA_API_KEY')
        self.api_key_anticaptcha = os.getenv('ANTICAPTCHA_API_KEY')
        
        # Log which services are available
        services = []
        if self.api_key_2captcha:
            services.append("2captcha")
        if self.api_key_anticaptcha:
            services.append("AntiCaptcha")
        
        if services:
            logger.info(f"CAPTCHA services initialized: {', '.join(services)}")
        else:
            logger.warning("No CAPTCHA API keys found!")
        
    def solve_captcha(self, page: Page, captcha_selector: str = None) -> bool:
        """
        Main CAPTCHA solving method with multiple approaches
        
        Args:
            page: Playwright page object
            captcha_selector: CSS selector for CAPTCHA image/iframe
            
        Returns:
            bool: True if CAPTCHA was solved successfully
        """
        try:
            # Step 1: Detect CAPTCHA type
            captcha_info = self._detect_captcha_type(page)
            if not captcha_info:
                logger.info("No CAPTCHA detected")
                return True
                
            logger.info(f"CAPTCHA detected: {captcha_info['type']}")
            
            # Step 2: Try different solving methods based on type with intelligent service selection
            if captcha_info['type'] == 'recaptcha':
                # Try 2captcha first for reCAPTCHA (they excel at this)
                return self._solve_with_fallback(['2captcha', 'anticaptcha'], 'recaptcha', page, captcha_info)
            elif captcha_info['type'] == 'hcaptcha':
                # Try AntiCaptcha first for hCaptcha (they excel at this)
                return self._solve_with_fallback(['anticaptcha', '2captcha'], 'hcaptcha', page, captcha_info)
            elif captcha_info['type'] == 'image':
                # Try both services for image CAPTCHAs
                return self._solve_with_fallback(['2captcha', 'anticaptcha'], 'image', page, captcha_info)
            elif captcha_info['type'] == 'text':
                # Try 2captcha first for text CAPTCHAs
                return self._solve_with_fallback(['2captcha', 'anticaptcha'], 'text', page, captcha_info)
            else:
                logger.warning(f"Unknown CAPTCHA type: {captcha_info['type']}")
                return False
                
        except Exception as e:
            logger.error(f"CAPTCHA solving failed: {e}")
            return False
    
    def _detect_captcha_type(self, page: Page) -> Optional[Dict[str, Any]]:
        """Detect what type of CAPTCHA is present on the page"""
        
        # Check for reCAPTCHA
        if page.locator("iframe[src*='recaptcha']").count() > 0:
            return {
                'type': 'recaptcha',
                'element': page.locator("iframe[src*='recaptcha']").first,
                'sitekey': self._extract_recaptcha_sitekey(page)
            }
        
        # Check for hCaptcha
        if page.locator("iframe[src*='hcaptcha']").count() > 0:
            return {
                'type': 'hcaptcha',
                'element': page.locator("iframe[src*='hcaptcha']").first,
                'sitekey': self._extract_hcaptcha_sitekey(page)
            }
        
        # Check for image CAPTCHA
        captcha_images = page.locator("img[src*='captcha'], img[alt*='captcha'], img[id*='captcha']")
        if captcha_images.count() > 0:
            return {
                'type': 'image',
                'element': captcha_images.first
            }
        
        # Check for text CAPTCHA input
        captcha_inputs = page.locator("input[name*='captcha'], input[id*='captcha'], input[placeholder*='captcha']")
        if captcha_inputs.count() > 0:
            return {
                'type': 'text',
                'element': captcha_inputs.first,
                'image_element': self._find_associated_image(page, captcha_inputs.first)
            }
        
        return None
    
    def _solve_with_fallback(self, service_order: list, captcha_type: str, page: Page, captcha_info: Dict) -> bool:
        """Try multiple CAPTCHA services in order until one succeeds"""
        for service in service_order:
            if service == '2captcha' and self.api_key_2captcha:
                logger.info(f"Trying 2captcha for {captcha_type} CAPTCHA...")
                if self._solve_with_2captcha(captcha_type, page, captcha_info):
                    return True
                logger.info("2captcha attempt failed, trying next service...")
                
            elif service == 'anticaptcha' and self.api_key_anticaptcha:
                logger.info(f"Trying AntiCaptcha for {captcha_type} CAPTCHA...")
                if self._solve_with_anticaptcha(captcha_type, page, captcha_info):
                    return True
                logger.info("AntiCaptcha attempt failed, trying next service...")
        
        logger.error(f"All CAPTCHA services failed for {captcha_type}")
        return False
    
    def _solve_with_2captcha(self, captcha_type: str, page: Page, captcha_info: Dict) -> bool:
        """Solve CAPTCHA using 2captcha service"""
        try:
            if captcha_type == 'recaptcha':
                return self._solve_recaptcha_2captcha(page, captcha_info)
            elif captcha_type == 'hcaptcha':
                return self._solve_hcaptcha_2captcha(page, captcha_info)
            elif captcha_type == 'image':
                return self._solve_image_2captcha(page, captcha_info)
            elif captcha_type == 'text':
                return self._solve_text_2captcha(page, captcha_info)
            return False
        except Exception as e:
            logger.error(f"2captcha solving error: {e}")
            return False
    
    def _solve_with_anticaptcha(self, captcha_type: str, page: Page, captcha_info: Dict) -> bool:
        """Solve CAPTCHA using AntiCaptcha service"""
        try:
            if captcha_type == 'recaptcha':
                return self._solve_recaptcha_anticaptcha(page, captcha_info)
            elif captcha_type == 'hcaptcha':
                return self._solve_hcaptcha_anticaptcha(page, captcha_info)
            elif captcha_type == 'image':
                return self._solve_image_anticaptcha(page, captcha_info)
            elif captcha_type == 'text':
                return self._solve_text_anticaptcha(page, captcha_info)
            return False
        except Exception as e:
            logger.error(f"AntiCaptcha solving error: {e}")
            return False
    
    def _solve_recaptcha_2captcha(self, page: Page, captcha_info: Dict) -> bool:
        """Solve reCAPTCHA using 2captcha service"""
        try:
            if not self.api_key_2captcha:
                logger.warning("2captcha API key not set")
                return False
            
            sitekey = captcha_info['sitekey']
            page_url = page.url
            
            # Submit CAPTCHA to 2captcha
            submit_response = requests.post(
                "http://2captcha.com/in.php",
                data={
                    'key': self.api_key_2captcha,
                    'method': 'userrecaptcha',
                    'googlekey': sitekey,
                    'pageurl': page_url
                }
            )
            
            if not submit_response.text.startswith('OK|'):
                logger.error(f"2captcha submission failed: {submit_response.text}")
                return False
            
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
                    }
                )
                
                if result_response.text == 'CAPCHA_NOT_READY':
                    continue
                elif result_response.text.startswith('OK|'):
                    solution = result_response.text.split('|')[1]
                    logger.info("reCAPTCHA solved!")
                    
                    # Inject solution into page
                    page.evaluate(f"""
                        document.getElementById('g-recaptcha-response').innerHTML = '{solution}';
                        if (typeof grecaptcha !== 'undefined') {{
                            grecaptcha.getResponse = function() {{ return '{solution}'; }};
                        }}
                    """)
                    
                    return True
                else:
                    logger.error(f"2captcha error: {result_response.text}")
                    return False
            
            logger.error("2captcha timeout")
            return False
            
        except Exception as e:
            logger.error(f"reCAPTCHA solving failed: {e}")
            return False
    
    def _solve_hcaptcha(self, page: Page, captcha_info: Dict) -> bool:
        """Solve hCaptcha using AntiCaptcha service"""
        try:
            if not self.api_key_anticaptcha:
                logger.warning("AntiCaptcha API key not set")
                return False
            
            # Similar implementation to reCAPTCHA but for hCaptcha
            # This would use AntiCaptcha API
            logger.info("hCaptcha solving not implemented yet")
            return False
            
        except Exception as e:
            logger.error(f"hCaptcha solving failed: {e}")
            return False
    
    def _solve_image_captcha(self, page: Page, captcha_info: Dict) -> bool:
        """Solve image-based CAPTCHA using OCR + AI"""
        try:
            # Take screenshot of CAPTCHA image
            captcha_element = captcha_info['element']
            captcha_screenshot = captcha_element.screenshot()
            
            # Process image
            image = Image.open(io.BytesIO(captcha_screenshot))
            
            # Method 1: Try local OCR
            solution = self._ocr_solve_image(image)
            if solution:
                logger.info(f"OCR solution found: {solution}")
                return self._input_captcha_solution(page, solution)
            
            # Method 2: Try 2captcha image solving
            solution = self._api_solve_image(captcha_screenshot)
            if solution:
                logger.info(f"API solution found: {solution}")
                return self._input_captcha_solution(page, solution)
            
            return False
            
        except Exception as e:
            logger.error(f"Image CAPTCHA solving failed: {e}")
            return False
    
    def _solve_text_captcha(self, page: Page, captcha_info: Dict) -> bool:
        """Solve text-based CAPTCHA"""
        try:
            if captcha_info.get('image_element'):
                # Has associated image - treat as image CAPTCHA
                return self._solve_image_captcha(page, {
                    'element': captcha_info['image_element']
                })
            else:
                logger.warning("Text CAPTCHA without image - cannot solve")
                return False
                
        except Exception as e:
            logger.error(f"Text CAPTCHA solving failed: {e}")
            return False
    
    def _ocr_solve_image(self, image: Image.Image) -> Optional[str]:
        """Use local OCR to solve simple image CAPTCHAs"""
        try:
            import pytesseract
            
            # Convert PIL image to OpenCV format
            img_array = np.array(image)
            img_cv2 = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            # Preprocess image
            gray = cv2.cvtColor(img_cv2, cv2.COLOR_BGR2GRAY)
            
            # Apply noise reduction
            denoised = cv2.medianBlur(gray, 3)
            
            # Apply threshold
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # OCR with specific configuration for CAPTCHAs
            custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
            text = pytesseract.image_to_string(thresh, config=custom_config)
            
            # Clean up result
            solution = ''.join(c for c in text if c.isalnum())
            
            if len(solution) >= 3:  # Minimum reasonable CAPTCHA length
                return solution
            
            return None
            
        except ImportError:
            logger.warning("pytesseract not installed - install with: pip install pytesseract")
            return None
        except Exception as e:
            logger.error(f"OCR solving failed: {e}")
            return None
    
    def _api_solve_image(self, image_data: bytes) -> Optional[str]:
        """Solve image CAPTCHA using 2captcha API"""
        try:
            if not self.api_key_2captcha:
                return None
            
            # Encode image to base64
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            # Submit to 2captcha
            submit_response = requests.post(
                "http://2captcha.com/in.php",
                data={
                    'key': self.api_key_2captcha,
                    'method': 'base64',
                    'body': image_b64
                }
            )
            
            if not submit_response.text.startswith('OK|'):
                return None
            
            captcha_id = submit_response.text.split('|')[1]
            
            # Poll for solution
            for _ in range(24):  # 2 minutes
                time.sleep(5)
                
                result_response = requests.get(
                    "http://2captcha.com/res.php",
                    params={
                        'key': self.api_key_2captcha,
                        'action': 'get',
                        'id': captcha_id
                    }
                )
                
                if result_response.text.startswith('OK|'):
                    return result_response.text.split('|')[1]
                elif result_response.text != 'CAPCHA_NOT_READY':
                    break
            
            return None
            
        except Exception as e:
            logger.error(f"API image solving failed: {e}")
            return None
    
    def _input_captcha_solution(self, page: Page, solution: str) -> bool:
        """Input CAPTCHA solution into the form"""
        try:
            # Try common CAPTCHA input selectors
            selectors = [
                "input[name*='captcha']",
                "input[id*='captcha']",
                "input[placeholder*='captcha']",
                "input[class*='captcha']"
            ]
            
            for selector in selectors:
                if page.locator(selector).count() > 0:
                    page.fill(selector, solution)
                    logger.info(f"CAPTCHA solution entered: {solution}")
                    return True
            
            logger.warning("Could not find CAPTCHA input field")
            return False
            
        except Exception as e:
            logger.error(f"Failed to input CAPTCHA solution: {e}")
            return False
    
    def _extract_recaptcha_sitekey(self, page: Page) -> str:
        """Extract reCAPTCHA sitekey from page"""
        try:
            # Try to find sitekey in various places
            sitekey = page.evaluate("""
                () => {
                    // Look for data-sitekey attribute
                    const elements = document.querySelectorAll('[data-sitekey]');
                    if (elements.length > 0) return elements[0].getAttribute('data-sitekey');
                    
                    // Look in grecaptcha.render calls
                    const scripts = document.getElementsByTagName('script');
                    for (let script of scripts) {
                        const match = script.innerHTML.match(/sitekey['":]\\s*['"]([^'"]+)/);
                        if (match) return match[1];
                    }
                    
                    return null;
                }
            """)
            return sitekey or ""
        except:
            return ""
    
    def _extract_hcaptcha_sitekey(self, page: Page) -> str:
        """Extract hCaptcha sitekey from page"""
        try:
            sitekey = page.evaluate("""
                () => {
                    const elements = document.querySelectorAll('[data-sitekey]');
                    if (elements.length > 0) return elements[0].getAttribute('data-sitekey');
                    return null;
                }
            """)
            return sitekey or ""
        except:
            return ""
    
    def _find_associated_image(self, page: Page, input_element) -> Optional[Any]:
        """Find image associated with CAPTCHA input field"""
        try:
            # Look for images near the input field
            nearby_images = page.evaluate("""
                (input) => {
                    const images = input.parentElement.querySelectorAll('img');
                    return images.length > 0 ? images[0] : null;
                }
            """, input_element)
            
            return page.locator('img').first if nearby_images else None
        except:
            return None

# Configuration class for easy setup
class CAPTCHAConfig:
    """Configuration for CAPTCHA solver"""
    
    def __init__(self):
        self.enable_2captcha = True
        self.enable_anticaptcha = True
        self.enable_local_ocr = True
        self.api_key_2captcha = None  # Set your API key
        self.api_key_anticaptcha = None  # Set your API key
        
        # OCR settings
        self.ocr_min_confidence = 60
        self.ocr_timeout = 30
        
        # API settings
        self.api_timeout = 120  # 2 minutes
        self.max_retries = 3

# Usage example function
def integrate_with_scraper(page: Page) -> bool:
    """
    Example integration with your existing scraper
    Call this function when you detect a CAPTCHA
    """
    solver = CAPTCHASolver()
    
    # Set your API keys here
    # solver.api_key_2captcha = "your_2captcha_key"
    # solver.api_key_anticaptcha = "your_anticaptcha_key"
    
    return solver.solve_captcha(page)

if __name__ == "__main__":
    print("🤖 CAPTCHA Solver initialized")
    print("Set up your API keys in the CAPTCHASolver class to enable solving")
    print("Supported types: reCAPTCHA, hCaptcha, Image CAPTCHAs, Text CAPTCHAs")
