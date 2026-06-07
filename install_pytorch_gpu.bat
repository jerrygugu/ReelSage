@echo off
echo ========================================
echo 安装 PyTorch GPU 版本
echo ========================================
echo.
echo 你的显卡: RTX 3090 24GB
echo 驱动版本: 610.47
echo.
echo 将安装 PyTorch GPU 版本 (CUDA 12.4)
echo.
pause

echo.
echo 1. 卸载当前的 CPU 版本 PyTorch...
.venv\Scripts\python.exe -m pip uninstall -y torch torchvision torchaudio

echo.
echo 2. 安装 GPU 版本 PyTorch (CUDA 12.4)...
.venv\Scripts\python.exe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

echo.
echo 3. 验证安装...
.venv\Scripts\python.exe check_gpu.py

echo.
echo ========================================
echo 安装完成！
echo ========================================
pause
