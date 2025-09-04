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
        self.logger = logging.getLogger(__name__)
        
    def get_verification_code_via_imap(self, timeout: int = 300) -> Optional[str]:
        """
        通过 IMAP 协议获取验证码
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            验证码字符串，如果未找到则返回None
        """
        try:
            # 连接到Gmail IMAP服务器
            context = ssl.create_default_context()
            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993, ssl_context=context)
            
            # 登录
            mail.login(self.config["email"], self.config["password"])
            self.logger.info("成功连接到Gmail IMAP服务器")
            
            # 选择收件箱
            mail.select("inbox")
            
            # 设置搜索时间范围（最近2分钟，确保是最新的）
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
                                    verification_code = self._extract_code_from_email(mail, latest_id)
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
            return None
            
    def _extract_code_from_email(self, mail, message_id: bytes) -> Optional[str]:
        """
        从邮件中提取验证码
        
        Args:
            mail: IMAP连接对象
            message_id: 邮件ID
            
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
            self.logger.info(f"正在处理邮件 - 发送方: {sender}, 主题: {subject}")
            
            # 获取邮件正文
            body = self._get_email_body(message)
            
            if not body:
                return None
                
            # 常见的验证码模式
            patterns = [
                r'验证码[：:\s]*([A-Za-z0-9]{4,8})',
                r'verification code[：:\s]*([A-Za-z0-9]{4,8})',
                r'code[：:\s]*([A-Za-z0-9]{4,8})',
                r'([A-Za-z0-9]{4,8})',  # 通用数字字母组合
                r'(\d{4,8})',  # 纯数字验证码
            ]
            
            for pattern in patterns:
                match = re.search(pattern, body, re.IGNORECASE)
                if match:
                    code = match.group(1).strip()
                    if len(code) >= 4:  # 验证码至少4位
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
        
    def get_verification_code(self, timeout: int = 300) -> Optional[str]:
        """
        获取验证码的主要入口方法（仅使用IMAP）
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            验证码字符串，如果未找到则返回None
        """
        self.logger.info("开始使用 IMAP 方法获取验证码...")
        return self.get_verification_code_via_imap(timeout)