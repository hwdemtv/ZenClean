import os
import shutil
import sys
from setuptools import setup, Extension

try:
    from Cython.Build import cythonize
except ImportError:
    print("Cython is not installed. Please run `pip install cython`.")
    sys.exit(1)

# 获取项目根目录
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT_DIR)

# 目标需要加密编译的文件 (相对 ROOT_DIR 的路径)
TARGETS = [
    "src/core/auth.py",
    "src/ai/cloud_engine.py",
    "src/config/settings.py"
]

def build():
    # 构造 extensions，去除 src 前缀，转换为模块名
    extensions = [
        Extension(
            name=f.replace("src/", "").replace("/", ".").replace(".py", ""),
            sources=[f]
        ) for f in TARGETS
    ]
    
    # 运行 setup 编译
    setup(
        name="ZenClean Core Modules",
        ext_modules=cythonize(
            extensions,
            compiler_directives={
                'language_level': "3",
                'always_allow_keywords': True,
                'optimize.unpack_method_calls': True,
            }
        ),
        script_args=["build_ext", "--build-lib", "src"] # 直接输出构建结果到 src 目录下对应的包路径
    )
    
    # 清除生成的中间 .c 文件和 build 临时文件夹
    for f in TARGETS:
        c_file = f.replace(".py", ".c")
        if os.path.exists(c_file):
            os.remove(c_file)
            
    if os.path.exists("build"):
        shutil.rmtree("build")
        
    print("\n[✔] Cython (.pyd) build completed successfully.")

if __name__ == "__main__":
    build()
