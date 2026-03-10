import os
import shutil
import tempfile
from pathlib import Path

# 针对由于在脚本模式下运行可能找不到模块的相对引用问题
import sys
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent / 'src'
sys.path.insert(0, str(src_dir))

from core.app_migrator import AppMigrator, APP_TARGETS

def create_large_dummy_file(filepath: Path, size_mb: int):
    """生成指定大小(MB)的测试文件"""
    with open(filepath, "wb") as f:
        f.write(os.urandom(size_mb * 1024 * 1024))

def run_io_test():
    print("🚀 启动大厂应用无损极客搬家 - 真实 I/O 压测沙盒")

    # 1. 建立模拟源目录 (类似 C:\Users\xxx\Documents\WeChat Files)
    # 我们使用 APPDATA 或 LOCALAPPDATA 下建个临时夹，以避开权限问题，但仍属于 C 盘。
    mock_c_drive_base = Path(os.environ.get("LOCALAPPDATA")) / "ZenClean_MochaTest_Src"
    mock_wechat_dir = mock_c_drive_base / "WeChat Files"
    
    # 清理历史遗留
    if mock_c_drive_base.exists():
        # 如果是 Junction，先 rmdir
        try:
            if os.stat(str(mock_wechat_dir), follow_symlinks=False).st_file_attributes & 0x400:
                os.rmdir(str(mock_wechat_dir))
            shutil.rmtree(str(mock_c_drive_base), ignore_errors=True)
        except Exception:
            pass

    os.makedirs(mock_wechat_dir, exist_ok=True)
    
    # 填入测试数据 (生成几个 10MB 的假文件)
    print("📁 正在生成源端测试文件 (30MB)...")
    for i in range(3):
        create_large_dummy_file(mock_wechat_dir / f"dummy_data_{i}.bin", 10)
    
    # 2. 建立模拟目标盘符目录 (由于没有真实 D 盘分配控制权，我们在 D: 根建个隔离测试区)
    mock_d_drive_base = Path("D:\\ZenClean_MochaTest_Dest")
    if mock_d_drive_base.exists():
        shutil.rmtree(str(mock_d_drive_base), ignore_errors=True)
    os.makedirs(mock_d_drive_base, exist_ok=True)

    # 3. 热补丁 (Hot-patch): 替换 APP_TARGETS 里微信路径，指向我们的沙盒
    target = next(t for t in APP_TARGETS if t.id == "wechat_data")
    original_template = target.path_template
    target.path_template = str(mock_wechat_dir) # 劫持为测试路径
    
    migrator = AppMigrator()
    
    # 清理可能残留的历史记录
    history = migrator.get_history()
    history = [h for h in history if h["target_id"] != "wechat_data"]
    migrator._save_history(history)

    # =============== 测试阶段 1：搬运与 Junction 建立 ===============
    print("\n📦 测试 1: 执行迁移到 D 盘沙盒...")
    # dest_drive 填入模拟的 D 盘基础路径
    success, msg = migrator.execute_migration("wechat_data", str(mock_d_drive_base))
    print(f"执行结果: {success} -> {msg}")
    assert success, f"迁移失败: {msg}"

    # 验证 C 盘路径是否变成了 Junction
    is_junction = migrator.is_already_migrated(mock_wechat_dir)
    print(f"🔍 源路径是否已变身为 Junction 软连接: {is_junction}")
    assert is_junction, "致命错误：源路径未能正确转化为 Junction！"

    # 验证 D 盘是否实打实多出了那些文件
    real_dest = mock_d_drive_base / "ZenClean_AppSpace" / target.name
    dest_files = list(real_dest.glob("*.bin"))
    print(f"👉 目标盘真实落盘文件数: {len(dest_files)}")
    assert len(dest_files) == 3, "目标盘文件数量丢失！"

    # =============== 测试阶段 2：拆毁 Junction 还原回迁 ===============
    print("\n↩️ 测试 2: 撤销映射并执行物理回迁...")
    success, msg = migrator.restore_migration("wechat_data")
    print(f"执行结果: {success} -> {msg}")
    assert success, f"还原失败: {msg}"

    # 验证 C 盘是否变回了原貌
    is_junction_now = migrator.is_already_migrated(mock_wechat_dir)
    print(f"🔍 源路径是否不再属于 Junction: {not is_junction_now}")
    assert not is_junction_now, "致命错误：软链接外壳未能拆除！"

    # 验证 C 盘里面的文件是否活着
    src_files = list(mock_wechat_dir.glob("*.bin"))
    print(f"👉 回迁后源盘存活文件数: {len(src_files)}")
    assert len(src_files) == 3, "回迁后源盘文件数量丢失！"

    # ================= 结尾清理 =================
    print("\n🧹 沙盒清理...")
    target.path_template = original_template # 恢复补丁
    shutil.rmtree(str(mock_c_drive_base), ignore_errors=True)
    shutil.rmtree(str(mock_d_drive_base), ignore_errors=True)
    
    print("\n✅ 所有 I/O 核心链路测试通过！防病毒软件未在此过程中发生恶性拦截。")

if __name__ == "__main__":
    run_io_test()
