# M-Team 自动登录工具

一个自动登录M-Team网站并处理邮箱验证码的Python工具。

## 🔧 系统要求

- **Python版本**: 3.7 或更高版本
- **操作系统**: Windows 10/11, Linux, macOS
- **Chrome浏览器**: 自动下载最新版本

## ✨ 特性

- 📧 **智能验证码**：自动获取Gmail邮箱验证码
- 🛡️ **反检测模式**：使用Chrome二进制版本，内置反爬虫检测机制
- 💻 **跨平台支持**：支持Windows、Linux、macOS

## 项目结构

```text
mteam/
├── src/                    # 源代码目录
│   ├── mteam_login.py     # 主登录脚本
│   └── gmail_client.py    # Gmail验证码获取客户端
├── bin/                    # 二进制文件目录（自动生成）
│   ├── browsers/          # Chrome 140.0.7339.80 二进制版本
│   └── drivers/           # ChromeDriver 140.0.7339.80
├── config/                 # 配置文件目录（自动生成）
│   └── config.json        # 配置文件
├── logs/                   # 日志文件目录（自动生成）
├── requirements.txt       # Python依赖
├── run.py                 # 主启动脚本
├── install.py             # 自动安装脚本
├── start.bat              # Windows启动脚本
├── start.sh               # Linux/macOS启动脚本
├── start_hidden.vbs       # Windows静默运行脚本（极简版）
├── start_silent.vbs       # Windows静默运行脚本（带通知）
├── venv/                  # Python虚拟环境（自动创建）
└── README.md              # 项目说明
```

## 快速开始

### 1. 自动安装（推荐）

运行自动安装脚本，它会自动下载Chrome浏览器、ChromeDriver并创建配置文件：

```bash
python install.py
```

或者直接双击运行：

- Windows: `start.bat`
- Linux/macOS: `start.sh` (首次需要设置执行权限，见下方说明)

### 2. 设置脚本执行权限 (macOS/Linux)

**⚠️ 重要**: 在macOS和Linux系统下，首次使用需要给脚本设置执行权限：

```bash
# 给start.sh脚本设置执行权限
chmod +x start.sh

# 然后就可以直接运行
./start.sh
```

**或者使用以下任一方法**：

```bash
# 方法1: 直接用bash运行
bash start.sh

# 方法2: 使用Python直接安装
python3 install.py
```

### 3. 配置Gmail应用专用密码

1. 登录Google账户
2. 进入 安全性 → 两步验证
3. 生成应用专用密码（16位字符）用于IMAP访问
4. 记录这个密码

### 4. 编辑配置文件

安装完成后，编辑 `config/config.json` 文件，将默认值替换为真实信息：

```json
{
    "mteam": {
        "username": "你的M-Team用户名",
        "password": "你的M-Team密码"
    },
    "gmail": {
        "email": "你的Gmail邮箱",
        "password": "Gmail应用专用密码",
        "method": "imap"
    },
    "headless": true,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "proxy": ""
}
```

### 5. 运行程序

```bash
# 方法1: 使用Python直接运行
python run.py

# 方法2: Windows下使用批处理文件
start.bat

# 方法3: Windows静默运行（推荐用于定时任务）
start_hidden.vbs    # 极简版，无任何通知
start_silent.vbs    # 带现代Toast通知

```

## 🔧 VBS脚本高级配置

### VBS脚本说明

- **start_hidden.vbs**: 极简版，完全静默运行，无任何通知
- **start_silent.vbs**: 增强版，支持现代Windows Toast通知

### 开机启动配置

#### 方法1: 启动文件夹（推荐）

1. **按下** `Win + R`，输入 `shell:startup`
2. **将VBS创建快捷方式复制到启动文件夹**
3. **重启电脑验证**

#### 方法2: 任务计划程序

1. **打开任务计划程序** (`taskschd.msc`)
2. **创建基本任务**:
   - 名称: `M-Team自动登录`
   - 触发器: `计算机启动时`
   - 操作: `启动程序`
   - 程序: `wscript.exe`
   - 参数: `"D:\Develop\messypyscript\mteam\start_silent.vbs"`
