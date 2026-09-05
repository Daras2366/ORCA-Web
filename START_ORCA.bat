@echo off

echo ========================================
echo        ORCA MARINE INTELLIGENCE
echo ========================================
echo.

set PYTHON=%~dp0.venv\Scripts\python.exe

echo Using Python:
"%PYTHON%" -c "import sys; print(sys.executable)"
echo.

echo Starting Decision Layer on port 8000...
start "ORCA Decision Layer" cmd /k "cd /d %~dp0 && "%PYTHON%" -m uvicorn backend.agents.decision_layer.main:app --reload --port 8000"

timeout /t 2 /nobreak >nul

echo Starting Query Agent on port 8001...
start "ORCA Query Agent" cmd /k "cd /d %~dp0 && "%PYTHON%" -m uvicorn backend.agents.query_agent.main:app --reload --port 8001"

timeout /t 2 /nobreak >nul

echo Starting Ocean Agent on port 8002...
start "ORCA Ocean Agent" cmd /k "cd /d %~dp0 && "%PYTHON%" -m uvicorn backend.api.ocean_api:app --reload --port 8002"

timeout /t 2 /nobreak >nul

echo Starting Safety Agent on port 8003...
start "ORCA Safety Agent" cmd /k "cd /d %~dp0 && "%PYTHON%" -m uvicorn backend.api.safety_api:app --reload --port 8003"

timeout /t 2 /nobreak >nul

echo Starting Route Agent on port 8004...
start "ORCA Route Agent" cmd /k "cd /d %~dp0 && "%PYTHON%" -m uvicorn backend.api.route_api:app --reload --port 8004"

timeout /t 3 /nobreak >nul

echo Starting Frontend...
start "ORCA Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo       ORCA SERVICES STARTED
echo ========================================
echo.
echo Frontend:
echo http://localhost:8080
echo.
echo Decision API:
echo http://localhost:8000
echo.
echo Query API:
echo http://localhost:8001
echo.
echo Ocean API:
echo http://localhost:8002
echo.
echo Safety API:
echo http://localhost:8003
echo.
echo Routing API:
echo http://localhost:8004
echo.
echo Keep the ORCA terminal windows open.
echo ========================================

pause