#!/usr/bin/env python3
"""
Category Database Manager for Streamlit Dashboard
Efficiently loads and manages split category databases
"""

import json
import os
import pandas as pd
from typing import Dict, List, Optional

class CategoryDatabaseManager:
    def __init__(self, index_file="master_database_index.json"):
        self.index_file = index_file
        self.index_data = None
        self.loaded_categories = {}
        self._load_index()
    
    def _load_index(self):
        """Load the master database index"""
        try:
            with open(self.index_file, 'r') as f:
                self.index_data = json.load(f)
        except FileNotFoundError:
            print("❌ Master database index not found. Please run split_master_database.py first.")
            self.index_data = None
    
    def get_available_categories(self) -> List[str]:
        """Get list of available categories"""
        if not self.index_data:
            return []
        return list(self.index_data.get('categories', {}).keys())
    
    def get_category_stats(self) -> Dict[str, int]:
        """Get contact counts for each category"""
        if not self.index_data:
            return {}
        return self.index_data.get('categories', {})
    
    def load_category(self, category: str) -> Optional[Dict]:
        """Load a specific category database"""
        if not self.index_data:
            return None
        
        # Check if already loaded
        if category in self.loaded_categories:
            return self.loaded_categories[category]
        
        # Get file path
        category_files = self.index_data.get('category_files', {})
        if category not in category_files:
            print(f"❌ Category '{category}' not found")
            return None
        
        file_path = category_files[category]
        
        try:
            with open(file_path, 'r') as f:
                category_data = json.load(f)
                self.loaded_categories[category] = category_data
                print(f"✅ Loaded {category}: {len(category_data.get('contacts', {}))} contacts")
                return category_data
        except FileNotFoundError:
            print(f"❌ Category file not found: {file_path}")
            return None
    
    def load_categories(self, categories: List[str]) -> Dict[str, Dict]:
        """Load multiple categories at once"""
        results = {}
        for category in categories:
            data = self.load_category(category)
            if data:
                results[category] = data
        return results
    
    def load_all_categories(self) -> Dict[str, Dict]:
        """Load all available categories"""
        return self.load_categories(self.get_available_categories())
    
    def get_combined_dataframe(self, categories: Optional[List[str]] = None) -> pd.DataFrame:
        """Get a combined pandas DataFrame for specified categories"""
        if categories is None:
            categories = self.get_available_categories()
        
        all_contacts = {}
        
        for category in categories:
            category_data = self.load_category(category)
            if category_data:
                contacts = category_data.get('contacts', {})
                all_contacts.update(contacts)
        
        # Convert to DataFrame (reuse your existing logic from DashboardAnalyzer)
        records = []
        for contact_id, contact in all_contacts.items():
            record = {
                'contact_id': contact_id,
                'seller_company': contact.get('seller_company', ''),
                'primary_phone': contact.get('primary_phone', ''),
                'primary_location': contact.get('primary_location', ''),
                'total_listings': contact.get('total_listings', 1),
                # Add all other fields...
            }
            records.append(record)
        
        return pd.DataFrame(records)
    
    def get_total_contacts(self) -> int:
        """Get total number of contacts across all categories"""
        if not self.index_data:
            return 0
        return self.index_data.get('metadata', {}).get('total_contacts', 0)

# Usage in your dashboard:
def get_category_manager():
    """Get the category database manager (cached)"""
    if 'category_manager' not in st.session_state:
        st.session_state.category_manager = CategoryDatabaseManager()
    return st.session_state.category_manager
