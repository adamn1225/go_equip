# Contact Analytics Dashboard

Executive dashboard for equipment dealer contact analysis and business intelligence.

## Features
- Priority scoring algorithm for high-value contacts
- Interactive visualizations and filtering
- Geographic distribution analysis
- Export capabilities for CRM integration

## Setup

### Virtual Environment
This project uses the `ai_env` virtual environment. To activate it:

```bash
# Option 1: Use the activation script
./activate_env.sh

# Option 2: Manual activation
source ai_env/bin/activate
```

### Running the Dashboard
```bash
# Activate environment first
source ai_env/bin/activate

# Run main dashboard (with authentication)
streamlit run dashboard.py --server.port=8503

# Or run standalone Heavy Haulers dashboard
streamlit run heavy_haulers_dashboard.py --server.port=8504
```

## Usage
Access the dashboard at: http://localhost:8503

Login credentials will be provided to authorized personnel.

## Data Sources
- MachineryTrader.com scraping results
- Master contact database with 4,900+ contacts
- Real-time analysis and scoring
