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
            config: 完整配置字典，包含gmail配置和email_management配置
        """
        self.config = config
        self.gmail_config = config.get("gmail", {})
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
            self.logger.info(
                f"正在连接Gmail IMAP服务器 (邮箱: {self.gmail_config['email'][:3]}***{self.gmail_config['email'][-10:]})")

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
                    mail = imaplib.IMAP4_SSL(
                        "imap.gmail.com", 993, ssl_context=context)
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
                    mail.login(self.gmail_config["email"], self.gmail_config["password"])
                    self.logger.info("✅ Gmail IMAP认证成功")
                    break
                except imaplib.IMAP4.error as login_error:
                    error_msg = str(login_error)

                    if auth_retry < max_auth_retries - 1 and "SSL" in error_msg:
                        self.logger.warning(
                            f"认证尝试{auth_retry + 1}失败，可能是网络问题，2秒后重试...")
                        time.sleep(2)
                        continue

                    # 最后一次失败，提供详细诊断
                    self.logger.error(f"❌ Gmail IMAP认证失败: {error_msg}")

                    if "AUTHENTICATIONFAILED" in error_msg:
                        self.logger.error("🔍 认证失败原因分析:")
                        self.logger.error("   1. 应用专用密码可能已过期，请重新生成")
                        self.logger.error(
                            "   2. 访问: https://myaccount.google.com/apppasswords")
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
                # 使用指定的发送时间，往前推2分钟确保不遗漏，并且考虑邮件延迟
                search_datetime = datetime.fromtimestamp(
                    sent_after_time - 120)  # 往前推2分钟
                search_time = search_datetime.strftime("%d-%b-%Y")
                self.logger.info(
                    f"搜索 {search_datetime.strftime('%Y-%m-%d %H:%M:%S')} 之后的邮件")
            else:
                # 默认搜索最近5分钟，给邮件更多到达时间
                search_time = (datetime.now() -
                               timedelta(minutes=5)).strftime("%d-%b-%Y")

            start_time = time.time()
            search_attempt = 0
            max_attempts = 5

            # 添加邮箱状态检查
            try:
                status, message_count = mail.select("inbox")
                self.logger.info(f"收件箱状态: {status}, 当前邮件数: {message_count}")
            except:
                pass

            while time.time() - start_time < timeout and search_attempt < max_attempts:
                search_attempt += 1
                elapsed_time = time.time() - start_time
                self.logger.info(
                    f"第{search_attempt}/{max_attempts}次搜索邮件... (已用时 {elapsed_time:.1f}s/{timeout}s)")

                # 首次搜索时，检查最新邮件情况
                if search_attempt == 1:
                    try:
                        # 获取最新的5封邮件进行调试
                        status, all_messages = mail.search(None, 'ALL')
                        if status == 'OK' and all_messages[0]:
                            all_ids = all_messages[0].split()
                            recent_ids = all_ids[-5:] if len(
                                all_ids) >= 5 else all_ids
                            self.logger.info(
                                f"邮箱中最新5封邮件ID: {[id.decode() for id in recent_ids]}")
                    except Exception as debug_error:
                        self.logger.debug(f"调试信息获取失败: {debug_error}")

                # 进行快速的双重搜索（解决邮件到达时序问题）
                for search_round in range(2):
                    if search_round == 1:
                        # 第二轮搜索前等待1秒，确保新邮件被服务器索引
                        time.sleep(1)
                        self.logger.debug("进行第二轮快速搜索...")

                    try:
                        # 渐进式搜索策略：从最精确到最宽泛
                        search_criteria = [
                            # 第一优先级：最新的验证码相关邮件（不限未读状态）
                            f'(SINCE "{search_time}") (SUBJECT "验证" OR SUBJECT "verification" OR SUBJECT "code" OR SUBJECT "驗證")',
                            f'(SINCE "{search_time}") (BODY "验证码" OR BODY "verification code" OR BODY "驗證碼")',

                            # 第二优先级：M-Team相关邮件
                            f'(SINCE "{search_time}") (FROM "m-team" OR SUBJECT "m-team" OR BODY "m-team")',
                            f'(SINCE "{search_time}") (FROM "mteam" OR SUBJECT "mteam" OR BODY "mteam")',

                            # 第三优先级：常见PT站发送地址（精确匹配）
                            f'(SINCE "{search_time}") (FROM "web@m-team.cc" OR FROM "noreply@m-team.cc" OR FROM "admin@m-team.cc")',
                            f'(SINCE "{search_time}") (FROM "no-reply@m-team.cc" OR FROM "service@m-team.cc" OR FROM "system@m-team.cc")',
                            f'(SINCE "{search_time}") (FROM "@m-team.cc")',

                            # 第四优先级：任何包含数字验证码的邮件
                            f'(SINCE "{search_time}") (BODY "\\d{{6}}" OR BODY "\\d{{4}}")',

                            # 第五优先级：所有最新邮件（时间范围内）
                            f'(SINCE "{search_time}")',

                            # 第六优先级：放宽时间的验证码搜索
                            '(SUBJECT "验证" OR SUBJECT "verification" OR SUBJECT "code" OR SUBJECT "驗證")',
                            '(BODY "验证码" OR BODY "verification code" OR BODY "驗證碼")',

                            # 最后：所有未读邮件（作为兜底）
                            'UNSEEN'
                        ]

                        for i, criteria in enumerate(search_criteria):
                            try:
                                self.logger.debug(
                                    f"使用搜索条件 {i+1}/{len(search_criteria)}: {criteria}")
                                status, messages = mail.search(None, criteria)
                                if status == 'OK' and messages[0]:
                                    message_ids = messages[0].split()
                                    if message_ids:
                                        self.logger.info(
                                            f"搜索条件 {i+1} 找到 {len(message_ids)} 封邮件")

                                        # 处理所有找到的邮件，从最新的开始
                                        # 从最新的邮件开始处理
                                        for msg_id in reversed(message_ids):
                                            self.logger.debug(
                                                f"检查邮件ID: {msg_id}")
                                            verification_code = self._extract_code_from_email(
                                                mail, msg_id, sent_after_time)
                                            if verification_code:
                                                self.logger.info(
                                                    f"✅ 成功从邮件 {msg_id} 中提取验证码: {verification_code}")

                                                # 根据配置决定是否删除邮件
                                                email_config = self.config.get(
                                                    'email_management', {})
                                                if email_config.get('delete_after_use', False):
                                                    try:
                                                        wait_time = email_config.get(
                                                            'delete_wait_seconds', 5)
                                                        self.logger.info(
                                                            f"等待{wait_time}秒后删除验证码邮件...")
                                                        time.sleep(wait_time)
                                                        self._delete_email_safely(
                                                            mail, msg_id)
                                                    except Exception as delete_error:
                                                        self.logger.warning(
                                                            f"删除邮件失败: {delete_error}")
                                                else:
                                                    self.logger.info(
                                                        "📧 邮件删除功能已禁用，验证码邮件将保留")

                                                mail.close()
                                                mail.logout()
                                                return verification_code

                                        self.logger.debug(
                                            f"搜索条件 {i+1} 的所有邮件都未包含有效验证码")
                                else:
                                    self.logger.debug(f"搜索条件 {i+1} 未找到邮件")
                            except Exception as e:
                                self.logger.debug(f"搜索条件 {i+1} 执行失败: {e}")
                                continue

                    except Exception as search_error:
                        self.logger.error(
                            f"第{search_round + 1}轮搜索过程中发生错误: {search_error}")
                        continue

                # 两轮搜索都没找到，动态等待后重试
                remaining_time = timeout - (time.time() - start_time)
                if remaining_time > 5 and search_attempt < max_attempts:  # 确保有足够时间进行下次搜索
                    wait_time = min(5, remaining_time - 2)  # 动态调整等待时间，但不超过5秒
                    self.logger.info(
                        f"本次搜索未找到验证码邮件，{wait_time:.1f}秒后重试... (剩余时间: {remaining_time:.1f}s)")
                    time.sleep(wait_time)
                elif search_attempt >= max_attempts:
                    self.logger.warning(f"已达到最大搜索次数限制 ({max_attempts} 次)")
                    break
                else:
                    self.logger.warning(f"剩余时间不足 ({remaining_time:.1f}s)，停止搜索")
                    break

            mail.close()
            mail.logout()

            # 提供详细的失败信息
            total_time = time.time() - start_time
            self.logger.error(f"❌ 搜索失败总结:")
            self.logger.error(f"   • 总搜索时间: {total_time:.1f}s / {timeout}s")
            self.logger.error(f"   • 搜索尝试次数: {search_attempt}/{max_attempts}")
            self.logger.error(f"   • 搜索时间范围: 从 {search_time} 开始")
            if sent_after_time:
                search_datetime = datetime.fromtimestamp(sent_after_time)
                self.logger.error(
                    f"   • 期望邮件发送时间: {search_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

            self.logger.error("🔍 可能的原因:")
            self.logger.error("   1. 邮件延迟到达（M-Team服务器延迟）")
            self.logger.error("   2. 邮件被自动过滤或放入垃圾邮件")
            self.logger.error("   3. M-Team发送地址变更")
            self.logger.error("   4. 验证码邮件格式变更")
            self.logger.error("   5. 网络连接问题导致邮件同步延迟")

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
                self.logger.error(
                    "   2. 访问: https://myaccount.google.com/apppasswords")
                self.logger.error("   3. 删除旧密码，创建新的'M-Team自动登录'密码")
                self.logger.error("   4. 确保密码复制时没有多余空格")
                self.logger.error("   5. 确认两步验证已启用")
            elif "timeout" in error_msg.lower():
                self.logger.error("⏰ 连接超时 - 可能的解决方案:")
                self.logger.error("   1. 检查网络延迟")
                self.logger.error("   2. 尝试使用VPN")
                self.logger.error("   3. 稍后重试")

            return None

    def _delete_email_safely(self, mail, message_id: bytes) -> bool:
        """
        安全地删除指定的邮件

        Args:
            mail: IMAP连接对象
            message_id: 邮件ID

        Returns:
            bool: 删除是否成功
        """
        try:
            # 标记邮件为已删除
            mail.store(message_id, '+FLAGS', '\\Deleted')

            # 执行删除操作
            result = mail.expunge()

            if result[0] == 'OK':
                self.logger.info(f"✅ 已删除验证码邮件 (ID: {message_id.decode()})")
                return True
            else:
                self.logger.warning(f"删除邮件失败: {result}")
                return False

        except Exception as e:
            self.logger.error(f"删除邮件时发生错误: {e}")
            return False

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
                            self.logger.info(
                                f"跳过旧邮件 - 发送方: {sender}, 时间: {email_time.strftime('%Y-%m-%d %H:%M:%S')}")
                            return None
                        else:
                            self.logger.info(
                                f"处理新邮件 - 发送方: {sender}, 时间: {email_time.strftime('%Y-%m-%d %H:%M:%S')}")
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
                matches = re.findall(
                    pattern, body, re.IGNORECASE | re.MULTILINE)
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
            self.logger.info(
                f"只查找在 {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(sent_after_time))} 之后收到的邮件")
        return self.get_verification_code_via_imap(timeout, sent_after_time)
