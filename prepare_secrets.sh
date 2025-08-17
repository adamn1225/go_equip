#!/bin/bash
# Script to format JSON for Streamlit Secrets

echo "=== INSTRUCTIONS FOR STREAMLIT CLOUD ==="
echo "1. Deploy your app on Streamlit Cloud"
echo "2. Go to App Settings → Secrets"
echo "3. Copy and paste the content below:"
echo ""
echo "[database]"
echo 'contacts = """'
cat master_contact_database.json
echo '"""'
