import os
import sys
import zipfile
import hashlib

def calculate_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def verify_release(zip_path):
    print("=" * 60)
    print(f"🔍 正在验证发布包: {os.path.basename(zip_path)}")
    print("=" * 60)
    
    if not os.path.exists(zip_path):
        print("❌ 错误: 找不到指定的 Zip 文件")
        return

    required_structure = [
        "ZenClean/ZenClean.exe",
        "ZenClean/start.bat",
        "ZenClean/assets/icon.png",
        "ZenClean/config/file_kb.json",
        "ZenClean/_internal/"
    ]

    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            all_files = z.namelist()
            missing = []
            for req in required_structure:
                if not any(f.startswith(req) for f in all_files):
                    missing.append(req)
            
            if missing:
                print("❌ 验证失败！缺少以下关键组件:")
                for m in missing: print(f"  - {m}")
            else:
                print("✅ 结构完整性校验通过")
                print(f"📦 文件大小: {os.path.getsize(zip_path)/1024/1024:.2f} MB")
                print(f"🔑 MD5 校验码: {calculate_md5(zip_path)}")
                
    except Exception as e:
        print(f"❌ 读取压缩包出错: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python verify_release.py <your_zip_file>")
    else:
        verify_release(sys.argv[1])
