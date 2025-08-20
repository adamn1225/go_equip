#!/bin/bash
# CRM Features Setup Script

echo "🎯 Setting up CRM features for Equipment Seller Dashboard..."

# Install SendGrid for email integration
echo "📧 Installing SendGrid for email functionality..."
pip install sendgrid

# Create data directories for CRM persistence
echo "📁 Creating CRM data directories..."
mkdir -p crm_data
touch crm_data/crm_activities.json
touch crm_data/lead_assignments.json

# Initialize empty JSON files
echo "{}" > crm_data/crm_activities.json
echo "{}" > crm_data/lead_assignments.json

# Update CRM features to use correct data path
sed -i 's/crm_activities.json/crm_data\/crm_activities.json/g' crm_features.py
sed -i 's/lead_assignments.json/crm_data\/lead_assignments.json/g' crm_features.py

echo "✅ CRM features setup complete!"
echo ""
echo "Next steps:"
echo "1. Get SendGrid API key from: https://app.sendgrid.com/settings/api_keys"
echo "2. Add to .env file: SENDGRID_API_KEY=your_key_here"
echo "3. Verify sender email at: https://app.sendgrid.com/settings/sender_auth"
echo "4. Run dashboard: streamlit run dashboard.py"
echo ""
echo "🚀 Your CRM-enabled dashboard is ready for 5 sales reps!"
