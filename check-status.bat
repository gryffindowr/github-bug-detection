@echo off
echo ========================================
echo Checking Backend Status
echo ========================================
echo.

curl http://localhost:8000/ 2>nul

if %errorlevel% neq 0 (
    echo.
    echo ✗ Backend is not running!
    echo.
    echo Start it with:
    echo   cd backend\src
    echo   python api.py
) else (
    echo.
    echo.
    echo ========================================
    echo Testing OAuth Endpoint
    echo ========================================
    echo.
    curl http://localhost:8000/auth/github 2>nul
    
    if %errorlevel% neq 0 (
        echo.
        echo ⚠ OAuth endpoint not found (404)
        echo.
        echo SOLUTION: Restart your backend server
        echo   1. Press Ctrl+C in backend terminal
        echo   2. Run: python api.py
        echo   3. Look for: "Enhanced features enabled"
    )
)

echo.
echo.
pause
