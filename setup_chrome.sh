#!/bin/bash
# Install Chrome/Chromium for Railway deployment

set -e

echo "Installing Chrome dependencies..."

# Install Chrome
if ! command -v google-chrome &> /dev/null && ! command -v chromium &> /dev/null; then
    echo "Installing Google Chrome..."
    apt-get update
    apt-get install -y wget gnupg
    
    # Add Google Chrome repository
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list
    
    # Install Chrome
    apt-get update
    apt-get install -y google-chrome-stable
    
    echo "Chrome installed successfully"
else
    echo "Chrome/Chromium already installed"
fi

# Verify installation
if command -v google-chrome &> /dev/null; then
    echo "Chrome found at: $(which google-chrome)"
elif command -v chromium &> /dev/null; then
    echo "Chromium found at: $(which chromium)"
else
    echo "Warning: Chrome/Chromium not found after installation"
fi
