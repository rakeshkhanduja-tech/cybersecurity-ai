@echo off
echo ============================================================
echo Starting Evident Security Intelligence Agent
echo ============================================================
echo.
echo Installing dependencies...
pip install flask flask-cors chromadb sentence-transformers pandas pydantic python-dotenv tqdm
echo.
echo Starting web server with mock LLM...
echo.
python main.py --mode web --mock-llm
