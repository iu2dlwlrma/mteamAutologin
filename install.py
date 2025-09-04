#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M-Team 自动登录工具 - 自动安装脚本
"""

import os
import sys
import subprocess
import json
import platform
from pathlib import Path
import urllib.request
import zipfile
import tarfile
import shutil
import tempfile

# Chrome 二进制版本配置
CHROME_VERSION = "140.0.7339.80"
# Chrome二进制下载链接（使用Chrome for Testing获取二进制文件）
CHROME_BASE_URL = f"https://storage.googleapis.com/chrome-for-testing-public/{CHROME_VERSION}"

def print_banner():
    """打印安装程序标题"""
    banner = f"""
╔══════════════════════════════════════════════════════════════╗
║            M-Team 自动登录工具 - 全自动安装程序                 ║
║                                                              ║
║  此脚本将下载Chrome {CHROME_VERSION}二进制版本到项目目录       ║
║  🍎 macOS用户: 自动处理权限和Gatekeeper安全设置               ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def get_system_info():
    """获取系统信息"""
    system = platform.system().lower()
    arch = platform.machine().lower()
    
    if arch in ['x86_64', 'amd64']:
        arch = 'x64'
    elif arch in ['aarch64', 'arm64']:
        arch = 'arm64'
    elif arch in ['i386', 'i686', 'x86']:
        arch = 'x32'
    
    print(f"🖥️  检测到系统: {system} {arch}")
    print(f"🌐 Chrome版本: {CHROME_VERSION} (二进制版本)")
    return system, arch

def download_file(url, dest_path, description="文件"):
    """下载文件并显示进度"""
    print(f"📥 正在下载 {description}...")
    
    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        def progress_hook(block_num, block_size, total_size):
            if total_size > 0:
                downloaded = block_num * block_size
                percent = min(100, downloaded * 100 / total_size)
                print(f"\r   进度: {percent:.1f}% ({downloaded//1024//1024}MB/{total_size//1024//1024}MB)", end='')
        
        urllib.request.urlretrieve(url, dest_path, progress_hook)
        print(f"\n✅ {description} 下载完成")
        return True
        
    except Exception as e:
        print(f"\n❌ {description} 下载失败: {e}")
        return False

def extract_archive(archive_path, extract_to, description="压缩包"):
    """解压缩文件"""
    print(f"📦 正在解压 {description}...")
    
    try:
        os.makedirs(extract_to, exist_ok=True)
        
        if archive_path.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
        elif archive_path.endswith(('.tar.gz', '.tgz')):
            with tarfile.open(archive_path, 'r:gz') as tar_ref:
                tar_ref.extractall(extract_to)
        else:
            print(f"❌ 不支持的压缩格式: {archive_path}")
            return False
            
        print(f"✅ {description} 解压完成")
        return True
        
    except Exception as e:
        print(f"❌ {description} 解压失败: {e}")
        return False

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("❌ Python版本过低！需要Python 3.7或更高版本")
        print(f"   当前版本: {version.major}.{version.minor}.{version.micro}")
        return False
    else:
        print(f"✅ Python版本检查通过: {version.major}.{version.minor}.{version.micro}")
        return True

def create_virtual_environment():
    """创建虚拟环境"""
    print("\n🐍 创建Python虚拟环境...")
    
    venv_path = Path("venv")
    
    # 检查虚拟环境是否已存在
    if venv_path.exists() and (venv_path / "pyvenv.cfg").exists():
        print("✅ 虚拟环境已存在，跳过创建")
        return True, get_venv_python()
    
    try:
        # 创建虚拟环境
        subprocess.check_call([sys.executable, "-m", "venv", "venv"])
        print("✅ 虚拟环境创建成功")
        
        venv_python = get_venv_python()
        if not venv_python or not os.path.exists(venv_python):
            print("❌ 无法找到虚拟环境中的Python可执行文件")
            return False, None
            
        print(f"   虚拟环境Python路径: {venv_python}")
        return True, venv_python
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 虚拟环境创建失败: {e}")
        return False, None
    except Exception as e:
        print(f"❌ 虚拟环境创建失败: {e}")
        return False, None

