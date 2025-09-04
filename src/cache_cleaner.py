#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存清理模块
定期清理浏览器缓存和日志文件
"""

import os
import json
import shutil
import tempfile
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any


class CacheCleaner:
    """缓存清理器"""
    
    def __init__(self, config_file: str = "config/config.json"):
        """
        初始化缓存清理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = Path(config_file)
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def _save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"保存配置文件失败: {e}")
    
    def should_cleanup(self) -> bool:
        """检查是否需要清理缓存"""
        cleanup_config = self.config.get("cache_cleanup", {})
        
        # 检查是否启用
        if not cleanup_config.get("enabled", False):
            return False
        
        # 检查间隔天数
        interval_days = cleanup_config.get("interval_days", 7)
        last_cleanup = cleanup_config.get("last_cleanup")
        
        if not last_cleanup:
            # 第一次运行，需要清理
            return True
        
        try:
            last_cleanup_time = datetime.fromisoformat(last_cleanup)
            next_cleanup_time = last_cleanup_time + timedelta(days=interval_days)
            
            return datetime.now() >= next_cleanup_time
        except Exception as e:
            self.logger.warning(f"解析上次清理时间失败: {e}")
            return True
    
    def cleanup_browser_cache(self) -> bool:
        """清理浏览器缓存"""
        try:
            self.logger.info("开始清理浏览器缓存...")
            
            # 查找所有临时Chrome用户数据目录
            temp_dirs_cleaned = 0
            
            # 清理系统临时目录中的Chrome缓存
            temp_dir = Path(tempfile.gettempdir())
            
            # 查找Chrome相关的临时目录
            chrome_temp_patterns = [
                "chrome_*",
                "scoped_dir*",
                ".com.google.Chrome*"
            ]
            
            for pattern in chrome_temp_patterns:
                for temp_chrome_dir in temp_dir.glob(pattern):
                    if temp_chrome_dir.is_dir():
                        try:
                            shutil.rmtree(temp_chrome_dir)
                            temp_dirs_cleaned += 1
                            self.logger.info(f"已删除临时目录: {temp_chrome_dir}")
                        except Exception as e:
                            self.logger.warning(f"删除临时目录失败 {temp_chrome_dir}: {e}")
            
            # 清理项目内的任何缓存目录
            project_root = Path(__file__).parent.parent
            cache_dirs = [
                project_root / "cache",
                project_root / "browser_cache",
                project_root / ".chrome"
            ]
            
            for cache_dir in cache_dirs:
                if cache_dir.exists() and cache_dir.is_dir():
                    try:
                        shutil.rmtree(cache_dir)
                        self.logger.info(f"已删除项目缓存目录: {cache_dir}")
                    except Exception as e:
                        self.logger.warning(f"删除项目缓存目录失败 {cache_dir}: {e}")
            
            self.logger.info(f"浏览器缓存清理完成，共清理 {temp_dirs_cleaned} 个临时目录")
            return True
            
        except Exception as e:
            self.logger.error(f"清理浏览器缓存失败: {e}")
            return False
    
    def cleanup_logs(self) -> bool:
        """清理日志文件"""
        try:
            cleanup_config = self.config.get("cache_cleanup", {})
            keep_days = cleanup_config.get("keep_recent_logs_days", 3)
            
            self.logger.info(f"开始清理日志文件，保留最近 {keep_days} 天的日志...")
            
            # 日志目录
            project_root = Path(__file__).parent.parent
            logs_dir = project_root / "logs"
            
            if not logs_dir.exists():
                self.logger.info("日志目录不存在，无需清理")
                return True
            
            # 计算保留时间
            cutoff_time = datetime.now() - timedelta(days=keep_days)
            
            cleaned_files = 0
            total_size = 0
            
            for log_file in logs_dir.iterdir():
                if log_file.is_file():
                    try:
                        # 获取文件修改时间
                        file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                        
                        if file_time < cutoff_time:
                            file_size = log_file.stat().st_size
                            log_file.unlink()
                            cleaned_files += 1
                            total_size += file_size
                            self.logger.info(f"已删除旧日志文件: {log_file.name}")
                    except Exception as e:
                        self.logger.warning(f"删除日志文件失败 {log_file}: {e}")
            
            self.logger.info(f"日志清理完成，共删除 {cleaned_files} 个文件，释放空间 {total_size / 1024:.1f} KB")
            return True
            
        except Exception as e:
            self.logger.error(f"清理日志文件失败: {e}")
            return False
    
    def run_cleanup(self) -> bool:
        """执行完整的缓存清理"""
        if not self.should_cleanup():
            self.logger.debug("尚未到达清理时间，跳过缓存清理")
            return True
        
        self.logger.info("🧹 开始执行定期缓存清理...")
        
        cleanup_config = self.config.get("cache_cleanup", {})
        success = True
        
        # 清理浏览器缓存
        if cleanup_config.get("cleanup_browser_cache", True):
            if not self.cleanup_browser_cache():
                success = False
        
        # 清理日志文件
        if cleanup_config.get("cleanup_logs", True):
            if not self.cleanup_logs():
                success = False
        
        # 更新最后清理时间
        if success:
            self.config.setdefault("cache_cleanup", {})["last_cleanup"] = datetime.now().isoformat()
            self._save_config()
            self.logger.info("✅ 缓存清理完成")
        else:
            self.logger.warning("⚠️ 缓存清理部分失败")
        
        return success
    
    def force_cleanup(self) -> bool:
        """强制执行缓存清理（忽略时间间隔）"""
        self.logger.info("🧹 强制执行缓存清理...")
        
        cleanup_config = self.config.get("cache_cleanup", {})
        success = True
        
        # 清理浏览器缓存
        if cleanup_config.get("cleanup_browser_cache", True):
            if not self.cleanup_browser_cache():
                success = False
        
        # 清理日志文件
        if cleanup_config.get("cleanup_logs", True):
            if not self.cleanup_logs():
                success = False
        
        # 更新最后清理时间
        if success:
            self.config.setdefault("cache_cleanup", {})["last_cleanup"] = datetime.now().isoformat()
            self._save_config()
            self.logger.info("✅ 强制缓存清理完成")
        else:
            self.logger.warning("⚠️ 强制缓存清理部分失败")
        
        return success
    
    def get_cleanup_status(self) -> Dict[str, Any]:
        """获取清理状态信息"""
        cleanup_config = self.config.get("cache_cleanup", {})
        
        last_cleanup = cleanup_config.get("last_cleanup")
        next_cleanup = None
        
        if last_cleanup:
            try:
                last_cleanup_time = datetime.fromisoformat(last_cleanup)
                interval_days = cleanup_config.get("interval_days", 7)
                next_cleanup = last_cleanup_time + timedelta(days=interval_days)
            except:
                pass
        
        return {
            "enabled": cleanup_config.get("enabled", False),
            "interval_days": cleanup_config.get("interval_days", 7),
            "last_cleanup": last_cleanup,
            "next_cleanup": next_cleanup.isoformat() if next_cleanup else None,
            "should_cleanup": self.should_cleanup(),
            "cleanup_browser_cache": cleanup_config.get("cleanup_browser_cache", True),
            "cleanup_logs": cleanup_config.get("cleanup_logs", True),
            "keep_recent_logs_days": cleanup_config.get("keep_recent_logs_days", 3)
        }


def main():
    """测试缓存清理功能"""
    import sys
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    cleaner = CacheCleaner()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        # 强制清理
        print("执行强制缓存清理...")
        success = cleaner.force_cleanup()
    else:
        # 检查状态
        status = cleaner.get_cleanup_status()
        print("缓存清理状态:")
        for key, value in status.items():
            print(f"  {key}: {value}")
        
        # 执行清理
        success = cleaner.run_cleanup()
    
    if success:
        print("✅ 缓存清理成功")
    else:
        print("❌ 缓存清理失败")


if __name__ == "__main__":
    main()
