#!/usr/bin/env python
"""
ZenClean 网络诊断工具 - 独立运行版本
用于排查授权时的网络连接问题

使用方法:
    python run_network_diag.py
"""
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config.settings import LICENSE_SERVER_URLS
from utils.network_diag import run_full_diagnosis

if __name__ == "__main__":
    print("正在运行ZenClean网络诊断...")
    print("这将测试与授权服务器的连接情况\n")
    
    try:
        report = run_full_diagnosis(LICENSE_SERVER_URLS)
        print(report)
        
        print("\n" + "=" * 60)
        print("诊断完成！")
        print("=" * 60)
        print("\n常见问题解决:")
        print("1. 如果是DNS解析失败: 检查网络连接或修改DNS设置")
        print("2. 如果是TCP连接失败: 检查防火墙是否拦截")
        print("3. 如果是SSL握手失败: 检查系统时间和SSL证书")
        print("4. 如果是HTTP请求失败: 检查代理设置或网络策略")
        print("\n如果问题持续，请将此诊断结果提供给技术支持。")
        
    except Exception as e:
        print(f"诊断过程中出错: {e}")
        import traceback
        traceback.print_exc()
    
    input("\n按回车键退出...")
