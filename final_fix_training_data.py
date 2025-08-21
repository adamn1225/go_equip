#!/usr/bin/env python3
"""
Final Training Data Fix
Adds the missing 'type' field to screenshot objects
"""

import json
import os
from pathlib import Path

def final_fix_session_files():
    """Add missing 'type' field to screenshot objects"""
    
    data_dir = Path("captcha_training_data")
    solutions_dir = data_dir / "solutions"
    
    if not solutions_dir.exists():
        print("❌ Solutions directory not found!")
        return
    
    session_files = list(solutions_dir.glob("session_*.json"))
    fixed_count = 0
    
    print(f"🔧 Adding 'type' field to {len(session_files)} session files...")
    
    for session_file in session_files:
        try:
            # Read current session data
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            # Check if screenshots exist and need type field
            if 'screenshots' in session_data:
                needs_fix = False
                
                for screenshot in session_data['screenshots']:
                    if 'type' not in screenshot:
                        # Add type field - since these are scraped CAPTCHAs, mark as 'final'
                        screenshot['type'] = 'final'
                        needs_fix = True
                
                if needs_fix:
                    # Write back fixed session
                    with open(session_file, 'w') as f:
                        json.dump(session_data, f, indent=2)
                    
                    fixed_count += 1
                    
        except Exception as e:
            print(f"⚠️  Error processing {session_file}: {e}")
            continue
    
    print(f"✅ Added 'type' field to {fixed_count} session files!")
    print(f"📊 Screenshots now have 'type': 'final' for training")

def main():
    """Main function"""
    print("🔧 CAPTCHA Training Data Final Fix")
    print("=" * 40)
    
    final_fix_session_files()
    
    print("\n🎯 Training data is now fully ready!")
    print("Run: python ai/captcha_learning_system.py --mode info")

if __name__ == "__main__":
    main()
