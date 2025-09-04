#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动缓存清理工具
可以手动清理浏览器缓存和日志文件
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from src.cache_cleaner import CacheCleaner


def setup_logging(verbose: bool = False):
    """设置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/cache_cleanup.log', encoding='utf-8')
        ]
    )


def print_banner():
    """打印程序标题"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    M-Team 缓存清理工具                        ║
║                                                              ║
║  功能: 清理浏览器缓存和日志文件，释放磁盘空间                   ║
║  支持: 自动/手动清理，可配置清理间隔和保留策略                  ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def show_status(cleaner: CacheCleaner):
    """显示清理状态"""
    status = cleaner.get_cleanup_status()
    
    print("📊 当前缓存清理状态:")
    print(f"   • 清理功能: {'✅ 已启用' if status['enabled'] else '❌ 已禁用'}")
    print(f"   • 清理间隔: {status['interval_days']} 天")
    print(f"   • 浏览器缓存清理: {'✅ 启用' if status['cleanup_browser_cache'] else '❌ 禁用'}")
    print(f"   • 日志文件清理: {'✅ 启用' if status['cleanup_logs'] else '❌ 禁用'}")
    print(f"   • 保留日志天数: {status['keep_recent_logs_days']} 天")
    
    if status['last_cleanup']:
        print(f"   • 上次清理时间: {status['last_cleanup'][:19]}")
    else:
        print("   • 上次清理时间: 从未清理")
    
    if status['next_cleanup']:
        print(f"   • 下次清理时间: {status['next_cleanup'][:19]}")
    else:
        print("   • 下次清理时间: 未设置")
    
    print(f"   • 是否需要清理: {'✅ 是' if status['should_cleanup'] else '❌ 否'}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="M-Team 缓存清理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python clean_cache.py --status          # 查看清理状态
  python clean_cache.py --force           # 强制执行清理
  python clean_cache.py --auto            # 按配置自动清理
  python clean_cache.py --browser-only    # 仅清理浏览器缓存
  python clean_cache.py --logs-only       # 仅清理日志文件
        """
    )
    
    parser.add_argument('--status', action='store_true', help='显示清理状态')
    parser.add_argument('--force', action='store_true', help='强制执行清理（忽略时间间隔）')
    parser.add_argument('--auto', action='store_true', help='自动清理（根据配置决定是否清理）')
    parser.add_argument('--browser-only', action='store_true', help='仅清理浏览器缓存')
    parser.add_argument('--logs-only', action='store_true', help='仅清理日志文件')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细日志')
    
    args = parser.parse_args()
    
    # 如果没有参数，显示状态
    if not any([args.status, args.force, args.auto, args.browser_only, args.logs_only]):
        args.status = True
    
    print_banner()
    
    # 设置日志
    setup_logging(args.verbose)
    
    try:
        cleaner = CacheCleaner()
        
        if args.status:
            show_status(cleaner)
            return
        
        if args.browser_only:
            print("🧹 执行浏览器缓存清理...")
            success = cleaner.cleanup_browser_cache()
            if success:
                print("✅ 浏览器缓存清理完成")
            else:
                print("❌ 浏览器缓存清理失败")
        
        elif args.logs_only:
            print("🧹 执行日志文件清理...")
            success = cleaner.cleanup_logs()
            if success:
                print("✅ 日志文件清理完成")
            else:
                print("❌ 日志文件清理失败")
        
        elif args.force:
            print("🧹 执行强制缓存清理...")
            success = cleaner.force_cleanup()
            if success:
                print("✅ 强制缓存清理完成")
            else:
                print("❌ 强制缓存清理失败")
        
        elif args.auto:
            print("🧹 执行自动缓存清理...")
            if cleaner.should_cleanup():
                print("检测到需要清理缓存...")
                success = cleaner.run_cleanup()
                if success:
                    print("✅ 自动缓存清理完成")
                else:
                    print("❌ 自动缓存清理失败")
            else:
                print("🗂️ 当前不需要清理缓存")
                show_status(cleaner)
    
    except Exception as e:
        print(f"❌ 运行时错误: {e}")
        logging.exception("详细错误信息:")
        sys.exit(1)


if __name__ == "__main__":
    main()
