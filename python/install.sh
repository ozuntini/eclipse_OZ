#!/bin/bash
# Installation script for Eclipse_OZ Python migration
# For Raspberry Pi deployment

set -e  # Exit on any error

echo "=== Eclipse_OZ Python Installation ==="

# Update system
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install system dependencies
echo "Installing system dependencies..."
sudo apt install -y python3-pip python3-venv git
sudo apt install -y gphoto2 libgphoto2-dev libgphoto2-port12
sudo apt install -y build-essential pkg-config

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv ~/eclipse_env

# Activate environment
echo "Activating virtual environment..."
source ~/eclipse_env/bin/activate

# Install Python dependencies
echo "Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# USB configuration for multi-cameras
echo "Configuring USB rules for Canon cameras..."
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="04a9", MODE="0666"' | sudo tee /etc/udev/rules.d/99-canon-cameras.rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Test GPhoto2 installation
echo "Testing GPhoto2 installation..."
gphoto2 --version
echo "Camera detection test:"
gphoto2 --auto-detect

echo ""
echo "✅ Installation completed successfully!"
echo ""
echo "To activate the environment: source ~/eclipse_env/bin/activate"
echo "To run the application: python3 main.py config_eclipse.txt"
echo "For test mode: python3 main.py config_eclipse.txt --test-mode"
echo ""