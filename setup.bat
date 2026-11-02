@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo   Knowledge Graph Pipeline - Multi-LLM Consensus Setup
echo ============================================================
echo.

REM ── 1. Python dependencies ──────────────────────────────────────────
echo [1/4] Installing Python dependencies...
where python >nul 2>nul
if errorlevel 1 (
    echo   ERROR: Python was not found on PATH. Install Python 3.10+ from
    echo   https://www.python.org/downloads/ and re-run this script.
    goto :end
)

python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo   ERROR: pip install failed. Check the output above.
    goto :end
)
echo   Python dependencies installed.
echo.

REM ── 2. Check Ollama is installed ────────────────────────────────────
echo [2/4] Checking for Ollama (required for Llama 3.1 / Qwen 3, local)...
where ollama >nul 2>nul
if errorlevel 1 (
    echo   Ollama was NOT found on PATH.
    echo   Download and install it from: https://ollama.com/download
    echo   After installing, re-run this script so the models below can be
    echo   checked / pulled.
    goto :ollama_missing
)
echo   Ollama is installed.
echo.

REM ── 3. Make sure the Ollama server is reachable ─────────────────────
echo [3/4] Checking Ollama models (llama3.1:8b, qwen3:8b)...
ollama list >nul 2>nul
if errorlevel 1 (
    echo   Could not reach the Ollama server. Start it with:
    echo       ollama serve
    echo   then re-run this script.
    goto :ollama_missing
)

ollama list | findstr /I "llama3.1:8b" >nul
if errorlevel 1 (
    echo   Model 'llama3.1:8b' is NOT installed. Pull it with:
    echo       ollama pull llama3.1:8b
    set MISSING_MODELS=1
) else (
    echo   Model 'llama3.1:8b' found.
)

ollama list | findstr /I "qwen3:8b" >nul
if errorlevel 1 (
    echo   Model 'qwen3:8b' is NOT installed. Pull it with:
    echo       ollama pull qwen3:8b
    set MISSING_MODELS=1
) else (
    echo   Model 'qwen3:8b' found.
)

if defined MISSING_MODELS (
    echo.
    echo   Run the two 'ollama pull' commands above, then re-run this script
    echo   to verify. The pipeline will still run without them ^(it will use
    echo   whichever models ARE available^), but you need at least 2 of the
    echo   3 models ^(Gemini/Llama/Qwen^) enabled for Multi-LLM Consensus.
)
echo.

:ollama_missing

REM ── 4. Gemini API key reminder ──────────────────────────────────────
echo [4/4] Gemini API key
echo   Set your key either as an environment variable:
echo       set GEMINI_API_KEY=your-key-here
echo   or by editing GEMINI_API_KEY directly in config\settings.py.
echo   Get a key at: https://aistudio.google.com/apikey
echo.

echo ============================================================
echo   Setup check complete.
echo.
echo   Next steps:
echo     1. (If needed) ollama pull llama3.1:8b
echo     2. (If needed) ollama pull qwen3:8b
echo     3. set GEMINI_API_KEY=your-key-here
echo     4. streamlit run app.py
echo        (or: python run_pipeline.py)
echo ============================================================

:end
pause
