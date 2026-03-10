
import os
import shutil
import json
import time
from pathlib import Path
import sys

# 注入项目路径
sys.path.append(os.path.join(os.getcwd(), "src"))

from core.app_migrator import AppMigrator, MigrationPhase, APP_TARGETS, APP_DATA_DIR

def setup_test_env():
    """准备测试数据"""
    test_src = Path("test_src_chaos").absolute()
    test_dest_drive = "D:"
    
    if test_src.exists():
        shutil.rmtree(test_src)
    test_src.mkdir(parents=True)
    
    # 创建一些测试文件
    for i in range(5):
        with open(test_src / f"file_{i}.dat", "w") as f:
            f.write("A" * 1024 * 1024 * 2) 
            
    print(f"Test source created at {test_src}")
    return test_src, test_dest_drive

def mock_chaos_migration():
    """手动模拟中断并恢复"""
    migrator = AppMigrator()
    test_src, dest_drive = setup_test_env()
    
    target_id = "chaos_test_target"
    from core.app_migrator import AppTarget
    chaos_target = AppTarget(
        id=target_id,
        name="混沌测试项目",
        path_template=str(test_src),
        icon="BUG_REPORT",
        description="用于模拟中断恢复的测试目标",
        risk_level="SAFE"
    )
    
    # 动态注入
    import core.app_migrator
    core.app_migrator.APP_TARGETS.append(chaos_target)
    
    print("\n--- Phase 1: Establish Dirty State ---")
    dest_base = Path(dest_drive) / "ZenClean_AppSpace" / chaos_target.name
    
    # 模拟：搬了前两个文件就“嗝屁”了
    if dest_base.exists():
        shutil.rmtree(dest_base)
    os.makedirs(dest_base, exist_ok=True)
    
    items_to_move = ["file_0.dat", "file_1.dat"]
    for item in items_to_move:
        shutil.move(test_src / item, dest_base / item)
    
    state = {
        "target_id": target_id,
        "target_name": chaos_target.name,
        "phase": "copying",
        "src_path": str(test_src),
        "dest_path": str(dest_base),
        "dest_drive": dest_drive,
        "start_time": time.ctime(),
        "total_size": 1024 * 1024 * 10,
        "moved_items": items_to_move,
        "failed_items": [],
        "error": None
    }
    
    # 保存虚假状态
    state_dir = Path(APP_DATA_DIR) / "migration_states"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / f"{target_id}.json"
    
    with open(state_file, "w", encoding='utf-8') as f:
        json.dump(state, f, indent=2)
        
    print(f"Dirty state fixed at {state_file}")
    
    # 检查检测
    interrupted = migrator.check_interrupted_migrations()
    print(f"Scanner found interrupted tasks: {len(interrupted)}")
    
    if len(interrupted) == 0:
        return

    print("\n--- Phase 2: Resume & Complete ---")
    # 真正测试恢复逻辑
    success, msg = migrator.recover_interrupted_migration(target_id)
    print(f"Recovery Result: {success}, Message: {msg}")
    
    # 验证
    if migrator.is_already_migrated(test_src):
        print("FINAL SUCCESS: Junction established.")
        files_moved = list(dest_base.iterdir())
        print(f"Files in destination: {len(files_moved)} ({[f.name for f in files_moved]})")
    else:
        print("RECOVERY FAILED: Junction missing.")

    # 清理
    if test_src.exists() and migrator.is_already_migrated(test_src):
        os.rmdir(test_src)
    if dest_base.exists():
        shutil.rmtree(dest_base)
    core.app_migrator.APP_TARGETS.remove(chaos_target)

if __name__ == "__main__":
    try:
        mock_chaos_migration()
    except Exception as e:
        print(f"Chaos test failed: {e}")
        import traceback
        traceback.print_exc()
