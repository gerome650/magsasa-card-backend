#!/bin/bash
# MAGSASA-CARD Render Deployment Script
# This script deploys the staging environment to Render

echo "🚀 Deploying MAGSASA-CARD to Render Staging..."

# Check if we're in the right directory
if [ ! -f "app_production.py" ]; then
    echo "❌ Error: app_production.py not found. Run from project root."
    exit 1
fi

# Update deployment state
echo "📝 Updating deployment state..."
python3 -c "
import json
with open('deployment/deployment-state.json', 'r') as f:
    state = json.load(f)
state['environments']['staging']['status'] = 'deploying'
state['environments']['staging']['last_deployed'] = '$(date +%Y-%m-%d)'
with open('deployment/deployment-state.json', 'w') as f:
    json.dump(state, f, indent=2)
"

echo "✅ Ready for Render deployment!"
echo "📋 Next steps:"
echo "   1. Push code to GitHub"
echo "   2. Connect GitHub repo to Render"
echo "   3. Use deployment/render/render.yaml for configuration"
echo "   4. Set environment variables in Render dashboard"
