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
        
        # 减少日志输出
        chrome_options.add_argument('--disable-logging')
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_argument('--disable-dev-tools')
        chrome_options.add_argument('--no-first-run')
        chrome_options.add_argument('--disable-extensions')
        
        import tempfile
        user_data_dir = tempfile.mkdtemp()
        chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
        
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
        self.logger.info(f"✅ 设置Chrome二进制路径: {chrome_binary_path}")
        self.logger.info(f"✅ 文件是否存在: {os.path.exists(chrome_binary_path)}")
        chrome_options.binary_location = chrome_binary_path
        
        # 验证Chrome选项中的binary_location设置
        self.logger.info(f"✅ Chrome选项中的binary_location: {getattr(chrome_options, 'binary_location', 'None')}")
        
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
            
            # 访问登录页面，增加重试机制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.logger.info(f"尝试访问登录页面 (第{attempt + 1}次)...")
                    self.driver.get(self.login_url)
                    
                    # 等待页面加载完成
                    time.sleep(5)
                    
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
            
            # 输入用户名
            username_input.clear()
            username_input.send_keys(self.config["mteam"]["username"])
            self.logger.info("用户名已输入")
            
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
            password_input.send_keys(self.config["mteam"]["password"])
            self.logger.info("密码已输入")
            
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
                
            login_button.click()
            self.logger.info("登录按钮已点击")
            
            # 添加更长的等待时间，防止会话被意外关闭
            self.logger.info("等待页面跳转...")
            time.sleep(3)
            
            # 检查浏览器会话是否还有效
            try:
                _ = self.driver.current_url
                self.logger.info("浏览器会话正常")
            except Exception as e:
                self.logger.error(f"浏览器会话已断开: {e}")
                return False
            
            # 检查页面跳转和状态
            current_url = self.driver.current_url
            page_title = self.driver.title
            self.logger.info(f"登录后URL: {current_url}")
            self.logger.info(f"登录后页面标题: {page_title}")
            
            # 检查是否有错误信息（增强版，更多错误检测）
            error_messages = []
            error_selectors = [
                "//div[contains(@class, 'error')]",
                "//div[contains(@class, 'alert')]", 
                "//div[contains(@class, 'danger')]",
                "//span[contains(@class, 'error')]",
                "//div[contains(text(), '错误')]",
                "//div[contains(text(), '失败')]",
                "//div[contains(text(), 'error')]",
                "//div[contains(text(), 'failed')]",
                "//div[contains(text(), '用户名')]",
                "//div[contains(text(), '密码')]",
                "//div[contains(text(), 'username')]",
                "//div[contains(text(), 'password')]",
                "//div[contains(text(), 'invalid')]",
                "//div[contains(text(), 'incorrect')]"
            ]
            
            for selector in error_selectors:
                try:
                    error_elements = self.driver.find_elements(By.XPATH, selector)
                    for element in error_elements:
                        if element.text.strip():
                            error_messages.append(element.text.strip())
                except:
                    continue
            
            # 检查登录表单是否还存在（表明登录失败）
            login_form_exists = False
            try:
                self.driver.find_element(By.ID, "username")
                self.driver.find_element(By.ID, "password")
                login_form_exists = True
                self.logger.warning("🔍 检测到登录表单仍然存在，可能登录失败")
            except:
                pass
            
            if error_messages:
                self.logger.error(f"🚨 页面显示错误信息: {error_messages}")
                return False
            
            if login_form_exists and "login" in current_url.lower():
                self.logger.warning("🔍 仍在登录页面且登录表单存在，检查用户名密码是否正确")
                # 这里不直接返回False，而是继续检查是否需要邮箱验证
            
            # 🔑 关键修复：M-Team登录后不跳转页面，而是通过JavaScript切换div
            # 因此需要先检查是否进入邮箱验证流程，而不是先判断URL跳转
            
            # 1. 优先检查是否跳转到邮箱验证页面 (M-Team的两步验证流程)
            if self._is_email_verification_page():
                self.logger.info("✅ 登录成功！检测到邮箱验证页面，开始处理邮箱验证...")
                return self.handle_email_verification()
            
            # 2. 如果没有邮箱验证，检查是否直接登录成功（URL跳转）
            if self.is_login_successful():
                self.logger.info("✅ M-Team 登录成功！")
                return True
            
            # 3. 最后才判断登录失败
            # 注意：即使仍在login页面，也可能是因为需要邮箱验证但检测失败
            if login_form_exists and "login" in current_url.lower():
                self.logger.error("❌ M-Team 登录失败 - 仍在登录页面且存在登录表单")
                if error_messages:
                    self.logger.error(f"🚨 错误信息: {', '.join(error_messages)}")
                else:
                    self.logger.error("💡 可能原因：用户名或密码错误")
                return False
            else:
                # 特殊情况：在login页面但没有表单，可能是页面加载问题
                self.logger.warning("⚠️ 页面状态异常，无法确定登录结果")
                return False
                
        except Exception as e:
            self.logger.error(f"登录过程中发生错误: {e}")
            return False
            
    def _is_email_verification_page(self) -> bool:
        """
        检测是否在邮箱验证页面（优化版，减少等待时间）
        
        Returns:
            bool: 是否为邮箱验证页面
        """
        try:
            current_url = self.driver.current_url
            page_title = self.driver.title
            
            # 优先检查URL和标题（最快速的检查）
            url_indicators = ["verify", "2fa", "verification", "email"]
            if any(keyword in current_url.lower() for keyword in url_indicators):
                self.logger.info(f"✅ URL中检测到邮箱验证关键词: {current_url}")
                return True
            
            title_indicators = ["验证", "verification", "2fa", "email"]
            if any(keyword in page_title.lower() for keyword in title_indicators):
                self.logger.info(f"✅ 标题中检测到邮箱验证关键词: {page_title}")
                return True
            
            # 使用显式等待快速检查关键元素存在（专门针对M-Team的div切换）
            wait = WebDriverWait(self.driver, 2)  # 稍微增加到2秒，给div切换时间
            
            # M-Team特有的邮箱验证元素
            verification_elements = [
                "//input[contains(@placeholder, '验证码')]",
                "//input[contains(@placeholder, 'verification')]", 
                "//input[contains(@placeholder, 'code')]",
                "//input[contains(@placeholder, '輸入')]",  # 繁体中文
                "//button[contains(text(), '获取验证码')]",
                "//button[contains(text(), '獲取驗證碼')]",  # 繁体中文
                "//button[contains(text(), '验证')]",
                "//button[contains(text(), '驗證')]",  # 繁体中文
                "//div[contains(@class, 'verification')]",
                "//div[contains(@class, 'email-verify')]"
            ]
            
            for xpath in verification_elements:
                try:
                    element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                    self.logger.info(f"✅ 找到邮箱验证元素: {xpath}")
                    # 检查元素是否可见（因为可能有隐藏的元素）
                    if element.is_displayed():
                        self.logger.info("✅ 邮箱验证元素可见，确认进入验证流程")
                        return True
                except TimeoutException:
                    continue
            
            self.logger.info("❌ 邮箱验证页面检测结果: False")
            return False
            
        except Exception as e:
            self.logger.error(f"检测邮箱验证页面时发生错误: {e}")
            return False

    def handle_email_verification(self) -> bool:
        """
        处理M-Team的邮箱验证流程
        
        Returns:
            bool: 验证是否成功
        """
        try:
            self.logger.info("开始M-Team邮箱验证流程...")
            
            # Step 1: 查找并填写邮箱输入框
            email_input = None
            email_selectors = [
                (By.ID, "email")
            ]

            for by, selector in email_selectors:
                try:
                    self.logger.info(f"尝试查找邮箱输入框: {by} = {selector}")
                    email_input = self.driver.find_element(by, selector)
                    self.logger.info(f"成功找到邮箱输入框: {by} = {selector}")
                    break
                except TimeoutException:
                    continue
                    
            if email_input:
                email_input.clear()
                email_input.send_keys(self.config["gmail"]["email"])
                self.logger.info(f"已输入邮箱地址: {self.config['gmail']['email']}")
            else:
                self.logger.warning("未找到邮箱输入框，可能已预填充")
            
            # Step 2: 查找并点击获取验证码按钮
            send_code_button = None
            send_button_selectors = [
                (By.XPATH, "//button[contains(@class, 'ant-btn-default') and contains(., '獲取驗證碼')]"),
                (By.XPATH, "//button[contains(@class, 'ant-btn-default') and contains(., '获取验证码')]"),
                (By.XPATH, "//button[contains(@class, 'ant-btn-default')]"),
                (By.XPATH, "//button[contains(text(), '獲取驗證碼') or contains(text(), '获取验证码')]"),
                (By.XPATH, "//button[@type='button' and contains(@class, 'ant-btn')]//span[contains(text(), '獲取驗證碼')]/.."),
                (By.CSS_SELECTOR, "button.ant-btn-default"),
                (By.CSS_SELECTOR, "button.ant-btn.ant-btn-default")
            ]
            for by, selector in send_button_selectors:
                try:
                    self.logger.info(f"尝试查找发送验证码按钮: {selector}")
                    # 先尝试找到按钮元素（不要求可点击）
                    send_code_button = self.driver.find_element(by, selector)
                    # 检查按钮状态
                    is_disabled = send_code_button.get_attribute("disabled")
                    button_text = send_code_button.text or ""
                    self.logger.info(f"找到按钮: 文本='{button_text}', 禁用状态={is_disabled}")
                    
                    # 如果按钮被禁用，等待一段时间让它变为可用
                    if is_disabled:
                        self.logger.info("按钮当前被禁用，等待变为可用...")
                        for wait_count in range(10):  # 等待最多10秒
                            time.sleep(1)
                            is_disabled = send_code_button.get_attribute("disabled")
                            if not is_disabled:
                                self.logger.info("按钮现在可用了！")
                                break
                        else:
                            self.logger.info("按钮仍然被禁用，但将尝试强制点击")
                    
                    self.logger.info(f"成功找到发送验证码按钮: {selector}")
                    break
                    
                except TimeoutException:
                    self.logger.info(f"未找到按钮: {selector}")
                    continue
                    
            # Step 3: 先查找验证码输入框
            code_input = None
            code_selectors = [
                "//input[@placeholder='輸入6位數字驗證碼']",
            ]
            
            for selector in code_selectors:
                try:
                    self.logger.info(f"尝试查找验证码输入框: {selector}")
                    code_input = self.driver.find_element(By.XPATH, selector)
                    self.logger.info(f"成功找到验证码输入框: {selector}")
                    break
                except TimeoutException:
                    continue
                    
            if not code_input:
                self.logger.error("未找到验证码输入框")
                
                # 尝试查找所有输入框进行调试
                all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
                self.logger.info(f"页面中共有 {len(all_inputs)} 个输入框:")
                for i, inp in enumerate(all_inputs):
                    try:
                        inp_type = inp.get_attribute("type") or "未知"
                        inp_name = inp.get_attribute("name") or "无"
                        inp_id = inp.get_attribute("id") or "无"
                        inp_placeholder = inp.get_attribute("placeholder") or "无"
                        inp_class = inp.get_attribute("class") or "无"
                        self.logger.info(f"  输入框{i+1}: type={inp_type}, name={inp_name}, id={inp_id}, placeholder={inp_placeholder}, class={inp_class}")
                    except:
                        continue
                
                return False
            
            # Step 4: 点击发送验证码按钮（如果有）
            if send_code_button:
                self.logger.info("找到发送验证码按钮，准备点击...")
                
                try:
                    # 确保按钮可见
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", send_code_button)
                    time.sleep(1)
                    
                    # 检查按钮是否仍然被禁用
                    is_disabled = send_code_button.get_attribute("disabled")
                    if is_disabled:
                        self.logger.info("按钮被禁用，尝试使用JavaScript强制点击...")
                        self.driver.execute_script("arguments[0].click();", send_code_button)
                    else:
                        self.logger.info("按钮可用，使用普通点击...")
                        send_code_button.click()
                    
                    self.logger.info("成功点击发送验证码按钮！")
                    
                    # 等待验证码发送到邮箱（减少等待时间提高效率）
                    self.logger.info("等待验证码邮件发送...")
                    time.sleep(5)  # 等待5秒确保邮件发送完成
                    
                except Exception as click_error:
                    self.logger.error(f"点击发送验证码按钮失败: {click_error}")
                    # 继续执行，可能验证码已经自动发送
                
            else:
                self.logger.warning("使用选择器未找到按钮，尝试直接查找...")
                
                # 直接查找包含"獲取驗證碼"文本的按钮
                try:
                    all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    for btn in all_buttons:
                        btn_text = btn.text.strip()
                        if "獲取驗證碼" in btn_text or "获取验证码" in btn_text or "獲取" in btn_text:
                            self.logger.info(f"直接找到按钮: {btn_text}")
                            send_code_button = btn
                            break
                except Exception as e:
                    self.logger.error(f"直接查找按钮时出错: {e}")
                
                # 如果找到了按钮，重新进入成功分支
                if send_code_button:
                    self.logger.info("直接查找成功！现在点击按钮...")
                    try:
                        # 确保按钮可见并可点击
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", send_code_button)
                        time.sleep(1)
                        
                        # 尝试普通点击
                        try:
                            send_code_button.click()
                        except:
                            # 如果普通点击失败，使用JavaScript点击
                            self.logger.info("普通点击失败，尝试JavaScript点击...")
                            self.driver.execute_script("arguments[0].click();", send_code_button)
                        
                        self.logger.info("成功点击发送验证码按钮！")
                        time.sleep(5)  # 等待验证码发送到邮箱
                        
                    except Exception as e:
                        self.logger.error(f"点击发送验证码按钮失败: {e}")
                else:
                    self.logger.error("未找到发送验证码按钮！显示调试信息")
                
                # 无论如何都显示调试信息
                try:
                    all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    all_inputs = self.driver.find_elements(By.XPATH, "//input[@type='button' or @type='submit']")
                    
                    self.logger.info(f"页面中共有 {len(all_buttons)} 个button元素:")
                    
                    for i, btn in enumerate(all_buttons):
                        try:
                            btn_text = btn.text or "无文本"
                            btn_type = btn.get_attribute("type") or "无"
                            btn_class = btn.get_attribute("class") or "无"
                            btn_id = btn.get_attribute("id") or "无"
                            self.logger.info(f"  按钮{i+1}: text='{btn_text}', type={btn_type}, class={btn_class}, id={btn_id}")
                        except Exception as btn_error:
                            self.logger.warning(f"获取按钮{i+1}信息时出错: {btn_error}")
                    
                    self.logger.info(f"页面中共有 {len(all_inputs)} 个input按钮:")
                    for i, btn in enumerate(all_inputs):
                        try:
                            btn_value = btn.get_attribute("value") or "无文本"
                            btn_type = btn.get_attribute("type") or "无"
                            btn_class = btn.get_attribute("class") or "无"
                            self.logger.info(f"  输入按钮{i+1}: value='{btn_value}', type={btn_type}, class={btn_class}")
                        except Exception as btn_error:
                            self.logger.warning(f"获取输入按钮{i+1}信息时出错: {btn_error}")
                            
                except Exception as e:
                    self.logger.error(f"获取页面元素时出错: {e}")
                    return False
            
            # Step 5: 从Gmail获取最新验证码
            self.logger.info("正在从Gmail获取最新验证码...")
            self.gmail_client = GmailClient(self.config["gmail"])
            
            # 尝试获取验证码，最多重试5次
            verification_code = None
            for attempt in range(5):
                self.logger.info(f"第{attempt+1}次尝试获取验证码...")
                verification_code = self.gmail_client.get_verification_code(timeout=60)
                if verification_code:
                    break
                if attempt < 1:  # 不是最后一次尝试
                    self.logger.info("等待5秒后重试...")
                    time.sleep(5)
            
            if not verification_code:
                self.logger.error("未能获取到验证码")
                return False
                
            self.logger.info(f"成功获取验证码: {verification_code}")
            
            # Step 6: 立即填写验证码（code_input已在Step 3中找到）
            
            code_input.clear()
            code_input.send_keys(verification_code)
            self.logger.info("已输入验证码")
            
            # Step 7: 查找并点击登录按钮
            login_button = None
            login_selectors = [
                "//button[@type='submit']",
            ]
            
            for selector in login_selectors:
                try:
                    self.logger.info(f"尝试查找登录按钮: {selector}")
                    login_button = self.driver.find_element(By.XPATH, selector)
                    self.logger.info(f"成功找到登录按钮: {selector}")
                    break
                except NoSuchElementException:
                    continue
                    
            if not login_button:
                self.logger.error("未找到登录按钮")
                return False
                
            login_button.click()
            self.logger.info("已点击登录按钮，等待验证结果...")
            
            time.sleep(5)
            
            # Step 8: 检查验证是否成功
            if self.is_login_successful():
                self.logger.info("邮箱验证成功，登录完成！")
                return True
            else:
                self.logger.error("邮箱验证失败或登录失败")

                return False
                
        except Exception as e:
            self.logger.error(f"邮箱验证过程中发生错误: {e}")
            return False
            
    def is_login_successful(self) -> bool:
        """
        检查是否登录成功（优化版，减少等待时间）
        
        Returns:
            bool: 是否登录成功
        """
        try:
            current_url = self.driver.current_url
            page_title = self.driver.title
            
            self.logger.info(f"检查登录状态 - URL: {current_url}")
            self.logger.info(f"检查登录状态 - 标题: {page_title}")
            
            # 1. 检查URL：注意M-Team登录后可能仍在login页面（div切换）
            # 所以不能简单地因为包含"login"就判断失败
            if "login" in current_url.lower():
                # 需要进一步检查页面内容来确定是否真的失败
                self.logger.info("📍 仍在login页面，需要进一步检查页面内容...")
            
            # 2. 快速检查：URL跳转成功是最可靠的标志
            success_urls = ['index', 'home', 'main', 'dashboard', 'user', 'member', 'browse', 'torrents']
            if any(keyword in current_url.lower() for keyword in success_urls):
                self.logger.info(f"✅ URL跳转成功: {current_url}")
                return True
            
            # 3. 快速检查：页面标题改变通常表示登录成功
            if "登录" not in page_title and "login" not in page_title.lower() and page_title.strip():
                self.logger.info(f"✅ 页面标题已改变，登录成功: {page_title}")
                return True
                
            # 4. 简化的元素检查（只检查最常见的几个，使用显式等待）
            wait = WebDriverWait(self.driver, 1)  # 只等待1秒
            
            # 优先检查最可能存在的元素
            quick_check_elements = [
                "//a[contains(@href, 'logout')]",      # 退出链接最常见
                "//a[contains(text(), '退出')]",        # 中文退出链接
                "//div[contains(@class, 'user')]"      # 用户相关div
            ]
            
            for xpath in quick_check_elements:
                try:
                    element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                    self.logger.info(f"✅ 找到登录标志元素: {xpath}")
                    return True
                except TimeoutException:
                    continue
            
            # 5. 最后检查：页面内容判断（不在登录页面且有足够内容）
            if "login" not in current_url.lower() and len(self.driver.page_source) > 5000:
                self.logger.info("✅ 页面内容丰富且不在登录页面，判断为登录成功")
                return True
                
            self.logger.info("❌ 所有快速检查都未通过，登录可能失败")
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
        """
        运行完整的登录流程
        
        Returns:
            bool: 登录是否成功
        """
        try:
            success = self.login_to_mteam()
            return success
        finally:
            self.close()


def main():
    """主函数"""
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