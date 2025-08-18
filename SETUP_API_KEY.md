# OpenAI API Key Setup

## Shared Team API Key (Current Setup)

To enable AI features for all team members:

1. **Get an OpenAI API Key**: Visit https://platform.openai.com/api-keys
2. **Edit the `.env` file**: Replace `your_openai_api_key_here` with your actual API key
3. **Restart the dashboard**: Stop and restart the Streamlit server

```bash
# In .env file
OPENAI_API_KEY=sk-your-actual-api-key-here
```

## Benefits of Shared Key:
- ✅ All team members get AI features automatically
- ✅ No need to enter keys manually
- ✅ Centralized cost management
- ✅ Consistent experience across the team

## Individual API Key Option (Available on branch)

If you prefer individual API keys, switch to the `individual-api-keys` branch:

```bash
git checkout individual-api-keys
```

This preserves the original setup where each user enters their own API key.

## Switching Between Setups:

```bash
# For shared API key (recommended for teams)
git checkout main

# For individual API keys (better for cost control)
git checkout individual-api-keys
```

## Testing the Setup:

1. Run the dashboard: `streamlit run dashboard.py --server.port=8502`
2. Select "🚛 Heavy Haulers Sales Intelligence"
3. Go to the "🤖 AI-Powered Business Insights" tab
4. You should see "✅ Team OpenAI API key configured" if set up correctly
