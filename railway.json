#!/bin/bash
apt-get update -y && apt-get install -y ffmpeg
cd backend
pip3 install -r requirements.txt || pip install -r requirements.txt
python3 app.py || python app.py
