#!/usr/bin/env python3
"""
Quick URL pattern tester for Sandhills publishing sites
Helps identify pagination and category parameters
"""

import requests
from urllib.parse import urljoin, urlparse
import re

# Known Sandhills sites to test
SANDHILLS_SITES = {
    "machinerytrader.com": {
        "base_url": "https://www.machinerytrader.com",
        "test_patterns": [
            "/listings/search?Category=1031&page=1",  # Construction equipment (known working)
            "/listings/search?Category=1032&page=1",  # Different category
            "/listings/search?page=1",                # No category filter
        ]
    },
    "pavingequipment.com": {
        "base_url": "https://www.pavingequipment.com", 
        "test_patterns": [
            "/listings/search?page=1",
            "/listings/search?Category=1031&page=1",
        ]
    },
    "tractorhouse.com": {
        "base_url": "https://www.tractorhouse.com",
        "test_patterns": [
            "/listings/search?page=1",
            "/listings/search?Category=1031&page=1",
            "/listings/search?Category=1001&page=1",  # Farm equipment category
        ]
    },
    "auctiontime.com": {
        "base_url": "https://www.auctiontime.com",
        "test_patterns": [
            "/listings/search?page=1",
            "/search?page=1",
            "/auctions?page=1",
        ]
    },
    "machinefinder.com": {
        "base_url": "https://www.machinefinder.com",
        "test_patterns": [
            "/listings/search?page=1",
            "/listings/search?Category=1031&page=1",
        ]
    },
    "truckpaper.com": {
        "base_url": "https://www.truckpaper.com",
        "test_patterns": [
            "/listings/search?page=1",
            "/listings/search?Category=1031&page=1",
        ]
    }
}

def test_url_pattern(site, base_url, pattern):
    """Test if a URL pattern exists and returns valid content"""
    full_url = base_url + pattern
    print(f"Testing: {full_url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(full_url, headers=headers, timeout=10)
        
        # Check for common indicators of listing pages
        indicators = {
            "has_listings": any(keyword in response.text.lower() for keyword in [
                'listing', 'equipment', 'machinery', 'seller', 'contact', 'phone'
            ]),
            "has_pagination": any(keyword in response.text.lower() for keyword in [
                'page', 'next', 'previous', 'pagination'
            ]),
            "response_size": len(response.text),
            "status_code": response.status_code
        }
        
        return {
            "url": full_url,
            "working": response.status_code == 200,
            "indicators": indicators
        }
        
    except Exception as e:
        return {
            "url": full_url, 
            "working": False,
            "error": str(e)
        }

def analyze_site(site_name, site_config):
    """Analyze a single site for working URL patterns"""
    print(f"\n🔍 Analyzing {site_name}...")
    print("=" * 60)
    
    working_patterns = []
    
    for pattern in site_config["test_patterns"]:
        result = test_url_pattern(site_name, site_config["base_url"], pattern)
        
        if result["working"] and result.get("indicators", {}).get("has_listings", False):
            working_patterns.append({
                "pattern": pattern,
                "full_url": result["url"],
                "size": result["indicators"]["response_size"]
            })
            print(f"✅ WORKING: {pattern} (Size: {result['indicators']['response_size']} chars)")
        elif result["working"]:
            print(f"⚠️  LOADS: {pattern} (Size: {result['indicators']['response_size']} chars) - May not have listings")
        else:
            print(f"❌ FAILED: {pattern} - {result.get('error', 'HTTP error')}")
    
    return working_patterns

def main():
    print("🌐 Sandhills Publishing Network - URL Pattern Tester")
    print("Testing pagination and category patterns across sites...")
    
    all_working_patterns = {}
    
    for site_name, config in SANDHILLS_SITES.items():
        working = analyze_site(site_name, config)
        if working:
            all_working_patterns[site_name] = working
    
    print("\n" + "="*80)
    print("📊 SUMMARY - Working URL Patterns for Go Scraper:")
    print("="*80)
    
    for site, patterns in all_working_patterns.items():
        print(f"\n🎯 {site.upper()}:")
        for pattern_info in patterns:
            base_url = SANDHILLS_SITES[site]["base_url"]
            full_pattern = base_url + pattern_info["pattern"]
            go_pattern = full_pattern.replace('page=1', 'page=')
            print(f"   baseURL := \"{go_pattern}\"")
    
    if all_working_patterns:
        print(f"\n✅ Found working patterns for {len(all_working_patterns)} sites!")
        print("💡 Copy the baseURL patterns above into your Go scraper main.go")
    else:
        print("\n⚠️  No working patterns found. Sites may require different approaches.")

if __name__ == "__main__":
    main()
