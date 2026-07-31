@echo off
echo Pushing latest server code to GitHub for Render deployment...
git add .
git commit -m "Update server admin logic and fixes"
git push
echo.
echo Push complete! Render will now automatically deploy the new code.
echo This usually takes about 1-2 minutes.
pause