def get_venv_python():
    """获取虚拟环境中的Python可执行文件路径"""
    venv_path = Path("venv")
    
    if platform.system().lower() == "windows":
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"
    
    return str(python_exe) if python_exe.exists() else None

def get_venv_pip():
    """获取虚拟环境中的pip可执行文件路径"""
    venv_path = Path("venv")
    
    if platform.system().lower() == "windows":
        pip_exe = venv_path / "Scripts" / "pip.exe"
    else:
        pip_exe = venv_path / "bin" / "pip"
    
    return str(pip_exe) if pip_exe.exists() else None

def check_package_installed(package_name, venv_python=None):
    """检查包是否已安装（在虚拟环境中检查）"""
    try:
        # 从包名中提取实际的模块名（去掉版本号）
        module_name = package_name.split('==')[0].split('>=')[0].split('<=')[0].strip()
        
        if venv_python:
            # 在虚拟环境中检查
            result = subprocess.run([
                venv_python, "-c", f"import {module_name}"
            ], capture_output=True, text=True)
            return result.returncode == 0
        else:
            # 在当前环境中检查
            # 特殊处理一些包名映射
            name_mapping = {
                'beautifulsoup4': 'bs4',
                'python-dotenv': 'dotenv',
                'webdriver-manager': 'webdriver_manager'
            }
            
            import_name = name_mapping.get(module_name, module_name)
            
            # 尝试导入包
            __import__(import_name)
            return True
    except (ImportError, subprocess.SubprocessError):
        return False

def get_missing_packages(venv_python=None):
    """获取缺失的依赖包列表"""
    requirements_file = "requirements.txt"
    if not os.path.exists(requirements_file):
        return []
    
    try:
        with open(requirements_file, 'r', encoding='utf-8') as f:
            all_packages = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        missing_packages = []
        for package in all_packages:
            if not check_package_installed(package, venv_python):
                missing_packages.append(package)
        
        return missing_packages
    except Exception as e:
        print(f"⚠️ 读取requirements.txt失败: {e}")
        return []

def install_dependencies(venv_python=None):
    """在虚拟环境中安装Python依赖"""
    print("\n📦 检查Python依赖包...")
    
    requirements_file = "requirements.txt"
    if not os.path.exists(requirements_file):
        print("❌ requirements.txt 文件不存在！")
        return False
    
    # 使用虚拟环境的Python或系统Python
    python_exe = venv_python if venv_python else sys.executable
    
    # 检查缺失的包（在虚拟环境中检查）
    missing_packages = get_missing_packages(venv_python)
    
    if not missing_packages:
        print("✅ 所有依赖包已安装，跳过安装步骤")
        return True
    
    print(f"📋 发现 {len(missing_packages)} 个缺失的依赖包:")
    for pkg in missing_packages:
        print(f"   - {pkg}")
    
    # 在虚拟环境中安装缺失的包
    print(f"\n🔄 开始在虚拟环境中安装依赖包...")
    if venv_python:
        print(f"   使用虚拟环境: {venv_python}")
    
    # 首先升级pip
    try:
        subprocess.check_call([
            python_exe, "-m", "pip", "install", "--upgrade", "pip"
        ], stdout=subprocess.DEVNULL)
        print("✅ pip已升级到最新版本")
    except:
        print("⚠️ pip升级失败，继续使用当前版本")
    
    # 首先尝试批量安装缺失的包
    try:
        # 创建临时requirements文件只包含缺失的包
        temp_requirements = "temp_requirements.txt"
        with open(temp_requirements, 'w', encoding='utf-8') as f:
            for pkg in missing_packages:
                f.write(f"{pkg}\n")
        
        subprocess.check_call([
            python_exe, "-m", "pip", "install", "-r", temp_requirements
        ])
        
        # 清理临时文件
        os.remove(temp_requirements)
        
        print("✅ 依赖包安装完成")
        return True
    except subprocess.CalledProcessError as e:
        # 清理临时文件
        if os.path.exists(temp_requirements):
            os.remove(temp_requirements)
            
        print(f"⚠️  批量安装失败: {e}")
        print("🔄 尝试逐个安装依赖包...")
        
        # 逐个安装缺失的包
        try:
            failed_packages = []
            for package in missing_packages:
                if not install_single_package(package, python_exe):
                    failed_packages.append(package)
            
            if failed_packages:
                print(f"❌ 以下依赖包安装失败: {', '.join(failed_packages)}")
                
