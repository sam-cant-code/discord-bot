#!/bin/bash

echo "Getting server IP..."
python3 -c "import urllib.request; print(urllib.request.urlopen('https://api.ipify.org').read().decode('utf8'))"
echo ""

pip install -r requirements.txt
python3 main.py