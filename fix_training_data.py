#!/usr/bin/env python3
"""
Fix Training Data Organization
Converts session files to the correct format expected by the learning system
"""

import json
import os
from pathlib import Path
from datetime import datetime

def fix_session_files():
    """Convert session files to expected format with screenshots array"""
    
    data_dir = Path("captcha_training_data")
    solutions_dir = data_dir / "solutions"
    screenshots_dir = data_dir / "screenshots"
    
    if not solutions_dir.exists():
        print("❌ Solutions directory not found!")
        return
        
    if not screenshots_dir.exists():
        print("❌ Screenshots directory not found!")
        return
    
    session_files = list(solutions_dir.glob("session_*.json"))
    fixed_count = 0
    
    print(f"🔧 Fixing {len(session_files)} session files...")
    
    for session_file in session_files:
        try:
            # Read current session data
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            # Check if already in correct format
            if 'screenshots' in session_data:
                continue
                
            # Extract screenshot filename from path
            screenshot_path = session_data.get('screenshot_path', '')
            if screenshot_path:
                screenshot_filename = Path(screenshot_path).name
                
                # Check if screenshot file exists
                full_screenshot_path = screenshots_dir / screenshot_filename
                if full_screenshot_path.exists():
                    # Convert to expected format
                    new_session_data = {
                        'session_id': session_data.get('session_id'),
                        'timestamp': session_data.get('timestamp'),
                        'success': session_data.get('success', False),
                        'method': session_data.get('method', 'automated_capture'),
                        'captcha_type': session_data.get('captcha_type', 'unknown'),
                        'processing_time': session_data.get('processing_time', 0),
                        'screenshots': [
                            {
                                'filename': screenshot_filename,
                                'timestamp': session_data.get('timestamp'),
                                'solution': session_data.get('solution', 'unlabeled'),
                                'success': session_data.get('success', False),
                                'needs_labeling': session_data.get('needs_labeling', True)
                            }
                        ],
                        'screenshot_count': 1
                    }
                    
                    # Write back fixed session
                    with open(session_file, 'w') as f:
                        json.dump(new_session_data, f, indent=2)
                    
                    fixed_count += 1
                    
        except Exception as e:
            print(f"⚠️  Error processing {session_file}: {e}")
            continue
    
    print(f"✅ Fixed {fixed_count} session files!")
    print(f"📊 Session files now have proper 'screenshots' array format")

def main():
    """Main function"""
    print("🔧 CAPTCHA Training Data Fixer")
    print("=" * 40)
    
    fix_session_files()
    
    print("\n🎯 Training data is now ready for the learning system!")
    print("Run: python ai/captcha_learning_system.py --mode info")

if __name__ == "__main__":
    main()
