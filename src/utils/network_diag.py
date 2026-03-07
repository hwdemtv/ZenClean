"""
网络连接诊断工具
用于排查授权时的网络连接问题
"""
import sys
import socket
import ssl
import urllib.parse
from typing import List, Tuple

def test_dns_resolution(hostname: str) -> Tuple[bool, str]:
    """测试DNS解析"""
    try:
        ip = socket.gethostbyname(hostname)
        return True, f"DNS解析成功: {hostname} -> {ip}"
    except socket.gaierror as e:
        return False, f"DNS解析失败: {e}"

def test_tcp_connect(hostname: str, port: int = 443, timeout: int = 5) -> Tuple[bool, str]:
    """测试TCP连接"""
    try:
        sock = socket.create_connection((hostname, port), timeout=timeout)
        sock.close()
        return True, f"TCP连接成功: {hostname}:{port}"
    except Exception as e:
        return False, f"TCP连接失败: {e}"

def test_ssl_connect(hostname: str, port: int = 443, timeout: int = 5) -> Tuple[bool, str]:
    """测试SSL/TLS握手"""
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                return True, f"SSL握手成功: {hostname}:{port}"
    except Exception as e:
        return False, f"SSL握手失败: {e}"

def test_http_get(url: str, timeout: int = 5) -> Tuple[bool, str]:
    """测试HTTP GET请求（使用requests）"""
    try:
        import requests
        response = requests.get(url, timeout=timeout, verify=True)
        return True, f"HTTP请求成功: {url} (状态码: {response.status_code})"
    except Exception as e:
        return False, f"HTTP请求失败: {e}"

def diagnose_url(url: str) -> List[Tuple[str, bool, str]]:
    """对单个URL进行完整诊断"""
    results = []
    
    try:
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        
        # DNS解析
        success, msg = test_dns_resolution(hostname)
        results.append(("DNS解析", success, msg))
        
        if success:
            # TCP连接
            success, msg = test_tcp_connect(hostname, port)
            results.append(("TCP连接", success, msg))
            
            # SSL/TLS握手（仅HTTPS）
            if parsed.scheme == "https":
                success, msg = test_ssl_connect(hostname, port)
                results.append(("SSL/TLS握手", success, msg))
            
            # HTTP请求
            test_url = f"{parsed.scheme}://{hostname}"
            success, msg = test_http_get(test_url, timeout=5)
            results.append(("HTTP请求", success, msg))
        
    except Exception as e:
        results.append(("URL解析", False, f"URL格式错误: {e}"))
    
    return results

def run_full_diagnosis(server_urls: List[str]) -> str:
    """对所有授权服务器进行完整诊断并返回报告"""
    report_lines = ["=" * 60, "ZenClean 网络连接诊断报告", "=" * 60, ""]
    
    for url in server_urls:
        report_lines.append(f"诊断目标: {url}")
        report_lines.append("-" * 60)
        
        results = diagnose_url(url)
        for test_name, success, message in results:
            status = "✅ 通过" if success else "❌ 失败"
            report_lines.append(f"{status} {test_name}: {message}")
        
        report_lines.append("")
    
    # 系统信息
    report_lines.extend([
        "=" * 60,
        "系统环境信息",
        "=" * 60,
        f"Python版本: {sys.version}",
        f"操作系统: {sys.platform}",
    ])
    
    # 检查requests库
    try:
        import requests
        report_lines.append(f"requests库版本: {requests.__version__}")
    except:
        report_lines.append("requests库: 未安装")
    
    # 检查SSL
    try:
        import ssl
        report_lines.append(f"SSL版本: {ssl.OPENSSL_VERSION}")
    except:
        report_lines.append("SSL: 不可用")
    
    return "\n".join(report_lines)

if __name__ == "__main__":
    # 测试用的URL列表
    test_urls = [
        "https://km.hwdemtv.com",
        "https://kami.hwdemtv.com",
        "https://hw-license-center.hwdemtv.workers.dev"
    ]
    
    print(run_full_diagnosis(test_urls))
    print("\n按回车键退出...")
    input()
