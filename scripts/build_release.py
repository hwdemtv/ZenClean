import os
import shutil
import subprocess
import sys
from pathlib import Path

# --- 配置区 ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"
RELEASE_DIR = PROJECT_ROOT / "dist"
SPEC_FILE = PROJECT_ROOT / "zenclean.spec"

def clean_old_builds():
    """清理旧的打包产物，确保环境干净"""
    print("🧹 [1/3] 清理旧的编译残骸 (build/release_build)...")
    for d in [BUILD_DIR, RELEASE_DIR]:
        if d.exists():
            try:
                shutil.rmtree(d)
                print(f"  - 已删除: {d.name}")
            except Exception as e:
                print(f"  ! 警告: 无法常规删除 {d.name}: {e}")
                if "拒绝访问" in str(e) or "Access is denied" in str(e):
                    # Flet 的热重载或音频插件常会引发底层的长期系统锁，杀进程都没用
                    import time
                    rename_target = d.with_name(f"{d.name}_locked_{int(time.time())}")
                    try:
                        d.rename(rename_target)
                        print(f"  - ⚡ 已采取重命名隔离绕过文件锁: {rename_target.name}")
                    except Exception as re_err:
                        print(f"  - ❌ 隔离失败，打包核心可能被严重污染。错误: {re_err}")

def run_pyinstaller():
    """执行 PyInstaller 打包指令"""
    print(f"🚀 [2/3] 正在启动 PyInstaller 进行全量编译打包 (依据: {SPEC_FILE.name})...")
    print("  - 这可能需要几分钟，请耐心等待...")
    
    # 构建命令
    cmd = [
        sys.executable, "-m", "PyInstaller", 
        "--noconfirm", 
        "--distpath", str(RELEASE_DIR),
        str(SPEC_FILE)
    ]
    
    # 捕获输出并实时显示
    try:
        process = subprocess.Popen(
            cmd, 
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                # 过滤掉一些无关痛痒的常规 INFO，让界面清爽紧凑些
                line = output.strip()
                if "INFO:" not in line or "Building" in line or "Completed" in line:
                    print(f"    [PyInstaller] {line}")
        
        rc = process.poll()
        if rc == 0:
            print("✅ [PyInstaller] 编译成功！")
            return True
        else:
            print(f"❌ [PyInstaller] 编译失败，退出码: {rc}")
            return False
            
    except Exception as e:
        print(f"❌ 启动 PyInstaller 进程失败: {e}")
        return False

def verify_output():
    """审计最终产物"""
    print("🔍 [3/3] 审计与环境校验...")
    target_exe = RELEASE_DIR / "ZenClean" / "ZenClean.exe"
    
    if target_exe.exists():
        size_mb = target_exe.stat().st_size / (1024 * 1024)
        print(f"  - 校验通过：找到核心执行体 {target_exe.name} (大小: {size_mb:.2f} MB)")
        print(f"  - 📦 产物路径: {target_exe.parent}")
        print("\n🎉 成功！全量编译打包完成。请将整个 [ZenClean] 目录发给无 Python 环境的测试机进行双击校验。")
    else:
        print("  ❌ 警告：未找到目标构建产物 ZenClean.exe，打包可能并未真正成功。")

if __name__ == "__main__":
    print(f"[{'ZenClean 生产构建管线':=^40}]")
    clean_old_builds()
    if run_pyinstaller():
        verify_output()
    else:
        sys.exit(1)
