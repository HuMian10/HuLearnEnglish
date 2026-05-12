import smtplib
from email.mime.text import MIMEText
from email.header import Header

# 163邮箱配置
smtp_server = "smtp.163.com"
smtp_port = 465  # SSL端口
sender_email = "hulearnenglish@163.com"  # 你的163邮箱地址
password = "MSSX4c76C7YfTmq2"  # 授权码（不是登录密码）
receiver_email = "1724535697@qq.com"  # 收件人邮箱

# 创建邮件内容
msg = MIMEText("这是Python自动发送的测试邮件", "plain", "utf-8")
msg["From"] = Header(sender_email)
msg["To"] = Header(receiver_email)
msg["Subject"] = Header("Python自动邮件测试", "utf-8")

# 发送邮件
try:
    server = smtplib.SMTP_SSL(smtp_server, smtp_port)
    server.login(sender_email, password)
    server.sendmail(sender_email, [receiver_email], msg.as_string())
    print("邮件发送成功！")
except Exception as e:
    print(f"发送失败：{e}")
finally:
    server.quit()