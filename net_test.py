import requests
import sys
import ssl
import socket


def diagnose_connection():
    print(f"=== 环境诊断 ===")
    print(f"Python 版本: {sys.version}")
    print(f"requests 版本: {requests.__version__}")
    print(f"OpenSSL 版本: {ssl.OPENSSL_VERSION}")
    print(f"socket 默认超时: {socket.getdefaulttimeout()}")

    print(f"\n=== 测试连接 ===")
    url = 'https://www.aibase.com'

    # 测试1：基本连接
    try:
        print("测试1: 基本 GET 请求...")
        response = requests.get(url, timeout=10)
        print(f"✓ 成功！状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 失败: {type(e).__name__}: {e}")

    # 测试2：使用不同的方法
    try:
        print("\n测试2: 使用 Session...")
        session = requests.Session()
        session.trust_env = False
        response = session.get(url, timeout=10)
        print(f"✓ 成功！状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 失败: {type(e).__name__}: {e}")

    # 测试3：禁用 SSL 验证
    try:
        print("\n测试3: 禁用 SSL 验证...")
        response = requests.get(url, timeout=10, verify=False)
        print(f"✓ 成功！状态码: {response.status_code}")
    except Exception as e:
        print(f"✗ 失败: {type(e).__name__}: {e}")

    # 测试4：DNS 解析
    try:
        print("\n测试4: DNS 解析...")
        ip = socket.gethostbyname('www.aibase.com')
        print(f"✓ DNS 解析成功: {ip}")
    except Exception as e:
        print(f"✗ DNS 解析失败: {e}")


diagnose_connection()