#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gmail 客户端，用于自动获取验证码（仅使用IMAP方法）
"""

import time
import re
import logging
from typing import Optional
from datetime import datetime, timedelta
import imaplib
import email
from email.header import decode_header
import ssl


class GmailClient:
    def __init__(self, config: dict):
        """
        初始化Gmail客户端
        
        Args:
            config: Gmail配置，包含邮箱账号和密码
        """
        self.config = config
        # 使用根logger确保日志正常输出
        self.logger = logging.getLogger()
        
    def get_verification_code_via_imap(self, timeout: int = 300, sent_after_time: float = None) -> Optional[str]:
        """
        通过 IMAP 协议获取验证码
        
        Args:
            timeout: 超时时间（秒）
            sent_after_time: 只查找在此时间戳之后收到的邮件（Unix时间戳）
            
        Returns:
            验证码字符串，如果未找到则返回None
        """
        try:
            # 连接到Gmail IMAP服务器（增强稳定性）
            self.logger.info(f"正在连接Gmail IMAP服务器 (邮箱: {self.config['email'][:3]}***{self.config['email'][-10:]})")
            
            # 创建更稳定的SSL上下文
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_REQUIRED
            
            # 添加重试机制用于连接
            max_retries = 3
            mail = None
            
            for retry in range(max_retries):
                try:
                    self.logger.info(f"尝试连接 (第{retry + 1}/{max_retries}次)...")
                    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993, ssl_context=context)
                    break
                except (ssl.SSLError, OSError) as conn_error:
                    self.logger.warning(f"连接尝试{retry + 1}失败: {conn_error}")
                    if retry < max_retries - 1:
                        time.sleep(2)  # 等待2秒后重试
                        continue
                    else:
                        raise conn_error
            
            if not mail:
                raise Exception("无法建立IMAP连接")
            
            self.logger.info("✅ Gmail IMAP服务器连接成功")
            
            # 登录（带重试机制）
            self.logger.info("正在进行IMAP认证...")
            max_auth_retries = 2
            
            for auth_retry in range(max_auth_retries):
                try:
                    mail.login(self.config["email"], self.config["password"])
                    self.logger.info("✅ Gmail IMAP认证成功")
                    break
                except imaplib.IMAP4.error as login_error:
                    error_msg = str(login_error)
                    
                    if auth_retry < max_auth_retries - 1 and "SSL" in error_msg:
                        self.logger.warning(f"认证尝试{auth_retry + 1}失败，可能是网络问题，2秒后重试...")
                        time.sleep(2)
                        continue
                    
                    # 最后一次失败，提供详细诊断
                    self.logger.error(f"❌ Gmail IMAP认证失败: {error_msg}")
                    
                    if "AUTHENTICATIONFAILED" in error_msg:
                        self.logger.error("🔍 认证失败原因分析:")
                        self.logger.error("   1. 应用专用密码可能已过期，请重新生成")
                        self.logger.error("   2. 访问: https://myaccount.google.com/apppasswords")
                        self.logger.error("   3. 删除旧密码，创建新的'M-Team自动登录'密码")
                        self.logger.error("   4. 确保两步验证已启用")
                    elif "Invalid credentials" in error_msg:
                        self.logger.error("🔍 无效凭据 - 请检查:")
                        self.logger.error("   • 应用专用密码格式是否正确")
                        self.logger.error("   • 是否复制了完整的16位密码")
                    
                    raise login_error
            
            # 选择收件箱
            mail.select("inbox")
            
            # 设置搜索时间范围
            if sent_after_time:
                # 使用指定的发送时间，稍微往前推30秒以确保不遗漏
                search_datetime = datetime.fromtimestamp(sent_after_time - 30)
                search_time = search_datetime.strftime("%d-%b-%Y")
                self.logger.info(f"搜索 {search_datetime.strftime('%Y-%m-%d %H:%M:%S')} 之后的邮件")
            else:
                # 默认搜索最近2分钟
                search_time = (datetime.now() - timedelta(minutes=2)).strftime("%d-%b-%Y")
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    # 广泛搜索最新邮件（先找到M-Team真实的发送地址）
                    search_criteria = [
                        # 最新的未读邮件（包含验证码关键词）
                        f'(SINCE "{search_time}") (SUBJECT "验证" OR SUBJECT "verification" OR SUBJECT "code" OR SUBJECT "驗證") UNSEEN',
                        f'(SINCE "{search_time}") (BODY "验证码" OR BODY "verification code" OR BODY "驗證碼") UNSEEN',
                        
                        # 所有最新邮件（包含M-Team相关）
                        f'(SINCE "{search_time}") (FROM "m-team" OR SUBJECT "m-team" OR BODY "m-team") UNSEEN',
                        f'(SINCE "{search_time}") (FROM "mteam" OR SUBJECT "mteam" OR BODY "mteam") UNSEEN',
                        
                        # 常见的PT站发送地址
                        f'(SINCE "{search_time}") (FROM "web@m-team.cc" OR FROM "noreply@m-team.cc" OR FROM "admin@m-team.cc" OR FROM "system@m-team.cc") UNSEEN',
                        f'(SINCE "{search_time}") (FROM "no-reply@m-team.cc" OR FROM "service@m-team.cc") UNSEEN',
                        
                        # 放宽时间限制的搜索
                        f'(SUBJECT "验证" OR SUBJECT "verification" OR SUBJECT "code" OR SUBJECT "驗證") UNSEEN',
                        f'(BODY "验证码" OR BODY "verification code" OR BODY "驗證碼") UNSEEN',
                        
                        # 最后尝试：所有未读邮件
                        'UNSEEN'
                    ]
                    
                    for criteria in search_criteria:
                        try:
                            status, messages = mail.search(None, criteria)
                            if status == 'OK' and messages[0]:
                                message_ids = messages[0].split()
                                if message_ids:
                                    # 获取最新的邮件（邮件ID通常是按时间排序的，最后一个是最新的）
                                    latest_id = message_ids[-1]
                                    self.logger.info(f"找到邮件ID: {latest_id}")
                                    verification_code = self._extract_code_from_email(mail, latest_id, sent_after_time)
                                    if verification_code:
                                        self.logger.info(f"成功从最新邮件中提取验证码: {verification_code}")
                                        mail.close()
                                        mail.logout()
                                        return verification_code
                        except Exception as e:
                            self.logger.debug(f"搜索条件 {criteria} 失败: {e}")
                            continue
                    
                    # 等待5秒后重试
                    time.sleep(5)
                    
                except Exception as e:
                    self.logger.error(f"IMAP搜索过程中发生错误: {e}")
                    time.sleep(5)
                    
            mail.close()
            mail.logout()
            self.logger.error("在指定时间内未找到验证码邮件")
            return None
            
        except Exception as e:
            self.logger.error(f"IMAP连接失败: {e}")
            
            # 提供更详细的错误诊断
            error_msg = str(e)
            if "SSL" in error_msg or "EOF" in error_msg:
                self.logger.error("🌐 SSL连接问题 - 可能的解决方案:")
                self.logger.error("   1. 检查网络连接是否稳定")
                self.logger.error("   2. 尝试更换网络环境")
                self.logger.error("   3. 检查防火墙是否阻止IMAP连接")
                self.logger.error("   4. 稍后重试，可能是Gmail服务器暂时问题")
            elif "AUTHENTICATIONFAILED" in error_msg or "Invalid credentials" in error_msg:
                self.logger.error("🔐 Gmail认证失败 - 解决方案:")
                self.logger.error("   1. 重新生成Gmail应用专用密码")
                self.logger.error("   2. 访问: https://myaccount.google.com/apppasswords")
                self.logger.error("   3. 删除旧密码，创建新的'M-Team自动登录'密码")
                self.logger.error("   4. 确保密码复制时没有多余空格")
                self.logger.error("   5. 确认两步验证已启用")
            elif "timeout" in error_msg.lower():
                self.logger.error("⏰ 连接超时 - 可能的解决方案:")
                self.logger.error("   1. 检查网络延迟")
                self.logger.error("   2. 尝试使用VPN")
                self.logger.error("   3. 稍后重试")
            
            return None
            
    def _extract_code_from_email(self, mail, message_id: bytes, sent_after_time: float = None) -> Optional[str]:
        """
        从邮件中提取验证码
        
        Args:
            mail: IMAP连接对象
            message_id: 邮件ID
            sent_after_time: 只处理在此时间戳之后收到的邮件（Unix时间戳）
            
        Returns:
            验证码字符串
        """
        try:
            # 获取邮件内容
            status, msg_data = mail.fetch(message_id, '(RFC822)')
            
            if status != 'OK':
                return None
                
            # 解析邮件
            email_body = msg_data[0][1]
            message = email.message_from_bytes(email_body)
            
            # 记录邮件发送方和主题，方便调试
            sender = message.get('From', '未知发送方')
            subject = message.get('Subject', '无主题')
            
            # 检查邮件时间是否符合要求
            if sent_after_time:
                date_header = message.get('Date')
                if date_header:
                    try:
                        from email.utils import parsedate_to_datetime
                        email_time = parsedate_to_datetime(date_header)
                        email_timestamp = email_time.timestamp()
                        
                        if email_timestamp < sent_after_time:
                            self.logger.info(f"跳过旧邮件 - 发送方: {sender}, 时间: {email_time.strftime('%Y-%m-%d %H:%M:%S')}")
                            return None
                        else:
                            self.logger.info(f"处理新邮件 - 发送方: {sender}, 时间: {email_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    except Exception as time_error:
                        self.logger.warning(f"解析邮件时间失败，继续处理: {time_error}")
            
            self.logger.info(f"正在处理邮件 - 发送方: {sender}, 主题: {subject}")
            
            # 获取邮件正文
            body = self._get_email_body(message)
            
            if not body:
                return None
            
            # 记录邮件内容以便调试（截取前200字符）
            self.logger.debug(f"邮件正文预览: {body[:200]}...")
                
            # 优化的验证码匹配模式（优先匹配数字验证码）
            patterns = [
                r'(\d{6})',  # 6位纯数字验证码（M-Team最常用）
                r'(\d{4,8})',  # 4-8位纯数字验证码
                r'验证码[：:\s]*(\d{4,8})',  # 中文+数字
                r'verification code[：:\s]*(\d{4,8})',  # 英文+数字  
                r'code[：:\s]*(\d{4,8})',  # code+数字
                r'验证码[：:\s]*([A-Za-z0-9]{4,8})',  # 中文+字母数字
                r'verification code[：:\s]*([A-Za-z0-9]{4,8})',  # 英文+字母数字
                r'(?:^|\s)([A-Z0-9]{6})(?:\s|$)',  # 独立的6位大写字母数字组合
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, body, re.IGNORECASE | re.MULTILINE)
                for code in matches:
                    code = code.strip()
                    # 验证码长度和格式检查
                    if len(code) >= 4 and not code.lower() in ['image', 'style', 'class', 'width', 'height', 'color']:
                        # 进一步验证：如果是6位数字，优先返回
                        if len(code) == 6 and code.isdigit():
                            self.logger.info(f"从邮件中提取到6位数字验证码: {code}")
                            return code
                        # 其他格式的验证码
                        elif len(code) >= 4:
                            self.logger.info(f"从邮件中提取到验证码: {code}")
                            return code
                        
            self.logger.warning("未能从邮件中提取验证码")
            return None
            
        except Exception as e:
            self.logger.error(f"解析邮件时发生错误: {e}")
            return None
            
    def _get_email_body(self, message) -> str:
        """
        获取邮件正文内容
        
        Args:
            message: 邮件消息对象
            
        Returns:
            邮件正文字符串
        """
        body = ""
        
        try:
            if message.is_multipart():
                for part in message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    # 跳过附件
                    if "attachment" in content_disposition:
                        continue
                        
                    # 获取文本内容
                    if content_type == "text/plain" or content_type == "text/html":
                        charset = part.get_content_charset() or 'utf-8'
                        part_body = part.get_payload(decode=True)
                        if part_body:
                            body += part_body.decode(charset, errors='ignore')
            else:
                charset = message.get_content_charset() or 'utf-8'
                body = message.get_payload(decode=True)
                if body:
                    body = body.decode(charset, errors='ignore')
                    
        except Exception as e:
            self.logger.error(f"解析邮件正文时发生错误: {e}")
            
        return body
        
    def get_verification_code(self, timeout: int = 300, sent_after_time: float = None) -> Optional[str]:
        """
        获取验证码的主要入口方法（仅使用IMAP）
        
        Args:
            timeout: 超时时间（秒）
            sent_after_time: 只查找在此时间戳之后收到的邮件（Unix时间戳）
            
        Returns:
            验证码字符串，如果未找到则返回None
        """
        self.logger.info("开始使用 IMAP 方法获取验证码...")
        if sent_after_time:
            import time
            self.logger.info(f"只查找在 {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(sent_after_time))} 之后收到的邮件")
        return self.get_verification_code_via_imap(timeout, sent_after_time)