# lxml依赖已从requirements.txt中移除，不再需要特殊处理
                
                print("请手动运行以下命令尝试安装:")
                for pkg in failed_packages:
                    if venv_python:
                        print(f"  {python_exe} -m pip install {pkg}")
                    else:
                        print(f"  pip install {pkg}")
                return False
            else:
                print("✅ 所有依赖包安装完成")
                return True
                
        except Exception as e:
            print(f"❌ 依赖包安装失败: {e}")
            if venv_python:
                print(f"请手动运行: {python_exe} -m pip install -r requirements.txt")
            else:
                print("请手动运行: pip install -r requirements.txt")
            return False

def install_single_package(package, python_exe=None):
    """安装单个依赖包"""
    print(f"📦 正在安装: {package}")
    
    if not python_exe:
        python_exe = sys.executable
    
    # 普通包的安装
    try:
        subprocess.check_call([
            python_exe, "-m", "pip", "install", package
        ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        print(f"✅ {package} 安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {package} 安装失败")
        return False

# install_lxml_package函数已移除，因为lxml依赖已从requirements.txt中移除

# try_alternative_requirements函数已移除，因为备用文件已被删除

def download_chrome(system, arch):
    """下载Chrome二进制版本到项目目录"""
    print(f"\n🌐 正在下载Chrome二进制版本 {CHROME_VERSION}...")
    
    # 创建bin目录结构
    bin_dir = Path("bin")
    bin_dir.mkdir(exist_ok=True)
    
    browser_dir = bin_dir / "browsers"
    browser_dir.mkdir(exist_ok=True)
    
    chrome_dir = browser_dir / "chrome"
    
    if chrome_dir.exists() and any(chrome_dir.iterdir()):
        chrome_exe = find_chrome_executable(chrome_dir, system)
        if chrome_exe:
            print("✅ Chrome浏览器已存在，跳过下载")
            # macOS特殊处理：即使已存在也要确保权限正确
            if system == "darwin":
                setup_macos_chrome_permissions(chrome_exe)
            return True, str(chrome_exe)
    
    try:
        if system == "windows":
            if arch == "x64":
                url = f"{CHROME_BASE_URL}/win64/chrome-win64.zip"
                chrome_zip = browser_dir / "chrome-win64.zip"
            else:
                url = f"{CHROME_BASE_URL}/win32/chrome-win32.zip"
                chrome_zip = browser_dir / "chrome-win32.zip"
        elif system == "linux":
            url = f"{CHROME_BASE_URL}/linux64/chrome-linux64.zip"
            chrome_zip = browser_dir / "chrome-linux64.zip"
        elif system == "darwin":
            if arch == "arm64":
                url = f"{CHROME_BASE_URL}/mac-arm64/chrome-mac-arm64.zip"
            else:
                url = f"{CHROME_BASE_URL}/mac-x64/chrome-mac-x64.zip"
            chrome_zip = browser_dir / "chrome-mac.zip"
        else:
            print(f"❌ 不支持的操作系统: {system}")
            return False, None
        
        if download_file(url, str(chrome_zip), f"Chrome {CHROME_VERSION} 二进制包"):
            if extract_archive(str(chrome_zip), str(chrome_dir), f"Chrome {CHROME_VERSION}"):
                chrome_zip.unlink()
                chrome_exe = find_chrome_executable(chrome_dir, system)
                
                if chrome_exe:
                    # macOS特殊处理：设置权限和绕过Gatekeeper
                    if system == "darwin":
                        setup_macos_chrome_permissions(chrome_exe)
                    
                    print(f"✅ Chrome二进制版本安装完成: {chrome_exe}")
                    print(f"   Chrome版本: {CHROME_VERSION}")
                    return True, str(chrome_exe)
                else:
                    print("❌ 未找到Chrome可执行文件")
                    return False, None
            
    except Exception as e:
        print(f"❌ Chrome二进制版本下载失败: {e}")
        return False, None
    
    return False, None

def setup_macos_chrome_permissions(chrome_exe_path):
    """为macOS Chrome设置必要的权限和绕过Gatekeeper"""
    print("🍎 设置macOS Chrome权限...")
    
    try:
        chrome_exe = Path(chrome_exe_path)
        chrome_app = chrome_exe.parent.parent.parent  # 获取.app目录
        
        # 1. 设置Chrome可执行文件的执行权限
        print(f"   设置执行权限: {chrome_exe}")
        os.chmod(chrome_exe, 0o755)
        
        # 2. 移除Gatekeeper的隔离属性（绕过安全检查）
        print(f"   移除Gatekeeper隔离属性: {chrome_app}")
        try:
            subprocess.run([
                "xattr", "-rd", "com.apple.quarantine", str(chrome_app)
            ], check=False, capture_output=True)
        except FileNotFoundError:
            print("   ⚠️ xattr命令未找到，跳过Gatekeeper处理")
        
        # 3. 设置整个应用包的权限
        print(f"   设置应用包权限: {chrome_app}")
        subprocess.run([
            "chmod", "-R", "755", str(chrome_app)
        ], check=False, capture_output=True)
        
        print("✅ macOS Chrome权限设置完成")
        
    except Exception as e:
        print(f"⚠️ macOS权限设置失败: {e}")
        print("   程序将继续运行，如果遇到权限问题请手动设置")

def find_chrome_executable(chrome_dir, system):
    """查找Chrome可执行文件"""
    if system == "windows":
        for chrome_exe in chrome_dir.rglob("chrome.exe"):
            return chrome_exe
    elif system == "linux":
        for chrome_bin in chrome_dir.rglob("chrome"):
            if chrome_bin.is_file() and os.access(chrome_bin, os.X_OK):
                return chrome_bin
        for chrome_bin in chrome_dir.rglob("google-chrome"):
            if chrome_bin.is_file() and os.access(chrome_bin, os.X_OK):
                return chrome_bin
    elif system == "darwin":
        # 查找Chrome for Testing的应用
        for chrome_app in chrome_dir.rglob("Google Chrome for Testing.app"):
            chrome_exe = chrome_app / "Contents" / "MacOS" / "Google Chrome for Testing"
            if chrome_exe.exists():
                return chrome_exe
        # 如果找不到Testing版本，查找普通版本
        for chrome_app in chrome_dir.rglob("Google Chrome.app"):
            chrome_exe = chrome_app / "Contents" / "MacOS" / "Google Chrome"
            if chrome_exe.exists():
                return chrome_exe
    return None

def download_chromedriver_for_chrome(system, arch, chrome_path):
    """下载与Chrome 140.0.7339.80匹配的ChromeDriver"""
    print(f"\n🚗 正在下载匹配的ChromeDriver {CHROME_VERSION}...")
    
    # 创建bin目录结构
    bin_dir = Path("bin")
    bin_dir.mkdir(exist_ok=True)
    
    drivers_dir = bin_dir / "drivers"
    drivers_dir.mkdir(exist_ok=True)
    
    # 检查是否已存在
    if system == "windows":
        chromedriver_path = drivers_dir / "chromedriver.exe"
    else:
        chromedriver_path = drivers_dir / "chromedriver"
    
    if chromedriver_path.exists():
        print("✅ ChromeDriver已存在，跳过下载")
        return True, str(chromedriver_path)
    
    # 使用与Chrome相同的版本下载ChromeDriver
    driver_version = CHROME_VERSION
    print(f"📦 下载ChromeDriver版本: {driver_version}")
    
    try:
        # 构造下载URL（使用Chrome for Testing的ChromeDriver）
        if system == "windows":
            if arch == "x64":
                url = f"https://storage.googleapis.com/chrome-for-testing-public/{driver_version}/win64/chromedriver-win64.zip"
                driver_zip = drivers_dir / "chromedriver-win64.zip"
            else:
                url = f"https://storage.googleapis.com/chrome-for-testing-public/{driver_version}/win32/chromedriver-win32.zip"
                driver_zip = drivers_dir / "chromedriver-win32.zip"
        elif system == "linux":
            url = f"https://storage.googleapis.com/chrome-for-testing-public/{driver_version}/linux64/chromedriver-linux64.zip"
            driver_zip = drivers_dir / "chromedriver-linux64.zip"
        elif system == "darwin":
            if arch == "arm64":
                url = f"https://storage.googleapis.com/chrome-for-testing-public/{driver_version}/mac-arm64/chromedriver-mac-arm64.zip"
            else:
                url = f"https://storage.googleapis.com/chrome-for-testing-public/{driver_version}/mac-x64/chromedriver-mac-x64.zip"
            driver_zip = drivers_dir / "chromedriver-mac.zip"
        else:
            return False, None
        
        # 下载并安装ChromeDriver
        return extract_and_install_chromedriver(url, driver_zip, drivers_dir, chromedriver_path, driver_version)
        
    except Exception as e:
        print(f"❌ ChromeDriver下载失败: {e}")
        print(f"💡 如果链接失效，请检查版本 {CHROME_VERSION} 的可用性")
        return False, None

def extract_and_install_chromedriver(url, driver_zip, drivers_dir, chromedriver_path, version):
    """解压并安装ChromeDriver"""
    if download_file(url, str(driver_zip), "ChromeDriver"):
        # 解压到临时目录
        temp_extract = drivers_dir / "temp"
        if extract_archive(str(driver_zip), str(temp_extract), "ChromeDriver"):
            # 查找chromedriver文件
            chromedriver_file = None
            for file_path in temp_extract.rglob("chromedriver*"):
                if file_path.is_file() and (file_path.name == "chromedriver" or file_path.name == "chromedriver.exe"):
                    chromedriver_file = file_path
                    break
            
            if chromedriver_file:
                # 移动到正确位置
                shutil.move(str(chromedriver_file), str(chromedriver_path))
                
                # 在Linux/macOS上设置执行权限
                import os
                if not str(chromedriver_path).endswith('.exe'):
                    os.chmod(chromedriver_path, 0o755)
                
                # 清理临时文件
                driver_zip.unlink()
                shutil.rmtree(temp_extract)
                
                print(f"✅ ChromeDriver安装完成: {chromedriver_path}")
                print(f"   ChromeDriver版本: {version}")
                return True, str(chromedriver_path)
            else:
                print("❌ 未找到chromedriver文件")
                return False, None
    
    return False, None

def check_local_browsers():
    """检查本地下载的浏览器状态"""
    print("\n🔍 检查本地浏览器状态...")
    
    bin_dir = Path("bin")
    browser_dir = bin_dir / "browsers"
    drivers_dir = bin_dir / "drivers"
    
    # 检查Chrome
    chrome_found = False
    if browser_dir.exists():
        for chrome_exe in browser_dir.rglob("chrome*"):
            if chrome_exe.is_file() and ("chrome.exe" in chrome_exe.name.lower() or chrome_exe.name == "chrome"):
                print(f"✅ 找到Chrome浏览器: {chrome_exe}")
                chrome_found = True
                break
    
    if not chrome_found:
        print("❌ 未找到本地Chrome浏览器")
    
    # 检查ChromeDriver
    driver_found = False
    if drivers_dir.exists():
        for driver in drivers_dir.rglob("chromedriver*"):
            if driver.is_file():
                print(f"✅ 找到ChromeDriver: {driver}")
                driver_found = True
                break
    
    if not driver_found:
        print("❌ 未找到本地ChromeDriver")
    
    return chrome_found and driver_found

def check_system_chrome():
    """检查系统是否已安装Chrome（可选）"""
    print("\n🌐 检查系统Chrome浏览器（可选）...")
    
    system = platform.system().lower()
    chrome_paths = []
    
    if system == "windows":
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
    elif system == "darwin":  # macOS
        chrome_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ]
    elif system == "linux":
        chrome_paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium-browser"
        ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            print(f"✅ 系统Chrome已安装: {path}")
            return True
            
    print("ℹ️  未检测到系统Chrome（使用本地下载版本）")
    return False

def create_sample_config(chrome_path=None, chromedriver_path=None, venv_python=None):
    """创建示例配置文件"""
    print("\n⚙️  创建配置文件...")
    
    # 创建config目录
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    config_path = config_dir / "config.json"
    
    # 如果配置文件已存在，更新浏览器路径
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                existing_config = json.load(f)
            
            # 更新浏览器路径（转换为绝对路径）
            if chrome_path:
                existing_config["chrome_binary_path"] = os.path.abspath(chrome_path)
            if chromedriver_path:
                existing_config["chromedriver_path"] = os.path.abspath(chromedriver_path)
            if venv_python:
                existing_config["venv_python"] = os.path.abspath(venv_python)
            
            # 更新User-Agent到正确的Chrome版本
            existing_config["user_agent"] = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{CHROME_VERSION} Safari/537.36"
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(existing_config, f, indent=4, ensure_ascii=False)
            
            print("✅ 配置文件已更新")
            return True
            
        except Exception as e:
            print(f"⚠️ 更新配置文件失败，创建新的配置文件: {e}")
    
    # 创建新的配置文件
    sample_config = {
        "mteam": {
            "username": "your_mteam_username",
            "password": "your_mteam_password"
        },
        "gmail": {
            "email": "your_gmail@gmail.com",
            "password": "your_gmail_app_password",
            "method": "imap"
        },
        "headless": True,
        "user_agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{CHROME_VERSION} Safari/537.36",
    }
    
    # 添加本地浏览器路径（使用绝对路径）
    if chrome_path:
        sample_config["chrome_binary_path"] = os.path.abspath(chrome_path)
    if chromedriver_path:
        sample_config["chromedriver_path"] = os.path.abspath(chromedriver_path)
    if venv_python:
        sample_config["venv_python"] = os.path.abspath(venv_python)
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(sample_config, f, indent=4, ensure_ascii=False)
        print("✅ 配置文件已创建: config.json")
        return True
    except Exception as e:
        print(f"❌ 创建配置文件失败: {e}")
        return False

def interactive_config():
    """交互式配置"""
    print("\n🎯 交互式配置检查...")
    
    config_path = Path("config") / "config.json"
    if not config_path.exists():
        print("❌ 配置文件不存在，请先运行基本设置")
        return False
        
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except:
        print("❌ 读取配置文件失败")
        return False
    
    # 检查是否还是默认配置
    default_values = [
        "your_mteam_username", 
        "your_mteam_password",
        "your_gmail@gmail.com", 
        "your_gmail_app_password"
    ]
    
    current_values = [
        config.get("mteam", {}).get("username", ""),
        config.get("mteam", {}).get("password", ""),
        config.get("gmail", {}).get("email", ""),
        config.get("gmail", {}).get("password", "")
    ]
    
    # 如果所有值都不是默认值，说明已经配置过了
    has_defaults = any(current in default_values for current in current_values)
    
    if not has_defaults:
        print("✅ 检测到配置文件已包含有效配置，跳过交互式配置")
        return True
    
    print("⚠️  检测到配置文件中包含默认值，需要配置登录信息")
    print("是否要现在配置登录信息？(y/N): ", end='')
    if input().lower() != 'y':
        print("跳过交互式配置")
        return True
    
    print("\n📝 请输入以下信息:")
    
    # M-Team配置
    username = input("M-Team用户名: ").strip()
    if username:
        config["mteam"]["username"] = username
        
    password = input("M-Team密码: ").strip()
    if password:
        config["mteam"]["password"] = password
    
    # Gmail配置
    email = input("Gmail邮箱地址: ").strip()
    if email:
        config["gmail"]["email"] = email
        
    app_password = input("Gmail应用专用密码(16位): ").strip()
    if app_password:
        config["gmail"]["password"] = app_password
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        print("✅ 配置已保存")
        return True
    except Exception as e:
        print(f"❌ 保存配置失败: {e}")
        return False

def show_next_steps(venv_python=None):
    """显示下一步操作"""
    print("\n" + "="*60)
    print("🎉 自动安装完成！")
    print("="*60)
    
    print("\n📋 后续步骤:")
    print("1. 配置Gmail应用专用密码:")
    print("   - 登录Google账户 -> 安全性 -> 两步验证")
    print("   - 生成应用专用密码（16位字符）")
    
    print("\n2. 编辑配置文件 config/config.json:")
    print("   - 将 'your_mteam_username' 替换为真实的M-Team用户名")
    print("   - 将 'your_mteam_password' 替换为真实的M-Team密码")
    print("   - 将 'your_gmail@gmail.com' 替换为真实的Gmail邮箱")
    print("   - 将 'your_gmail_app_password' 替换为Gmail应用专用密码")
    
    print("\n3. 运行程序:")
    if venv_python:
        print(f"   {venv_python} run.py")
        print("   或者:")
        if platform.system().lower() == "windows":
            print("   venv\\Scripts\\activate && python run.py")
        else:
            print("   source venv/bin/activate && python run.py")
    else:
        print("   python run.py")
    
    print("\n📁 项目结构:")
    print("   ├── bin/               # 二进制文件目录")
    print(f"   │   ├── browsers/      # Chrome {CHROME_VERSION} 二进制版")
    print(f"   │   └── drivers/       # ChromeDriver {CHROME_VERSION}")
    print("   ├── config/            # 配置文件目录")
    print("   │   └── config.json    # 配置文件（需要编辑）")
    print("   ├── logs/              # 日志文件目录")
    if venv_python:
        print("   ├── venv/              # Python虚拟环境")
    print("   └── run.py             # 主程序")
    
    print("\n💡 提示:")
    print(f"   - Chrome和ChromeDriver版本: {CHROME_VERSION}")
    print("   - 使用二进制版本，无需系统安装Chrome")
    if venv_python:
        print("   - 使用虚拟环境，依赖包隔离管理")
    print("   - 版本固定，确保稳定性和兼容性")
    print("   - 如需重新安装，删除 bin/ 和 venv/ 目录后重新运行此脚本")
    
    print("\n📚 查看详细文档: README.md")

def main():
    """主安装流程"""
    print_banner()
    
    # 检查Python版本
    if not check_python_version():
        return
    
    # 获取系统信息
    system, arch = get_system_info()
    
    # 创建虚拟环境
    venv_ok, venv_python = create_virtual_environment()
    
    # 在虚拟环境中安装Python依赖
    deps_ok = install_dependencies(venv_python if venv_ok else None)
    
    # 自动下载Chrome浏览器
    chrome_ok, chrome_path = download_chrome(system, arch)
    
    # 自动下载匹配的ChromeDriver
    driver_ok, chromedriver_path = download_chromedriver_for_chrome(system, arch, chrome_path)
    
    # 创建配置文件
    config_ok = create_sample_config(chrome_path, chromedriver_path, venv_python if venv_ok else None)
    
    # 交互式配置（可选）
    if config_ok:
        interactive_config()
    
    # 显示安装结果
    print("\n" + "="*60)
    print("📊 安装完成结果:")
    print(f"   Python版本: ✅")
    print(f"   虚拟环境: {'✅' if venv_ok else '❌'}")
    print(f"   依赖包: {'✅' if deps_ok else '❌'}")
    print(f"   Chrome浏览器: {'✅' if chrome_ok else '❌'}")
    print(f"   ChromeDriver: {'✅' if driver_ok else '❌'}")
    print(f"   配置文件: {'✅' if config_ok else '❌'}")
    
    if venv_python:
        print(f"   虚拟环境Python: {venv_python}")
    if chrome_path:
        print(f"   Chrome路径: {chrome_path}")
    if chromedriver_path:
        print(f"   ChromeDriver路径: {chromedriver_path}")
    
    print(f"   Chrome版本: {CHROME_VERSION} (二进制版本)")
    
    if venv_ok and deps_ok and chrome_ok and driver_ok and config_ok:
        print("\n🎉 所有组件安装成功！")
        show_next_steps(venv_python if venv_ok else None)
    else:
        print("\n⚠️ 部分组件安装失败，但基本功能可能仍可使用")
        show_next_steps(venv_python if venv_ok else None)

if __name__ == "__main__":
    main() 