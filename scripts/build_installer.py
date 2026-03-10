import os
import sys
import shutil
import subprocess
from pathlib import Path

def main():
    print("=" * 30)
    print(" 🚀 启动 ZenClean 打包流水线 ")
    print("=" * 30)

    project_root = Path(__file__).parent.parent.resolve()
    iscc_path = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    iss_file = project_root / "zenclean.iss"
    spec_file = project_root / "zenclean.spec"

    # [1/3] 清理旧产物
    print("\n[1/3] 清理旧的构建文件...")
    for folder in ["dist", "build", "installer"]:
        target = project_root / folder
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
            print(f"  - 已清理: {target.name}")

    # [2/3] PyInstaller
    print("\n[2/3] 执行 PyInstaller 生成独立程序集...")
    os.chdir(project_root)
    result = subprocess.run([sys.executable, "-m", "PyInstaller", "--clean", str(spec_file)])
    if result.returncode != 0:
        print("X PyInstaller 打包失败！", file=sys.stderr)
        sys.exit(result.returncode)
    print("PyInstaller 成功生成 dist/ZenClean。")

    # [3/3] Inno Setup
    print("\n[3/3] 正在挂载 Inno Setup 编译器...")
    if not os.path.exists(iscc_path):
        print(f"⚠️ 未检测到 Inno Setup 安装目录 ({iscc_path})。", file=sys.stderr)
        print("跳过最后一步安装包生成。您可以在 dist/ZenClean 找到绿色免安装版。")
        sys.exit(0)

    result = subprocess.run([iscc_path, str(iss_file)])
    if result.returncode != 0:
        print("X Inno Setup 编译失败！", file=sys.stderr)
        sys.exit(result.returncode)

    print("\n🎉 打包流水线全部完成！")
    print(f"成品安装包已输出至: {project_root / 'installer'}")

if __name__ == "__main__":
    main()
