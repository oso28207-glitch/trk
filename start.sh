#!/bin/bash
apt-get update -y && apt-get install -y ffmpeg
cd backend
pip install -r requirements.txt
python app.py