3. **完成并测试**

#### 方法3: 注册表（高级用户）

1. **打开注册表编辑器** (`regedit`)
2. **导航到**: `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`
3. **新建字符串值**:
   - 名称: `MTeamLogin`
   - 数值: `wscript.exe "D:\Develop\messypyscript\mteam\start_silent.vbs"`

### VBS脚本特性

- ✅ 完全后台运行，不显示命令行窗口
- ✅ Windows 10/11 原生Toast通知支持
- ✅ 自动错误处理和通知
- ✅ 适合定时任务和开机启动

## 🐍 虚拟环境管理

### 自动创建虚拟环境

安装脚本会自动创建并使用Python虚拟环境，确保依赖包的隔离：

- ✅ **自动创建**: `install.py` 自动创建 `venv` 虚拟环境
- ✅ **依赖隔离**: 所有依赖包安装在虚拟环境中，不影响系统Python
- ✅ **版本固定**: 使用 `requirements.txt` 固定依赖版本
- ✅ **自动激活**: 启动脚本自动使用虚拟环境Python

### 手动管理虚拟环境

#### Windows

```batch
# 激活虚拟环境
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行程序
python run.py

# 退出虚拟环境
deactivate
```

#### Linux/macOS

```bash
# 首次使用设置执行权限
chmod +x start.sh

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行程序
python run.py

# 退出虚拟环境
deactivate
```

### 虚拟环境优势

- 🔒 **依赖隔离**: 不同项目的依赖包互不干扰
- 🛡️ **系统保护**: 避免污染系统Python环境
- 📦 **版本管理**: 精确控制每个包的版本
- 🚀 **快速部署**: 可轻松复制到其他机器

## 功能特性

- ✅ 自动登录M-Team网站
- ✅ 自动处理邮箱验证码
- ✅ 反自动化检测

## 依赖说明

- `selenium`: 浏览器自动化
- `webdriver-manager`: 自动管理ChromeDriver
- `requests`: HTTP请求
- `imaplib2`: IMAP邮件协议

## 故障排除

### macOS权限问题 🍎

如果在macOS上遇到 "Failed to create Chrome process" 错误：

#### 自动修复（推荐）

重新运行安装脚本，它会自动设置权限：

```bash
python3 install.py
```

#### 手动修复

如果自动修复失败，请手动执行以下命令：

```bash
# 1. 设置Chrome可执行文件权限
chmod +x "bin/browsers/chrome/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"

# 2. 移除Gatekeeper隔离属性
xattr -rd com.apple.quarantine "bin/browsers/chrome/chrome-mac-arm64/Google Chrome for Testing.app"

# 3. 设置整个应用包权限
chmod -R 755 "bin/browsers/chrome/chrome-mac-arm64/Google Chrome for Testing.app"
```

#### 系统设置

如果仍然失败，可能需要在 **系统偏好设置** → **安全性与隐私** 中：

1. 点击 “允许” Chrome for Testing 运行
2. 或者在 "开发者工具" 中添加 Terminal 应用

### 验证码获取失败

1. 检查Gmail应用专用密码是否正确
2. 确保启用了两步验证
3. 检查网络连接
4. 查看日志文件 `logs/mteam_login_*.log`

### ChromeDriver问题

1. 确保安装了Chrome浏览器
2. ChromeDriver会自动下载，如果失败可手动安装
3. 检查Chrome版本与ChromeDriver版本是否匹配
4. **macOS用户**: 确保ChromeDriver有执行权限 (`chmod +x bin/drivers/chromedriver`)

## 日志文件

程序运行时会生成详细的日志文件 `mteam_login.log`，包含：

- 登录过程详情
- 验证码获取过程
- 错误信息和调试信息

## 安全说明

- 配置文件包含敏感信息，请妥善保管
- 建议使用Gmail应用专用密码而非主密码
- 可以设置 `headless: true` 在后台运行浏览器

## 许可证

本项目仅供学习和个人使用，请遵守相关网站的使用条款。
