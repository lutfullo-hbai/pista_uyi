#!/bin/bash
# Ngrok Telegram Web App Setup - Step by Step

echo "🔧 Ngrok Telegram Web App Setup"
echo "================================"
echo ""

# Check if ngrok is running
check_ngrok() {
    response=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null)
    if [ -z "$response" ]; then
        echo "❌ ngrok not running on localhost:4040"
        return 1
    fi
    
    # Extract public URL
    url=$(echo "$response" | grep -o '"public_url":"[^"]*"' | head -1 | cut -d'"' -f4)
    if [ -n "$url" ]; then
        echo "✅ ngrok running"
        echo "   Public URL: $url"
        return 0
    else
        echo "❌ Could not extract ngrok URL"
        return 1
    fi
}

echo "Step 1: Check ngrok Status"
echo "=========================="
check_ngrok
NGROK_OK=$?

if [ $NGROK_OK -eq 0 ]; then
    echo ""
    echo "Step 2: Get Latest ngrok URL"
    echo "============================="
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo "URL: $NGROK_URL"
    
    echo ""
    echo "Step 3: Update .env file"
    echo "========================="
    echo "Edit .env and set:"
    echo "  WEB_APP_URL=$NGROK_URL"
    
    echo ""
    echo "Step 4: Restart Docker"
    echo "======================"
    echo "Run:"
    echo "  docker-compose down"
    echo "  docker-compose up -d"
    
    echo ""
    echo "Step 5: Test URL"
    echo "================"
    echo "Run:"
    echo "  curl $NGROK_URL"
    echo ""
    echo "Should see index.html"
else
    echo ""
    echo "❌ ngrok is NOT running"
    echo ""
    echo "To start ngrok:"
    echo "  1. Open new terminal"
    echo "  2. Run: ngrok http 8000"
    echo "  3. Copy the HTTPS URL from ngrok dashboard"
    echo "  4. Update .env with WEB_APP_URL=<ngrok-url>"
    echo "  5. Restart Docker: docker-compose down && docker-compose up -d"
fi
