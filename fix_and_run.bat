@echo off
chcp 65001 >nul
echo.
echo ════════════════════════════════════════════════════════════════
echo                    M-Team 自动登录工具修复器
echo ════════════════════════════════════════════════════════════════
echo.

echo 🔧 正在修复Python环境问题...
echo.

REM 检查各种Python安装方式
echo 🔍 检查Python安装状态...

set "PYTHON_FOUND=0"
set "PYTHON_CMD="

REM 方法1: 检查PATH中的python
where python >nul 2>&1
if %errorlevel% == 0 (
    python --version >nul 2>&1
    if %errorlevel% == 0 (
        echo ✅ 找到系统Python
        set "PYTHON_CMD=python"
        set "PYTHON_FOUND=1"
        goto PYTHON_DETECTED
    )
)

REM 方法2: 检查Python Launcher
py --version >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ 找到Python Launcher (py.exe)
    set "PYTHON_CMD=py"
    set "PYTHON_FOUND=1"
    goto PYTHON_DETECTED
)

REM 方法3: 检查Windows Store Python (新路径)
if exist "%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\python.exe" (
    "%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\python.exe" --version >nul 2>&1
    if %errorlevel% == 0 (
        echo ✅ 找到Windows Store Python
        set "PYTHON_CMD=%USERPROFILE%\AppData\Local\Microsoft\WindowsApps\python.exe"
        set "PYTHON_FOUND=1"
        goto PYTHON_DETECTED
    )
)

REM 方法4: 搜索常见安装路径
for /d %%i in ("C:\Python*") do (
    if exist "%%i\python.exe" (
        "%%i\python.exe" --version >nul 2>&1
        if %errorlevel% == 0 (
            echo ✅ 找到Python: %%i\python.exe
            set "PYTHON_CMD=%%i\python.exe"
            set "PYTHON_FOUND=1"
            goto PYTHON_DETECTED
        )
    )
)

REM 方法5: 检查Program Files
for /d %%i in ("C:\Program Files\Python*") do (
    if exist "%%i\python.exe" (
        "%%i\python.exe" --version >nul 2>&1
        if %errorlevel% == 0 (
            echo ✅ 找到Python: %%i\python.exe
            set "PYTHON_CMD=%%i\python.exe"
            set "PYTHON_FOUND=1"
            goto PYTHON_DETECTED
        )
    )
)

REM 如果找不到Python，显示安装指导
if %PYTHON_FOUND% == 0 (
    echo.
    echo ❌ 未找到Python安装！
    echo.
    echo 📥 请按照以下步骤安装Python：
    echo.
    echo 🏷️  方案1：从官网下载（推荐）
    echo   1. 访问 https://www.python.org/downloads/
    echo   2. 下载Python 3.9或更高版本
    echo   3. 安装时务必勾选 "Add Python to PATH"
    echo   4. 完成后重新运行此脚本
    echo.
    echo 🏷️  方案2：Microsoft Store安装
    echo   1. 打开Microsoft Store
    echo   2. 搜索并安装 "Python 3.x"
    echo   3. 完成后重新运行此脚本
    echo.
    echo 🏷️  方案3：使用Chocolatey
    echo   choco install python
    echo.
    pause
    exit /b 1
)

:PYTHON_DETECTED
echo.
echo 🐍 Python环境信息：
%PYTHON_CMD% --version
echo   路径: %PYTHON_CMD%
echo.

REM 创建新的虚拟环境
echo 📦 创建新的虚拟环境...
%PYTHON_CMD% -m venv venv
if %errorlevel% neq 0 (
    echo ❌ 虚拟环境创建失败
    echo 💡 尝试安装venv模块...
    %PYTHON_CMD% -m pip install virtualenv
    %PYTHON_CMD% -m virtualenv venv
    if %errorlevel% neq 0 (
        echo ❌ 仍然失败，请检查Python安装
        pause
        exit /b 1
    )
)
echo ✅ 虚拟环境创建成功

REM 激活虚拟环境
echo 🔄 激活虚拟环境...
call venv\Scripts\activate.bat

REM 升级pip
echo 📦 升级pip...
python -m pip install --upgrade pip

REM 安装依赖
echo 📦 安装Python依赖包...
if exist "requirements.txt" (
    python -m pip install -r requirements.txt
) else (
    echo 📦 安装基础依赖包...
    python -m pip install selenium requests beautifulsoup4 webdriver-manager python-dotenv
)

if %errorlevel% neq 0 (
    echo ❌ 依赖安装失败
    echo 💡 尝试使用国内镜像源...
    if exist "requirements.txt" (
        python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
    ) else (
        python -m pip install selenium requests beautifulsoup4 webdriver-manager python-dotenv -i https://pypi.tuna.tsinghua.edu.cn/simple/
    )
)

if %errorlevel% == 0 (
    echo ✅ 依赖包安装完成
) else (
    echo ⚠️ 部分依赖可能安装失败，但程序可能仍可运行
)

REM 运行安装脚本
if exist "install.py" (
    echo.
    echo 🔧 运行配置脚本...
    python install.py
)

REM 运行主程序
echo.
echo 🚀 启动M-Team自动登录工具...
echo ════════════════════════════════════════════════════════════════
python run.py

echo.
if %errorlevel% == 0 (
    echo ✅ 程序执行完成
) else (
    echo ❌ 程序执行出现问题，请查看日志文件
)

echo.
echo 📁 详细信息请查看 logs/ 目录中的日志文件
pause
