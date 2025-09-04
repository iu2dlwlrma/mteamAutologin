#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M-Team 自动登录和邮箱验证码获取脚本
"""

import time
import re
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import requests
from gmail_client import GmailClient
import os

import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(script_dir, '..', 'logs')
os.makedirs(log_dir, exist_ok=True)

current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_file_path = os.path.join(log_dir, f'mteam_login_{current_time}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class MTeamLogin:
    def __init__(self, config_file: str = None):
        """
        初始化 M-Team 登录器
        
        Args:
            config_file: 配置文件路径
        """
        # 先初始化logger，因为load_config方法中需要使用
        self.logger = logging.getLogger(__name__)
        
        # 如果未指定配置文件，使用默认路径
        if config_file is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_file = os.path.join(script_dir, '..', 'config', 'config.json')
            # 标准化路径，确保跨平台兼容
            config_file = os.path.normpath(config_file)
        
        # 然后加载配置
        self.config = self.load_config(config_file)
        self.driver = None
        self.gmail_client = None
        
        # 网站URLs
        self.login_url = "https://kp.m-team.cc/login"
        self.base_url = "https://kp.m-team.cc"
        
    def load_config(self, config_file: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            # 如果是相对路径，尝试多个可能的位置
            if not os.path.isabs(config_file):
                # 获取当前脚本的目录
                script_dir = os.path.dirname(os.path.abspath(__file__))
                
                # 尝试的路径列表
                possible_paths = [
                    config_file,  # 相对于当前工作目录
                    os.path.join(script_dir, config_file),  # 相对于脚本目录
                    os.path.join(script_dir, '..', config_file),  # 相对于脚本上级目录
                    os.path.join(script_dir, '..', 'config', 'config.json'),  # 新的config目录
                    'config.json',  # 兼容性：原始根目录
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        config_file = path
                        break
                else:
                    # 如果所有路径都不存在，使用原始路径并让它抛出FileNotFoundError
                    pass
            
            with open(config_file, 'r', encoding='utf-8') as f:
                self.logger.info(f"成功加载配置文件: {config_file}")
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"配置文件 {config_file} 不存在")
            raise
        except json.JSONDecodeError:
            self.logger.error(f"配置文件 {config_file} 格式错误")
            raise
            
    def _setup_stealth_mode(self, driver):
        """设置隐身模式，避免被检测为自动化"""
        try:
            # 隐藏webdriver特征
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # 修改user-agent中的HeadlessChrome标识
            driver.execute_script("""
                Object.defineProperty(navigator, 'userAgent', {
                    get: () => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.7258.67 Safari/537.36'
                });
            """)
            
            # 隐藏自动化相关属性
            driver.execute_script("""
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            """)
            
            driver.execute_script("""
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en', 'zh-CN', 'zh']
                });
            """)
            
            # 模拟真实的屏幕参数
            driver.execute_script("""
                Object.defineProperty(screen, 'width', {get: () => 1920});
                Object.defineProperty(screen, 'height', {get: () => 1080});
            """)
            
            self.logger.info("已设置反检测模式")
            
        except Exception as e:
            self.logger.warning(f"设置反检测模式失败: {e}")

    def init_driver(self) -> webdriver.Chrome:
        """初始化 Chrome 浏览器"""
        chrome_options = Options()
        
        # 基本选项
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # 证书相关
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument('--allow-running-insecure-content')
        
        # 反检测基本选项
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 使用最小化的chrome选项，避免被检测为自动化
        # 减少日志输出
        chrome_options.add_argument('--disable-logging')
        chrome_options.add_argument('--log-level=3')
        #chrome_options.add_argument('--incognito')  # 隐身模式
        # 不设置任何用户数据目录，使用Chrome默认行为
        self.logger.info("使用Chrome默认会话管理")
        
        if self.config.get('headless', False):
            chrome_options.add_argument('--headless')
            
        if 'user_agent' in self.config:
            chrome_options.add_argument(f'--user-agent={self.config["user_agent"]}')
            
        if 'proxy' in self.config and self.config['proxy']:
            chrome_options.add_argument(f'--proxy-server={self.config["proxy"]}')
        
        chrome_binary_path = self.config.get('chrome_binary_path')
        chromedriver_path = self.config.get('chromedriver_path')
        
        # 处理相对路径，确保正确解析
        if chrome_binary_path:
            if not os.path.isabs(chrome_binary_path):
                # 相对路径：基于脚本所在目录的上级目录
                script_dir = os.path.dirname(os.path.abspath(__file__))
                chrome_binary_path = os.path.join(script_dir, '..', chrome_binary_path)
            chrome_binary_path = os.path.normpath(chrome_binary_path)
            
        if chromedriver_path:
            if not os.path.isabs(chromedriver_path):
                script_dir = os.path.dirname(os.path.abspath(__file__))
                chromedriver_path = os.path.join(script_dir, '..', chromedriver_path)
            chromedriver_path = os.path.normpath(chromedriver_path)
        
        # 检查Chrome浏览器路径
        if not chrome_binary_path or not os.path.exists(chrome_binary_path):
            error_msg = "项目内Chrome浏览器未找到，请运行 'python install.py' 下载浏览器"
            self.logger.error(error_msg)
            if chrome_binary_path:
                self.logger.error(f"查找路径: {chrome_binary_path}")
            raise FileNotFoundError(error_msg)
        
        # 检查ChromeDriver路径
        if not chromedriver_path or not os.path.exists(chromedriver_path):
            error_msg = "项目内ChromeDriver未找到，请运行 'python install.py' 下载驱动"
            self.logger.error(error_msg)
            if chromedriver_path:
                self.logger.error(f"查找路径: {chromedriver_path}")
            raise FileNotFoundError(error_msg)
        
        # 设置Chrome浏览器路径
        self.logger.info(f"设置Chrome二进制路径: {chrome_binary_path}")
        chrome_options.binary_location = chrome_binary_path
        
        # 使用项目内ChromeDriver
        try:
            self.logger.info(f"使用项目内ChromeDriver: {chromedriver_path}")
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 执行反检测脚本
            self._setup_stealth_mode(driver)
            
            # 设置各种超时时间（优化等待时间）
            driver.implicitly_wait(3)  # 减少到3秒，提高响应速度
            driver.set_page_load_timeout(20)  # 减少页面加载超时
            driver.set_script_timeout(15)     # 减少脚本执行超时
            
            try:
                chrome_version = driver.capabilities['browserVersion']
                chromedriver_version = driver.capabilities['chrome']['chromedriverVersion'].split(' ')[0]
                self.logger.info(f"Chrome版本: {chrome_version}")
                self.logger.info(f"ChromeDriver版本: {chromedriver_version}")
            except:
                pass
            
            self.logger.info("✅ 项目内浏览器启动成功")
            return driver
            
        except Exception as e:
            self.logger.error(f"❌ 项目内ChromeDriver启动失败: {e}")
            self.logger.error("解决方案:")
            self.logger.error("1. 删除 bin/ 目录")
            self.logger.error("2. 重新运行 'python install.py' 下载最新的浏览器和驱动")
            raise e
            
    def login_to_mteam(self) -> bool:
        """
        登录到 M-Team 网站
        
        Returns:
            bool: 登录是否成功
        """
        try:
            self.driver = self.init_driver()
            self.logger.info("正在访问 M-Team 登录页面...")
            
            # 根据配置启用反检测功能
            import random
            anti_detection = self.config.get('anti_detection', {})
            
            if anti_detection.get('enable_human_simulation', True):
                initial_delay = random.uniform(3, 8)
                self.logger.info(f"模拟用户思考时间，等待 {initial_delay:.1f} 秒...")
                time.sleep(initial_delay)
            else:
                self.logger.info("跳过人类行为模拟延迟")
            
            # 访问登录页面，增加重试机制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.logger.info(f"尝试访问登录页面 (第{attempt + 1}次)...")
                    self.driver.get(self.login_url)
                    
                    # 根据配置决定是否使用随机延迟
                    if anti_detection.get('random_delays', True):
                        load_delay = random.uniform(4, 8)
                        self.logger.info(f"等待页面加载完成 ({load_delay:.1f}秒)...")
                        time.sleep(load_delay)
                    else:
                        self.logger.info("等待页面加载完成...")
                        time.sleep(3)  # 固定延迟
                    
                    # 检查页面是否正常加载
                    current_url = self.driver.current_url
                    if current_url and "kp.m-team.cc" in current_url:
                        self.logger.info(f"页面访问成功: {current_url}")
                        break
                    else:
                        raise Exception(f"页面重定向异常: {current_url}")
                        
                except Exception as e:
                    self.logger.warning(f"第{attempt + 1}次访问失败: {e}")
                    if attempt == max_retries - 1:
                        # 最后一次重试失败，尝试重新创建driver
                        self.logger.error("所有访问尝试失败，可能需要重新启动浏览器")
                        raise
                    
                    # 如果是连接丢失错误，尝试重新创建driver
                    if "session deleted" in str(e) or "disconnected" in str(e):
                        self.logger.warning("检测到浏览器连接丢失，重新启动浏览器...")
                        try:
                            self.driver.quit()
                        except:
                            pass
                        self.driver = self.init_driver()
                    
                    time.sleep(3)  # 等待3秒后重试
            
            # 检查页面标题和URL
            self.logger.info(f"页面标题: {self.driver.title}")
            self.logger.info(f"当前URL: {self.driver.current_url}")
            
            # 检查是否已经跳转到首页（说明已经登录）
            current_url = self.driver.current_url.lower()
            homepage_keywords = ['index', 'home', 'main', 'dashboard']
            found_keyword = next((kw for kw in homepage_keywords if kw in current_url), None)
            
            if found_keyword:
                self.logger.info(f"🔍 检测到页面包含首页关键词 '{found_keyword}': {self.driver.current_url}")
                self.logger.info("正在验证登录状态...")
                
                # 进一步确认是否真的已经登录
                if self.is_login_successful():
                    self.logger.info("✅ 验证通过：已检测到登录状态！")
                    self.logger.info("✅ 用户已登录，直接跳转到首页，跳过登录流程！")
                    self.logger.info("🎉 M-Team 登录成功（通过Cookie自动登录）！")
                    return True
                else:
                    self.logger.warning("⚠️ 页面跳转到首页但登录状态验证失败")
                    self.logger.info("继续尝试正常登录流程...")
            else:
                self.logger.info("页面未跳转到首页，继续正常登录流程")
            
            # 尝试多种方式查找用户名输入框
            username_input = None
            selectors = [
                (By.ID, "username")
            ]
            
            for by, selector in selectors:
                try:
                    self.logger.info(f"尝试查找元素: {by} = {selector}")
                    username_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    self.logger.info(f"成功找到用户名输入框: {by} = {selector}")
                    break
                except TimeoutException:
                    self.logger.info(f"未找到元素: {by} = {selector}")
                    continue
                    
            if not username_input:
                # 保存页面截图和源码用于调试
                self.driver.save_screenshot("debug_login_page.png")
                with open("debug_page_source.html", "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                self.logger.error("未找到用户名输入框，已保存截图和页面源码")
                raise Exception("未找到用户名输入框")
            
            # 输入用户名，根据配置决定是否模拟真实用户输入
            username_input.clear()
            username = self.config["mteam"]["username"]
            
            if anti_detection.get('typing_simulation', True):
                # 模拟逐字符输入
                for char in username:
                    username_input.send_keys(char)
                    time.sleep(random.uniform(0.05, 0.15))  # 随机打字速度
                
                # 用户思考密码的时间
                think_delay = random.uniform(1, 3)
                self.logger.info(f"用户名已输入，模拟思考时间 {think_delay:.1f}秒")
                time.sleep(think_delay)
            else:
                # 直接输入
                username_input.send_keys(username)
                self.logger.info("用户名已输入")
                time.sleep(0.5)  # 简短延迟
            
            # 输入密码
            password_selectors = [
                (By.ID, "password"),
            ]
            
            password_input = None
            for by, selector in password_selectors:
                try:
                    self.logger.info(f"尝试查找密码框: {by} = {selector}")
                    password_input = self.driver.find_element(by, selector)
                    self.logger.info(f"成功找到密码输入框: {by} = {selector}")
                    break
                except NoSuchElementException:
                    continue
                    
            if not password_input:
                raise Exception("未找到密码输入框")
                
            password_input.clear()
            password = self.config["mteam"]["password"]
            
            if anti_detection.get('typing_simulation', True):
                # 模拟逐字符输入密码
                for char in password:
                    password_input.send_keys(char)
                    time.sleep(random.uniform(0.03, 0.12))  # 密码输入稍快一些
                
                # 用户确认信息的时间
                confirm_delay = random.uniform(1.5, 4)
                self.logger.info(f"密码已输入，模拟确认时间 {confirm_delay:.1f}秒")
                time.sleep(confirm_delay)
            else:
                # 直接输入密码
                password_input.send_keys(password)
                self.logger.info("密码已输入")
                time.sleep(0.8)  # 简短延迟
            
            # 点击登录按钮
            login_selectors = [
                (By.XPATH, "//button[@type='submit']")
            ]
            
            login_button = None
            for by, selector in login_selectors:
                try:
                    self.logger.info(f"尝试查找登录按钮: {by} = {selector}")
                    login_button = self.driver.find_element(by, selector)
                    self.logger.info(f"成功找到登录按钮: {by} = {selector}")
                    break
                except NoSuchElementException:
                    continue
                    
            if not login_button:
                # 保存页面截图用于调试
                # self.driver.save_screenshot("debug_login_button.png")
                raise Exception("未找到登录按钮")
                
            # 添加鼠标移动模拟（可选）
            if anti_detection.get('enable_human_simulation', True):
                try:
                    from selenium.webdriver.common.action_chains import ActionChains
                    # 模拟鼠标移动到按钮
                    actions = ActionChains(self.driver)
                    actions.move_to_element(login_button)
                    actions.pause(random.uniform(0.2, 0.8))  # 悬停一下
                    actions.click()
                    actions.perform()
                    self.logger.info("模拟鼠标移动并点击登录按钮")
                except Exception as e:
                    # 如果模拟失败，使用普通点击
                    login_button.click()
                    self.logger.info("登录按钮已点击")
            else:
                login_button.click()
                self.logger.info("登录按钮已点击")
            
            # 根据配置决定等待时间
            if anti_detection.get('random_delays', True):
                wait_time = random.uniform(2, 5)
                self.logger.info(f"等待页面跳转... ({wait_time:.1f}秒)")
                time.sleep(wait_time)
            else:
                self.logger.info("等待页面跳转...")
                time.sleep(3)
            
            current_url = self.driver.current_url
            page_title = self.driver.title
            self.logger.info(f"登录后URL: {current_url}")
            self.logger.info(f"登录后页面标题: {page_title}")
            
            # 检查页面错误信息
            error_messages = self._check_page_errors()
            if error_messages:
                self.logger.error(f"页面显示错误信息: {error_messages}")
                
                # 检查是否是频率限制错误
                if any('頻繁' in msg or '频繁' in msg or 'frequent' in msg.lower() for msg in error_messages):
                    self.logger.warning("⚠️ 检测到频率限制错误，这通常是因为短时间内多次登录")
                    self.logger.info("💡 建议解决方案:")
                    self.logger.info("   1. 等待 10-30 分钟后再次尝试")
                    self.logger.info("   2. 使用不同的IP地址（如切换网络）")
                    self.logger.info("   3. 减少登录频率")
                    
                    # 添加更长的等待时间
                    wait_time = random.uniform(60, 120)  # 1-2分钟随机等待
                    self.logger.info(f"🕐 程序将等待 {wait_time:.0f} 秒后自动退出，建议稍后重试")
                    time.sleep(wait_time)
                
                return False
            
            # M-Team登录后通过div切换，优先检查邮箱验证
            if self._is_email_verification_page():
                self.logger.info("检测到邮箱验证页面，开始处理邮箱验证...")
                return self.handle_email_verification()
            
            # 检查是否直接登录成功
            if self.is_login_successful():
                self.logger.info("M-Team 登录成功！")
                return True
            
            # 最后判断登录失败
            if self._has_login_form() and "login" in current_url.lower():
                self.logger.error("M-Team 登录失败 - 仍在登录页面")
                return False
            
            self.logger.warning("页面状态异常，无法确定登录结果")
            return False
                
        except Exception as e:
            self.logger.error(f"登录过程中发生错误: {e}")
            return False
            
    def _check_page_errors(self) -> list:
        """检查页面错误信息"""
        error_messages = []
        error_selectors = [
            "//div[contains(@class, 'error') or contains(@class, 'alert') or contains(@class, 'danger')]",
            "//div[contains(text(), '错误') or contains(text(), '失败') or contains(text(), 'error') or contains(text(), 'failed')]"
        ]
        
        for selector in error_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                for element in elements:
                    text = element.text.strip()
                    if text:
                        error_messages.append(text)
            except:
                continue
        return error_messages
    
    def _has_login_form(self) -> bool:
        """检查是否存在登录表单"""
        try:
            self.driver.find_element(By.ID, "username")
            self.driver.find_element(By.ID, "password")
            return True
        except:
            return False

    def _is_email_verification_page(self) -> bool:
        """检测是否在邮箱验证页面"""
        try:
            # 检查URL和标题关键词
            current_url = self.driver.current_url.lower()
            page_title = self.driver.title.lower()
            
            url_keywords = ["verify", "2fa", "verification", "email"]
            title_keywords = ["验证", "verification", "2fa", "email"]
            
            if any(k in current_url for k in url_keywords) or any(k in page_title for k in title_keywords):
                return True
            
            # 检查邮箱验证元素
            wait = WebDriverWait(self.driver, 2)
            verification_selectors = [
                "//input[contains(@placeholder, '验证码') or contains(@placeholder, 'verification') or contains(@placeholder, 'code') or contains(@placeholder, '輸入')]",
                "//button[contains(text(), '获取验证码') or contains(text(), '獲取驗證碼') or contains(text(), '验证') or contains(text(), '驗證')]",
                "//div[contains(@class, 'verification') or contains(@class, 'email-verify')]"
            ]
            
            for selector in verification_selectors:
                try:
                    element = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                    if element.is_displayed():
                        self.logger.info(f"找到邮箱验证元素: {selector}")
                        return True
                except TimeoutException:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.error(f"检测邮箱验证页面时发生错误: {e}")
            return False

    def _find_element_by_selectors(self, selectors, description="元素"):
        """通过多个选择器查找元素"""
        for selector_info in selectors:
            try:
                if isinstance(selector_info, tuple):
                    by, selector = selector_info
                    return self.driver.find_element(by, selector)
                else:
                    return self.driver.find_element(By.XPATH, selector_info)
            except:
                continue
        return None

    def _click_element_safely(self, element):
        """安全点击元素"""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)
            element.click()
            return True
        except:
            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except:
                return False

    def handle_email_verification(self) -> bool:
        """处理M-Team的邮箱验证流程"""
        try:
            self.logger.info("开始M-Team邮箱验证流程...")
            
            # 填写邮箱地址
            email_input = self._find_element_by_selectors([(By.ID, "email")])
            if email_input:
                email_input.clear()
                email_input.send_keys(self.config["gmail"]["email"])
                self.logger.info(f"已输入邮箱地址: {self.config['gmail']['email']}")
            else:
                self.logger.warning("未找到邮箱输入框，可能已预填充")
            
            # 查找并点击发送验证码按钮
            send_button_selectors = [
                (By.XPATH, "//button[contains(@class, 'ant-btn-default') and contains(., '獲取驗證碼')]"),
                (By.XPATH, "//button[contains(text(), '獲取驗證碼') or contains(text(), '获取验证码')]"),
                (By.CSS_SELECTOR, "button.ant-btn-default")
            ]
            send_code_button = self._find_element_by_selectors(send_button_selectors, "发送验证码按钮")
            
            # 记录发送验证码的时间戳
            import time
            send_time = None
            
            if send_code_button:
                if send_code_button.get_attribute("disabled"):
                    time.sleep(2)  # 等待按钮可用
                if self._click_element_safely(send_code_button):
                    send_time = time.time()  # 记录发送时间
                    self.logger.info(f"成功点击发送验证码按钮，发送时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(send_time))}")
                    time.sleep(5)  # 等待邮件发送
                else:
                    self.logger.warning("点击发送验证码按钮失败")
                    
            # 查找验证码输入框
            code_selectors = ["//input[@placeholder='輸入6位數字驗證碼']"]
            code_input = self._find_element_by_selectors(code_selectors, "验证码输入框")
            if not code_input:
                self.logger.error("未找到验证码输入框")
                return False
            
            # 从Gmail获取验证码
            self.logger.info("正在从Gmail获取最新验证码...")
            self.gmail_client = GmailClient(self.config["gmail"])
            
            verification_code = None
            for attempt in range(5):
                self.logger.info(f"第{attempt+1}次尝试获取验证码...")
                # 传递发送时间，确保获取新邮件
                verification_code = self.gmail_client.get_verification_code(timeout=60, sent_after_time=send_time)
                if verification_code:
                    break
                if attempt < 4:  # 不是最后一次尝试
                    self.logger.info("等待5秒后重试...")
                    time.sleep(5)
            
            if not verification_code:
                self.logger.error("未能获取到验证码")
                return False
                
            self.logger.info(f"成功获取验证码: {verification_code}")
            
            # 填写验证码并提交
            code_input.clear()
            code_input.send_keys(verification_code)
            self.logger.info("已输入验证码")
            
            # 查找并点击登录按钮
            login_button = self._find_element_by_selectors(["//button[@type='submit']"], "登录按钮")
            if not login_button:
                self.logger.error("未找到登录按钮")
                return False
                
            if self._click_element_safely(login_button):
                self.logger.info("已点击登录按钮，等待验证结果...")
                time.sleep(5)
                
                if self.is_login_successful():
                    self.logger.info("邮箱验证成功，登录完成！")
                    return True
                else:
                    self.logger.error("邮箱验证失败或登录失败")
                    return False
            else:
                self.logger.error("点击登录按钮失败")
                return False
                
        except Exception as e:
            self.logger.error(f"邮箱验证过程中发生错误: {e}")
            return False
            
    def is_login_successful(self) -> bool:
        """检查是否登录成功"""
        try:
            current_url = self.driver.current_url.lower()
            page_title = self.driver.title
            
            # 检查URL跳转（M-Team首页特征）
            success_urls = ['index', 'home', 'main', 'dashboard', 'user', 'member', 'browse', 'torrents']
            if any(keyword in current_url for keyword in success_urls):
                self.logger.info(f"URL跳转成功: {current_url}")
                
                # 进一步验证：检查M-Team首页特有的标题特征
                if "m-team" in page_title.lower() and ("首頁" in page_title or "首页" in page_title or "home" in page_title.lower()):
                    self.logger.info(f"检测到M-Team首页标题: {page_title}")
                    return True
                
                # 如果不在登录页面且页面有足够内容，也认为登录成功
                if "login" not in current_url and len(self.driver.page_source) > 10000:
                    return True
            
            # 检查页面标题变化
            if "登录" not in page_title and "login" not in page_title.lower() and page_title.strip():
                # 进一步检查是否是M-Team的页面
                if "m-team" in page_title.lower() or "mteam" in page_title.lower():
                    return True
                
            # 检查登录成功元素（快速检查）
            try:
                wait = WebDriverWait(self.driver, 2)
                success_elements = [
                    "//a[contains(@href, 'logout') or contains(text(), '退出') or contains(text(), '登出')]",
                    "//div[contains(@class, 'user') and not(contains(@class, 'login'))]",
                    "//a[contains(@href, 'user') or contains(@href, 'profile')]"
                ]
                
                for selector in success_elements:
                    try:
                        element = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                        if element.is_displayed():
                            self.logger.info(f"检测到登录成功元素: {selector}")
                            return True
                    except TimeoutException:
                        continue
            except:
                pass
            
            # 最后的页面内容判断
            if "login" not in current_url and len(self.driver.page_source) > 5000:
                # 检查页面是否包含M-Team特有内容
                page_source = self.driver.page_source.lower()
                if any(keyword in page_source for keyword in ['torrent', 'download', 'upload', 'ratio', 'm-team']):
                    return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"检查登录状态时发生错误: {e}")
            return False
            
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.logger.info("浏览器已关闭")
            
    def run(self) -> bool:
        """运行完整的登录流程"""
        try:
            success = self.login_to_mteam()
            return success
        finally:
            self.close()


def main():
    try:
        mteam_login = MTeamLogin()
        success = mteam_login.run()
        
        if success:
            print("✅ M-Team 自动登录成功！")
        else:
            print("❌ M-Team 自动登录失败！")
            
    except Exception as e:
        logging.error(f"程序运行错误: {e}")
        print(f"❌ 程序运行错误: {e}")


if __name__ == "__main__":
    main() 