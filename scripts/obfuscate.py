import os
import shutil
import subprocess
import sys

# 项目根目录
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# 关键业务逻辑文件
TARGETS = [
    "src/core/auth.py",
    "src/ai/cloud_engine.py",
    "src/config/settings.py"
]

def run_command(cmd):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT_DIR)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    print(result.stdout)
    return True

def obfuscate():
    # 1. 确保 pyarmor 已安装
    try:
        import pyarmor
    except ImportError:
        print("PyArmor is not installed. Run 'pip install pyarmor'")
        return

    # 2. 创建临时混淆输出目录
    dist_dir = os.path.join(ROOT_DIR, ".pyarmor_dist")
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    os.makedirs(dist_dir)

    print("Starting PyArmor obfuscation...")

    # 3. 逐个文件执行混淆
    for target in TARGETS:
        print(f"\n--- Processing {target} ---")
        tmp_out = os.path.join(dist_dir, "tmp_single")
        if os.path.exists(tmp_out): shutil.rmtree(tmp_out)
        
        cmd = ["pyarmor", "gen", "-O", tmp_out, target]

        if not run_command(cmd):
            print(f"Failed to obfuscate {target}")
            continue
            
        # [CRITICAL] PyArmor 8+ 单文件模式下，
        # 如果输入是 'src/core/auth.py'，它会在 tmp_out 下直接生成 'auth.py'
        fname = os.path.basename(target)
        source_file = os.path.join(tmp_out, fname)
        
        final_dest = os.path.join(dist_dir, target.replace("src/", ""))
        os.makedirs(os.path.dirname(final_dest), exist_ok=True)
        
        if os.path.exists(source_file):
            shutil.move(source_file, final_dest)
            print(f"Success: {target} (Obfuscated) -> {final_dest}")
        else:
            print(f"Warning: Could not find obfuscated file at {source_file}")
        
        # 提取运行时包
        runtime_src = os.path.join(tmp_out, "pyarmor_runtime_000000")
        runtime_dest = os.path.join(dist_dir, "pyarmor_runtime_000000")
        if os.path.exists(runtime_src) and not os.path.exists(runtime_dest):
            shutil.copytree(runtime_src, runtime_dest)
            print(f"Runtime package extracted to {runtime_dest}")

    print("\n[✔] PyArmor obfuscation batch process completed.")
    print(f"Ready for replacement: {dist_dir}")

if __name__ == "__main__":
    obfuscate()
