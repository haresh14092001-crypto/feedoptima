@echo off
echo Starting FeedOptima Frontend Server...
cd frontend
python -m http.server 3000
pause