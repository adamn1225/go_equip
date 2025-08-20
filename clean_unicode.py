#!/usr/bin/env python3
"""
Unicode Character Cleaner for Contact Database
Replaces problematic Unicode characters with standard ASCII
"""

import json
import re

def clean_unicode_text(text):
    """Clean Unicode characters from text"""
    if not isinstance(text, str):
        return text
    
    # Replace common Unicode characters
    replacements = {
        '\u2018': "'",  # Left single quote
        '\u2019': "'",  # Right single quote  
        '\u201c': '"',  # Left double quote
        '\u201d': '"',  # Right double quote
        '\u2013': '-',  # En dash
        '\u2014': '--', # Em dash
        '\u00a0': ' ',  # Non-breaking space
        '\u003e': '>',  # Greater than
        '\u003c': '<',  # Less than
    }
    
    for unicode_char, replacement in replacements.items():
        text = text.replace(unicode_char, replacement)
    
    return text

def clean_json_file(input_file, output_file=None):
    """Clean Unicode characters from JSON file"""
    if output_file is None:
        output_file = input_file
    
    print(f"Cleaning Unicode characters from: {input_file}")
    
    # Load JSON
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Clean recursively
    def clean_dict_or_list(obj):
        if isinstance(obj, dict):
            return {key: clean_dict_or_list(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [clean_dict_or_list(item) for item in obj]
        elif isinstance(obj, str):
            return clean_unicode_text(obj)
        else:
            return obj
    
    cleaned_data = clean_dict_or_list(data)
    
    # Save cleaned JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
    
    print(f"Cleaned file saved to: {output_file}")

if __name__ == "__main__":
    # Clean the master database
    clean_json_file("master_contact_database.json")
    print("Unicode cleanup complete!")
