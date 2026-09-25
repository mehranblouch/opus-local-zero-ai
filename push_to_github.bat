@echo off
title Push Opus Local to GitHub
echo ========================================================
echo   Uploading Opus Local to github.com/mehranblouch/opus-local-zero-ai
echo ========================================================
echo.

git config user.name "mehranblouch"
git config user.email "mehranblouch@users.noreply.github.com"

git init
git add .
git commit -m "Deploy Opus Local AI zero API engine"
git branch -M main
git remote remove origin >nul 2>&1
git remote add origin https://github.com/mehranblouch/opus-local-zero-ai.git
git push -u origin main --force

echo.
echo ========================================================
echo   Upload complete! Check https://github.com/mehranblouch/opus-local-zero-ai
echo ========================================================
pause
