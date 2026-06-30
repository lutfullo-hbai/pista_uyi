#!/bin/bash
# Quick setup for local Telegram Web App testing

echo "🚀 Qurut Web App - Local Testing Setup"
echo "========================================"
echo ""

# Check if ngrok installed
if command -v ngrok &> /dev/null; then
    echo "✅ ngrok installed"
    echo ""
    echo "Start ngrok tunnel:"
    echo "  ngrok http 8000"
    echo ""
    echo "Then update .env with:"
    echo "  WEB_APP_URL=https://your-ngrok-url.ngrok.io"
else
    echo "⚠️  ngrok not installed"
    echo ""
    echo "Install ngrok:"
    echo "  1. Download: https://ngrok.com/download"
    echo "  2. Install and configure"
    echo "  3. Run: ngrok http 8000"
    echo ""
fi

echo ""
echo "Docker Status:"
docker ps | grep qurut

echo ""
echo "Test URLs:"
echo "  • Local: http://localhost:8000"
echo "  • Health: http://localhost:8000/health"
echo "  • API: http://localhost:8000/api/products"
echo ""
echo "After ngrok tunnel:"
echo "  • Telegram Web App URL:"
echo "    https://your-ngrok-url.ngrok.io"
