import sys
import os
from pathlib import Path

# 将 src 目录添加到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.whitelist import is_protected, is_migratable, should_skip_dir

def test_protected_prefixes():
    """测试系统关键前缀保护"""
    assert is_protected(r"C:\Windows\System32\shell32.dll")
    assert is_protected(r"C:\Windows\SysWOW64\ntdll.dll")
    assert is_protected(r"C:\Program Files\Windows Defender\MpCmdRun.exe")
    # 边界检查
    assert is_protected(r"C:\Windows\System32")
    # 不应该匹配的情况
    assert not is_protected(r"C:\Windows\System32_bak\test.txt")
    assert not is_protected(r"C:\MyData\System32")

def test_protected_filenames():
    """测试受保护的文件后缀/全名"""
    assert is_protected(r"C:\Users\Admin\Desktop\driver.sys")
    assert is_protected(r"C:\temp\some.dll")
    assert is_protected(r"C:\Downloads\installer.msi")
    assert is_protected(r"C:\pagefile.sys")
    assert is_protected(r"C:\hiberfil.sys")
    # 正常文件不应保护
    assert not is_protected(r"C:\Users\Admin\Desktop\report.pdf")
    assert not is_protected(r"C:\temp\data.json")

def test_user_data_protection():
    """测试用户敏感数据目录保护"""
    # 微信聊天记录根目录
    assert is_protected(r"C:\Users\John\Documents\WeChat Files")
    assert is_protected(r"c:\users\guest\documents\微信文件")
    # 浏览器用户数据根目录
    assert is_protected(r"C:\Users\Admin\AppData\Local\Google\Chrome\User Data\Default")
    
    # 子目录不应受到根目录规则的"精确匹配"保护（允许清理 Cache 等）
    # 注意：is_protected 中用户数据规则用的是 fullmatch
    assert not is_protected(r"C:\Users\John\Documents\WeChat Files\wxid_123\FileStorage\Cache")
    
    # 验证 is_migratable
    assert is_migratable(r"C:\Users\John\Documents\WeChat Files")
    assert not is_migratable(r"C:\Windows\System32")

def test_skip_dir_logic():
    """测试跳过目录逻辑"""
    # 全局跳过
    assert should_skip_dir(r"C:\Windows\WinSxS", "WinSxS")
    assert should_skip_dir(r"C:\SomePath\Package Cache", "Package Cache")
    
    # 非跳过目录
    assert not should_skip_dir(r"C:\temp\myfolder", "myfolder")

def test_case_insensitivity():
    """测试大小写不敏感"""
    assert is_protected(r"c:\windows\system32\KERNEL32.DLL")
    assert is_protected(r"C:\WINDOWS\SYSTEM32\kernel32.dll")
