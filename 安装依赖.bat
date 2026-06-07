@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Install ReelSage Dependencies

echo ============================================
echo   Install ReelSage Dependencies
echo ============================================
echo.

set "TUNA=https://pypi.tuna.tsinghua.edu.cn/simple"
set "TORCH_INDEX=https://download.pytorch.org/whl/cu124"

echo [1/5] Check Python (must be 3.11, to match ReelSage.exe) ...
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python not found. Please install Python 3.11.x first.
    echo     Download: https://www.python.org/downloads/release/python-3119/
    pause
    exit /b 1
)
python --version
rem ReelSage.exe 是用 Python 3.11 编译的，.venv 里的 torch 等必须是 cp311 ABI，
rem 否则 exe 加载 .venv 的 torch 会失败。这里强制校验 3.11。
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
echo %PYVER% | findstr /b "3.11." >nul
if errorlevel 1 (
    echo [X] 需要 Python 3.11.x，当前为 %PYVER% 。
    echo     请安装 Python 3.11（https://www.python.org/downloads/release/python-3119/）
    echo     安装时记得勾选 "Add python.exe to PATH"，再重新运行本脚本。
    pause
    exit /b 1
)
echo     Python 版本符合要求 (3.11.x)。
echo.

echo [2/5] Create / reuse virtual env .venv ...
if not exist ".venv\Scripts\python.exe" (
    echo     Creating clean .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [X] venv creation failed.
        pause
        exit /b 1
    )
    echo     .venv created.
) else (
    echo     .venv already exists, reuse it.
)
set "VENV_PY=.venv\Scripts\python.exe"
echo.

echo [3/5] Ensure pip is present, then upgrade ...
"%VENV_PY%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo     pip missing in venv, bootstrapping with ensurepip ...
    "%VENV_PY%" -m ensurepip --upgrade
)
"%VENV_PY%" -m pip install --upgrade pip -i %TUNA%
echo.

echo [4/5] Install PyTorch GPU (CUDA 12.4) + other deps ...
echo     -- Uninstalling old PyTorch if exists --
"%VENV_PY%" -m pip uninstall torch torchvision torchaudio -y >nul 2>&1
echo     -- Installing PyTorch + torchvision from CUDA index --
"%VENV_PY%" -m pip install torch torchvision torchaudio --index-url %TORCH_INDEX%
if errorlevel 1 (
    echo [X] PyTorch GPU install failed.
    echo     Check network. You can re-run this script to resume.
    pause
    exit /b 1
)
echo     -- Upgrading transformers to compatible version --
"%VENV_PY%" -m pip install "transformers>=4.45.0,<5.0.0" -i %TUNA%
echo     -- Installing remaining deps from mirror --
"%VENV_PY%" -m pip install accelerate opencv-python pillow numpy cryptography pystray -i %TUNA%
if errorlevel 1 (
    echo [X] Dependency install failed.
    echo     Re-run this script to resume.
    pause
    exit /b 1
)
echo.

echo [5/5] Verify key deps and GPU ...
"%VENV_PY%" -c "import torch, cv2, transformers, PIL, numpy, cryptography; print('cv2', cv2.__version__); print('torch', torch.__version__); print('CUDA available:', torch.cuda.is_available()); print('transformers', transformers.__version__)"
if errorlevel 1 (
    echo [X] Verification failed.
    pause
    exit /b 1
)
echo.

echo ============================================
echo   Dependencies installed successfully
echo ============================================
echo.
echo To start the app, double-click: start_ReelSage.bat  (or the Chinese-named launcher)
echo.
pause
