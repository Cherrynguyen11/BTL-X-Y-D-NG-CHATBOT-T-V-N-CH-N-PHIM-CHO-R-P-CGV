@echo off
title CGV Cinemas AI Assistant - BTL TTNT
color 0C
echo ======================================================================
echo          CGV CINEMAS AI ASSISTANT - TRO LY AI DIEN ANH
echo               Bai Tap Lon Mon Tri Tue Nhan Tao
echo ======================================================================
echo.
echo Dang kiem tra moi truong Python va thu vien...
python -m pip install -r requirements.txt
echo.
echo Dang khoi chay may chu AI tai http://localhost:8000
echo Ban co the mo trinh duyet va truy cap: http://localhost:8000
echo.
start http://localhost:8000
python run_server.py
pause
