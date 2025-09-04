#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gmail应用专用密码快速修复脚本
"""

import json
import webbrowser
from pathlib import Path

def main():
    print("🚀 Gmail认证问题快速修复向导")
    print("="*50)
    
    print("\n📋 请按以下步骤操作:")
    print("1. 重新生成Gmail应用专用密码（推荐）")
    print("2. 更新配置文件")
    print("3. 重新测试")
    
    choice = input("\n是否要现在打开Gmail应用专用密码设置页面？(y/N): ").lower().strip()
    
    if choice == 'y':
        print("\n🌐 正在打开Gmail应用专用密码设置页面...")
        webbrowser.open("https://myaccount.google.com/apppasswords")
        
        print("\n📝 请在打开的页面中执行以下操作:")
        print("1. 登录您的Google账户")
        print("2. 找到并删除旧的'M-Team自动登录'应用专用密码")
        print("3. 点击'选择应用' -> '邮件'")
        print("4. 点击'选择设备' -> '其他（自定义名称）'")
        print("5. 输入名称: 'M-Team自动登录'")
        print("6. 点击'生成'")
        print("7. 复制生成的16位密码（不要包含空格！）")
        
        new_password = input("\n请输入新生成的16位应用专用密码: ").strip()
        
        if len(new_password) >= 16:
            # 更新配置文件
            config_path = Path("config/config.json")
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    
                    config["gmail"]["password"] = new_password
                    
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=4, ensure_ascii=False)
                    
                    print("\n✅ 配置文件已更新！")
                    
                    # 运行测试
                    print("\n🔍 正在运行连接测试...")
                    import subprocess
                    result = subprocess.run(["python", "test_gmail_auth.py"], 
                                          capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        print("✅ 测试通过！现在可以运行M-Team自动登录了。")
                        print("\n🚀 运行命令: python run.py")
                    else:
                        print("❌ 测试失败，请检查密码是否正确输入")
                        print(f"错误信息: {result.stderr}")
                    
                except Exception as e:
                    print(f"❌ 更新配置文件失败: {e}")
            else:
                print("❌ 找不到配置文件 config/config.json")
        else:
            print("❌ 密码长度不正确，请确保输入完整的16位密码")
    
    else:
        print("\n💡 手动操作指南:")
        print("1. 访问: https://myaccount.google.com/apppasswords")
        print("2. 重新生成应用专用密码")
        print("3. 更新 config/config.json 中的password字段")
        print("4. 运行: python test_gmail_auth.py 验证")
        print("5. 运行: python run.py 开始登录")

if __name__ == "__main__":
    main()
