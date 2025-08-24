#!/usr/bin/env python3
"""
🔄 New Scraping Workflow with D1 Integration
This replaces the old JSON-based integration process

Step-by-Step Guide:
1. Run scraper (generates seller_contacts_*.json)
2. Run this script (uploads to D1) 
3. Dashboard automatically shows new data
"""

import os
import subprocess
import glob
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def run_command(command, description):
    """Run a command and show the result"""
    print(f"\\n🔄 {description}")
    print(f"Command: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Success!")
            if result.stdout:
                print(result.stdout)
        else:
            print(f"❌ Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to run command: {e}")
        return False
    
    return True

def main():
    print("🚀 New Scraping → D1 Integration Workflow")
    print("=" * 50)
    
    # Step 1: Check for new scraped files
    json_dir = os.path.join("mt_contacts", "json")
    patterns = [os.path.join(json_dir, "seller_contacts_*.json"), 
               os.path.join(json_dir, "seller_contacts_learning_*.json")]
    all_files = []
    for pattern in patterns:
        all_files.extend(glob.glob(pattern))
    
    if not all_files:
        print("❌ No scraped data files found")
        print("💡 Make sure to run your Go scraper first:")
        print("   go run cmd/scraper/main.go --start-page 1 --end-page 50")
        return
    
    # Check processed files
    processed_file = "d1_processed_files.json"
    processed_files = []
    if os.path.exists(processed_file):
        with open(processed_file, 'r') as f:
            processed_files = json.load(f)
    
    new_files = [f for f in all_files if f not in processed_files]
    
    if not new_files:
        print("✅ All files already processed")
    else:
        print(f"📄 Found {len(new_files)} new files to process:")
        for file in new_files:
            print(f"   • {file}")
    
    # Step 2: Check D1 connection
    print("\\n🔍 Checking D1 database connection...")
    
    required_env = ['CLOUDFLARE_ACCOUNT_ID', 'D1_DATABASE_ID', 'CLOUDFLARE_API_TOKEN']
    missing_env = [var for var in required_env if not os.getenv(var)]
    
    if missing_env:
        print(f"❌ Missing environment variables: {missing_env}")
        print("💡 Make sure these are set in your .env file")
        return
    
    print("✅ D1 credentials found")
    
    # Step 3: Run D1 integration
    if new_files:
        success = run_command("python ultra_fast_d1.py", "Uploading new data to D1 database")
        
        if success:
            print("\\n🎉 Integration successful!")
        else:
            print("\\n❌ Integration failed")
            return
    
    # Step 4: Show current database status
    print("\\n📊 Current database status:")
    run_command("python ultra_fast_d1.py status", "Getting D1 database statistics")
    
    # Step 5: Instructions for dashboard
    print("\\n🎯 Next Steps:")
    print("1. 🖥️  Start the dashboard:")
    print("   streamlit run dashboard.py")
    print("\\n2. 🔍 New categories will be automatically available")
    print("\\n3. 📊 All scraped data is now in D1 database")
    print("\\n4. 🚀 Future scrapes: just run this script after scraping!")

if __name__ == "__main__":
    main()
