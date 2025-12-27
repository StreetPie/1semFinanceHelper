import subprocess
import sys

subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"])
subprocess.Popen([sys.executable, "-m", "streamlit", "run", "frontend/app.py", "--server.port", "8501"])