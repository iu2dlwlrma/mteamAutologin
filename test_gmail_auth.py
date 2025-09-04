#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gmail 认证测试工具
用于快速诊断Gmail IMAP连接问题
"""

import json
import imaplib
import ssl
import time
from pathlib import Path

def test_gmail_connection():
    """测试Gmail IMAP连接"""
    print("🔍 开始Gmail IMAP连接测试...")
    
    # 读取配置文件
    config_path = Path("config/config.json")
    if not config_path.exists():
        print("❌ 找不到配置文件 config/config.json")
        return False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        gmail_config = config.get("gmail", {})
        email = gmail_config.get("email")
        password = gmail_config.get("password")
        
        if not email or not password:
            print("❌ Gmail配置信息不完整")
            return False
            
        print(f"📧 邮箱: {email[:3]}***{email[-10:]}")
        print(f"🔑 密码长度: {len(password)}位")
        print(f"🔑 密码格式: {'含空格' if ' ' in password else '无空格'}")
        
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
        return False
    
    # 测试连接
    print("\n🌐 测试SSL连接...")
    try:
        context = ssl.create_default_context()
        print("✅ SSL上下文创建成功")
        
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993, ssl_context=context)
        print("✅ Gmail IMAP服务器连接成功")
        
        print("\n🔐 测试认证...")
        mail.login(email, password)
        print("✅ Gmail认证成功！")
        
        print("\n📁 测试邮箱访问...")
        mail.select("inbox")
        print("✅ 收件箱访问成功！")
        
        # 测试搜索功能
        print("\n🔍 测试邮件搜索...")
        status, messages = mail.search(None, 'UNSEEN')
        if status == 'OK':
            unread_count = len(messages[0].split()) if messages[0] else 0
            print(f"✅ 邮件搜索成功，未读邮件数: {unread_count}")
        
        mail.close()
        mail.logout()
        print("\n🎉 所有测试通过！Gmail连接正常。")
        return True
        
    except imaplib.IMAP4.error as e:
        error_msg = str(e)
        print(f"❌ IMAP错误: {error_msg}")
        
        if "AUTHENTICATIONFAILED" in error_msg:
            print("\n🔧 认证失败解决方案:")
            print("1. 重新生成Gmail应用专用密码:")
            print("   https://myaccount.google.com/apppasswords")
            print("2. 删除旧的'M-Team自动登录'密码")
            print("3. 创建新密码（选择'邮件'和'其他设备'）")
            print("4. 复制16位密码（不要包含空格）")
            print("5. 更新config/config.json文件")
            
        return False
        
    except ssl.SSLError as e:
        print(f"❌ SSL连接错误: {e}")
        print("\n🔧 SSL错误解决方案:")
        print("1. 检查网络连接是否稳定")
        print("2. 尝试更换网络环境")
        print("3. 检查防火墙设置")
        print("4. 稍后重试")
        return False
        
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        return False

def provide_solution():
    """提供解决方案"""
    print("\n" + "="*60)
    print("🛠️  Gmail认证问题解决方案")
    print("="*60)
    
    print("\n📋 立即操作步骤:")
    print("1. 打开浏览器访问: https://myaccount.google.com/apppasswords")
    print("2. 登录您的Google账户")
    print("3. 找到并删除旧的'M-Team自动登录'应用专用密码")
    print("4. 点击'生成应用专用密码'")
    print("5. 选择应用: '邮件'")
    print("6. 选择设备: '其他（自定义名称）'")
    print("7. 输入名称: 'M-Team自动登录'")
    print("8. 复制生成的16位密码（注意：不要包含空格！）")
    
    print("\n📝 更新配置文件:")
    print('编辑 config/config.json 文件，更新Gmail密码:')
    print('  "gmail": {')
    print('    "email": "您的邮箱地址",')
    print('    "password": "您的16位新密码",  ← 更新这里')
    print('    "method": "imap"')
    print('  }')
    
    print("\n🔄 重新运行测试:")
    print("python test_gmail_auth.py")

if __name__ == "__main__":
    print("Gmail IMAP连接测试工具")
    print("="*40)
    
    success = test_gmail_connection()
    
    if not success:
        provide_solution()
        print(f"\n💡 提示: 完成配置更新后，请重新运行此脚本验证")
    else:
        print("\n✅ Gmail配置正常，可以正常使用M-Team自动登录功能！")
