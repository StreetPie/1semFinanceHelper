@echo off
chcp 65001 >nul
echo   Запуск Помощника...
echo.

REM Проверяем виртуальное окружение
if not exist ".venv" (
    echo Виртуальное окружение .venv не найдено в корне!
    echo Создайте его: python -m venv .venv
    echo Активируйте: .venv\Scripts\activate
    echo Установите зависимости: pip install -r requirements.txt
    pause
    exit /b 1
)

echo Виртуальное окружение найдено
echo Активируем...
call .venv\Scripts\activate.bat

echo.
echoПроверяем зависимости...
pip install -r backend/requirements.txt >nul 2>&1

echo.
echo Проверяем настройки БД...
if not exist "backend\.env" (
    echo ⚠Файл backend\.env не найден
    echo Создайте его с настройками подключения к MSSQL
    pause
    exit /b 1
)

echo.
echo Запуск backend (FastAPI)...
start "BACKEND" cmd /k "cd /d backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

echo Ожидаю запуск backend (3 сек)...
timeout /t 3 /nobreak >nul

echo.
echo Запуск frontend (Streamlit)...
start "FRONTEND" cmd /k "cd /d frontend && python -m streamlit run app.py"

echo.
echo Приложение запущено...
echo Backend API: http://localhost:8000
echo Frontend: http://localhost:8501
echo Документация API: http://localhost:8000/docs
echo.
echo.
pause