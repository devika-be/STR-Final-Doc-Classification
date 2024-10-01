#!/bin/bash

# Install Python dependencies from requirements.txt
echo "Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt

if [[ $? -ne 0 ]]; then
    echo "Python dependencies installation failed"
    exit 1
fi

# Download precompiled Tesseract binary
echo "Downloading precompiled Tesseract binary..."
curl -L -o tesseract.tar.gz https://github.com/tesseract-ocr/tesseract/releases/download/5.0.0/tesseract-5.0.0-linux-x86_64.tar.gz

if [[ $? -ne 0 ]]; then
    echo "Failed to download Tesseract binary"
    exit 1
fi

# Unpack the Tesseract binary
echo "Unpacking Tesseract..."
mkdir -p /tmp/tesseract
tar -xvzf tesseract.tar.gz -C /tmp/tesseract --strip-components=1

if [[ $? -ne 0 ]]; then
    echo "Extraction failed"
    exit 1
fi

# Add Tesseract binary to PATH
echo "Adding Tesseract to PATH..."
export PATH="/tmp/tesseract/bin:$PATH"

# Set the TESSDATA_PREFIX environment variable to Tesseract's data folder
echo "Setting TESSDATA_PREFIX..."
export TESSDATA_PREFIX="/tmp/tesseract/share/tessdata"

# Check if Tesseract is correctly installed and available
echo "Checking Tesseract installation..."
/tmp/tesseract/bin/tesseract --version

if [[ $? -ne 0 ]]; then
    echo "Tesseract installation failed"
    exit 1
else
    echo "Tesseract installed successfully"
fi

echo "Build completed successfully"





