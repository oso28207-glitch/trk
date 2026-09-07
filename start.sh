#!/bin/bash
# تثبيت ffmpeg
apt-get update -y && apt-get install -y ffmpeg
# تشغيل التطبيق
cd backend
pip install -r requirements.txt
python app.py
