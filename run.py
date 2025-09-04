#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M-Team 自动登录工具 - 主启动脚本
"""

import sys
import os
import json
import logging
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from src.mteam_login import MTeamLogin

def check_config():
    """检查配置文件是否存在和正确"""
    possible_config_paths = [
        "config/config.json",
        "config.json",
    ]
    
    config_file = None
    for path in possible_config_paths:
        if os.path.exists(path):
            config_file = path
            break
    
    if config_file is None:
        print("❌ 配置文件不存在！")
        print("请先运行 'python install.py' 创建配置文件")
        return False
        
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        required_fields = [
            ("mteam", "username"), 
            ("mteam", "password"),
            ("gmail", "email"),
            ("gmail", "password")
        ]
        
        for field_path in required_fields:
            current = config
            for key in field_path:
                if key not in current:
                    print(f"❌ 配置文件缺少必要字段: {'.'.join(field_path)}")
                    return False
                current = current[key]
                
            if isinstance(current, str) and current.startswith("your_"):
                print(f"❌ 请修改配置文件中的 {'.'.join(field_path)} 字段")
                return False
                
        print("✅ 配置文件检查通过")
        return True
        
    except json.JSONDecodeError:
        print("❌ 配置文件格式错误，请检查JSON语法")
        return False
    except Exception as e:
        print(f"❌ 读取配置文件时发生错误: {e}")
        return False

def print_banner():
    """打印程序标题"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    M-Team 自动登录工具                        ║
║                                                              ║
║  功能: 自动登录M-Team并处理邮箱验证码                          ║
║  支持: Gmail IMAP和Selenium两种获取验证码方式                  ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def show_usage():
    """显示使用说明"""
    usage = """
📋 使用说明:

1. 首次安装运行:
   python install.py
   (这将自动下载Chrome浏览器、ChromeDriver并创建配置文件)

2. 配置Gmail应用专用密码:
   - 登录Google账户 -> 安全性 -> 两步验证
   - 生成应用专用密码（16位字符）用于IMAP访问

3. 编辑配置文件config/config.json:
   - 将 'your_mteam_username' 替换为真实的M-Team用户名
   - 将 'your_mteam_password' 替换为真实的M-Team密码  
   - 将 'your_gmail@gmail.com' 替换为真实的Gmail邮箱地址
   - 将 'your_gmail_app_password' 替换为Gmail应用专用密码

4. 运行程序:
   python run.py

💡 提示:
   - 所有浏览器和驱动都会自动下载到 bin/ 目录中
   - 无需手动安装Chrome或配置系统环境
   - 如果浏览器出现问题，删除 bin/ 目录后重新运行 install.py
    """
    print(usage)

def main():
    """主函数"""
    print_banner()
    
    # 检查配置文件
    if not check_config():
        show_usage()
        return
        
    print("🚀 开始执行M-Team自动登录...")
    print("=" * 60)
    
    try:
        # 创建并运行登录器（使用默认配置路径）
        mteam_login = MTeamLogin()
        success = mteam_login.run()
        
        print("=" * 60)
        if success:
            print("🎉 恭喜！M-Team自动登录成功！")
            print("📧 如果需要邮箱验证，验证码已自动获取并填入")
        else:
            print("😞 M-Team自动登录失败，请检查以下项目:")
            print("   - 用户名和密码是否正确")
            print("   - 网络连接是否正常") 
            print("   - Gmail配置是否正确")
            print("   - ChromeDriver是否正常工作")
            
    except FileNotFoundError as e:
        error_str = str(e)
        if "Chrome浏览器未找到" in error_str or "ChromeDriver未找到" in error_str:
            print(f"❌ {e}")
            print("💡 解决方法: 运行 'python install.py' 自动下载浏览器和驱动")
        else:
            print(f"❌ 文件未找到错误: {e}")
            print("请确保所有必要文件都存在")
    except ImportError as e:
        print(f"❌ 模块导入错误: {e}")
        print("请安装所有依赖: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ 运行时错误: {e}")
        logging.exception("详细错误信息:")
        
    print("\n📋 运行完成，查看 logs/ 目录中的日志文件获取详细信息")

if __name__ == "__main__":
    main() 