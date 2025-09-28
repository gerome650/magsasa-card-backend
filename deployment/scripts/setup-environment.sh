#!/bin/bash
# Environment Setup Script for MAGSASA-CARD

echo "🔧 Setting up MAGSASA-CARD environment..."

# Create environment-specific .env file
if [ "$1" = "development" ]; then
    cp deployment/configs/.env.development .env
    echo "✅ Development environment configured"
elif [ "$1" = "staging" ]; then
    cp deployment/configs/.env.staging .env
    echo "✅ Staging environment configured"
elif [ "$1" = "production" ]; then
    cp deployment/configs/.env.production .env
    echo "✅ Production environment configured"
else
    echo "❌ Usage: ./setup-environment.sh [development|staging|production]"
    exit 1
fi

echo "🔐 Remember to update API keys in .env file"
echo "📊 Environment ready for deployment"
