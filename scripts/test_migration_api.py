"""验证迁移后旧目录是否彻底消失（对齐 Windows 原生行为）"""
import os, sys, time
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from core.migration import (
    get_shell_folders, MigrationPlan, restore_folder,
    SHELL_FOLDER_KEYS, get_default_c_path
)

def test():
    print("=== 验证：迁移后旧目录应彻底消失 ===\n")

    test_key = "My Video"
    label = SHELL_FOLDER_KEYS[test_key]
    folders = get_shell_folders()
    original_path = folders[test_key]
    target_base = Path("D:\\Users\\hwdem\\ZenClean_Test")

    print(f"[{label}] 当前路径: {original_path}")
    print(f"[{label}] 目标路径: {target_base / original_path.name}")

    # 在原目录放个标记文件
    marker = original_path / f"_test_{int(time.time())}.txt"
    try:
        marker.write_text("test marker", encoding="utf-8")
        print(f"\n✓ 已在源目录创建标记文件: {marker.name}")
    except Exception as e:
        print(f"✗ 创建标记文件失败: {e}")

    # 执行迁移
    print("\n[执行迁移]...")
    plan = MigrationPlan(folder_keys=[test_key], dst_base=target_base)
    report = plan.preflight()
    if not report.ok:
        print(f"✗ 前置检查失败: {report.issues}")
        return
    
    def on_progress(lbl, moved, total, f):
        pass  # 静默

    plan.execute(on_progress=on_progress)
    print("✓ 迁移执行完成")

    # 关键验证：旧目录是否还存在？
    print(f"\n[关键验证] C 盘旧路径 {original_path} 是否还存在？")
    if original_path.exists():
        # 检查是不是 Junction
        try:
            attrs = os.stat(str(original_path), follow_symlinks=False).st_file_attributes
            is_junction = bool(attrs & 0x400)
        except:
            is_junction = False
        
        if is_junction:
            print(f"  → 存在，但已是 Junction（兜底方案生效）")
        else:
            print(f"  ✗ 仍然存在且不是 Junction！这是 Bug！")
            print(f"  → 内容: {list(original_path.iterdir())}")
    else:
        print(f"  ✓ 已彻底消失！与 Windows 原生行为一致！")

    # 验证标记文件在 D 盘
    moved_marker = target_base / original_path.name / marker.name
    if moved_marker.exists():
        print(f"  ✓ 标记文件已在 D 盘: {moved_marker}")
    else:
        print(f"  ✗ 标记文件未在 D 盘找到")

    # 还原
    print("\n[还原回 C 盘]...")
    try:
        result = restore_folder(test_key, on_progress=on_progress)
        print(f"✓ {result}")
    except Exception as e:
        print(f"✗ 还原失败: {e}")

    # 清理测试目录
    try:
        tp = target_base / original_path.name
        if tp.exists() and not any(tp.iterdir()):
            tp.rmdir()
        if target_base.exists() and not any(target_base.iterdir()):
            target_base.rmdir()
    except:
        pass

    print("\n=== 测试结束 ===")

if __name__ == "__main__":
    test()
