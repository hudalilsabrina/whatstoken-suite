#!/usr/bin/env bash
set -e

echo "=== Installing WhatsToken Suite Dependencies ==="

python3 -m pip install -q -r requirements.txt
chmod +x main.py

echo ""
echo "=== Installation Complete! ==="
echo "Run interactive registration: ./main.py register"
echo "Login existing account:       ./main.py login -e <email> -p <password>"
echo "View balances:                ./main.py balance"
