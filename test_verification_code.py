#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gmail验证码提取测试脚本
用于调试和验证Gmail验证码获取功能
"""

import sys
import os
import json
import logging
from pathlib import Path

# 添加src目录到路径
sys.path.append('src')

from gmail_client import GmailClient

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.DEBUG,  # 设置为DEBUG级别以显示更多信息
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('verification_code_test.log', encoding='utf-8')
        ]
    )

def load_config():
    """加载配置文件"""
    config_path = Path("config/config.json")
    
    if not config_path.exists():
        print("❌ 配置文件不存在，请先运行 install.py")
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
        return None

def test_gmail_verification_code():
    """测试Gmail验证码获取"""
    print("🔍 Gmail验证码提取测试")
    print("=" * 50)
    
    # 设置日志
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # 加载配置
    config = load_config()
    if not config:
        return False
    
    gmail_config = config.get("gmail")
    if not gmail_config:
        print("❌ Gmail配置不存在")
        return False
    
    print(f"📧 测试邮箱: {gmail_config['email']}")
    print(f"🔐 应用密码: {'*' * len(gmail_config['password'])}")
    print()
    
    try:
        # 创建Gmail客户端
        gmail_client = GmailClient(gmail_config)
        
        print("⏳ 开始获取最新验证码...")
        print("💡 提示：请先手动触发M-Team发送验证码邮件")
        print("💡 或者等待现有的验证码邮件...")
        print()
        
        # 获取验证码（超时时间设为60秒）
        verification_code = gmail_client.get_verification_code(timeout=60)
        
        if verification_code:
            print(f"✅ 成功获取验证码: {verification_code}")
            print(f"✅ 验证码长度: {len(verification_code)}")
            print(f"✅ 验证码类型: {'纯数字' if verification_code.isdigit() else '字母数字混合'}")
            return True
        else:
            print("❌ 未能获取验证码")
            print("💡 可能原因:")
            print("   1. 没有新的验证码邮件")
            print("   2. 验证码格式识别失败")
            print("   3. Gmail连接问题")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        return False

def main():
    """主函数"""
    print("Gmail验证码提取测试工具")
    print("适用于M-Team自动登录项目")
    print()
    
    success = test_gmail_verification_code()
    
    print()
    print("=" * 50)
    if success:
        print("✅ 测试完成：验证码提取正常")
    else:
        print("❌ 测试完成：验证码提取失败")
        print("请检查日志文件 verification_code_test.log 获取详细信息")

if __name__ == "__main__":
    main()
