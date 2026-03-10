"""
Windows Installer 补丁缓存分析器

用于分析 C:\Windows\Installer\$PatchCache$ 目录中的内容，
帮助用户了解具体的补丁信息。
"""

import os
import shutil
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from core.logger import logger


@dataclass
class PatchInfo:
    """单个补丁的信息"""
    name: str           # 文件/文件夹名
    path: str           # 完整路径
    size_bytes: int     # 大小
    modified_time: datetime  # 修改时间
    patch_id: Optional[str]  # 补丁ID (如 KB5012345)
    description: Optional[str]  # 描述


class PatchCacheAnalyzer:
    """补丁缓存分析器"""

    PATCH_CACHE_DIR = r"C:\Windows\Installer\$PatchCache$"

    def __init__(self):
        self.patch_path = Path(self.PATCH_CACHE_DIR)

    def is_available(self) -> bool:
        """检查补丁缓存目录是否存在"""
        return self.patch_path.exists()

    def analyze(self) -> dict:
        """
        分析补丁缓存目录，返回统计信息
        """
        result = {
            "available": self.is_available(),
            "total_size": 0,
            "total_count": 0,
            "is_migrated": False,
            "patches": [],
            "error": None
        }

        if not result["available"]:
            result["error"] = "补丁缓存目录不存在，可能已被清理"
            return result

        # 检查是否已经是 Junction (已迁移)
        try:
            attrs = os.stat(str(self.patch_path), follow_symlinks=False).st_file_attributes
            if attrs & 0x400:  # FILE_ATTRIBUTE_REPARSE_POINT
                result["is_migrated"] = True
                result["error"] = "补丁缓存已迁移到其他盘"
                return result
        except Exception:
            pass

        # 扫描目录内容
        try:
            patches = self._scan_patches()
            result["patches"] = patches
            result["total_count"] = len(patches)
            result["total_size"] = sum(p.size_bytes for p in patches)
        except Exception as e:
            logger.error(f"Failed to analyze patch cache: {e}")
            result["error"] = f"扫描失败: {str(e)}"

        return result

    def _scan_patches(self) -> List[PatchInfo]:
        """扫描并解析补丁信息"""
        patches = []

        try:
            for entry in os.scandir(self.patch_path):
                if entry.is_dir():
                    # 子目录通常是 GUID 命名的补丁
                    patch_info = self._parse_patch_folder(entry)
                elif entry.is_file():
                    # 直接文件
                    patch_info = self._parse_patch_file(entry)

                if patch_info:
                    patches.append(patch_info)

        except PermissionError as e:
            logger.warning(f"Permission denied scanning patch cache: {e}")
        except Exception as e:
            logger.error(f"Error scanning patch cache: {e}")

        # 按大小排序
        patches.sort(key=lambda x: x.size_bytes, reverse=True)
        return patches

    def _parse_patch_folder(self, entry: os.DirEntry) -> Optional[PatchInfo]:
        """解析补丁文件夹"""
        size = self._get_folder_size(entry.path)
        mtime = datetime.fromtimestamp(entry.stat().st_mtime)

        # 尝试从文件夹名提取补丁ID
        patch_id = self._extract_patch_id(entry.name)

        # 尝试获取描述
        description = self._get_patch_description(entry.path)

        return PatchInfo(
            name=entry.name,
            path=entry.path,
            size_bytes=size,
            modified_time=mtime,
            patch_id=patch_id,
            description=description
        )

    def _parse_patch_file(self, entry: os.DirEntry) -> Optional[PatchInfo]:
        """解析补丁文件"""
        try:
            stat = entry.stat()
            return PatchInfo(
                name=entry.name,
                path=entry.path,
                size_bytes=stat.st_size,
                modified_time=datetime.fromtimestamp(stat.st_mtime),
                patch_id=None,
                description=self._get_file_description(entry.name)
            )
        except Exception:
            return None

    def _get_folder_size(self, folder_path: str) -> int:
        """递归计算文件夹大小"""
        total = 0
        try:
            for entry in os.scandir(folder_path):
                if entry.is_file():
                    try:
                        total += entry.stat().st_size
                    except:
                        pass
                elif entry.is_dir():
                    total += self._get_folder_size(entry.path)
        except:
            pass
        return total

    def _extract_patch_id(self, name: str) -> Optional[str]:
        """
        尝试从名称中提取补丁ID
        例如: "KB5012345_security_update" -> "KB5012345"
        """
        import re
        # 匹配 KB + 数字 格式
        match = re.search(r'(KB\d+)', name, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return None

    def _get_patch_description(self, folder_path: str) -> str:
        """尝试获取补丁描述"""
        # 检查文件夹内的文件类型
        try:
            files = os.listdir(folder_path)
            if not files:
                return "空目录"

            ext_counts = {}
            for f in files:
                _, ext = os.path.splitext(f)
                ext = ext.lower() if ext else ".unknown"
                ext_counts[ext] = ext_counts.get(ext, 0) + 1

            # 根据文件类型推断描述
            if '.msp' in ext_counts:
                return f"MSI 补丁包 ({ext_counts['.msp']} 个文件)"
            elif '.cab' in ext_counts:
                return f"Windows 补丁档案 ({ext_counts['.cab']} 个文件)"
            else:
                ext_list = ', '.join(f"{k}:{v}" for k, v in ext_counts.items())
                return f"系统组件缓存 ({ext_list})"

        except Exception:
            return "系统组件"

    def _get_file_description(self, filename: str) -> str:
        """根据文件名获取描述"""
        lower = filename.lower()

        if '.msp' in lower:
            return "Windows Installer 补丁"
        elif '.cab' in lower:
            return "Windows 补丁档案"
        elif '.xml' in lower:
            return "补丁元数据"
        else:
            return "系统缓存文件"

    def get_cleanup_recommendations(self) -> dict:
        """
        获取清理建议
        """
        analysis = self.analyze()

        if not analysis["available"] or analysis["is_migrated"]:
            return {"can_cleanup": False, "reason": analysis.get("error", "无法分析")}

        patches = analysis["patches"]
        if not patches:
            return {"can_cleanup": True, "message": "没有可清理的补丁", "savings": 0}

        # 按时间分组
        now = datetime.now()
        old_patches = []  # 超过1年的
        medium_patches = []  # 3-12个月的
        recent_patches = []  # 3个月内的

        for p in patches:
            age_days = (now - p.modified_time).days
            if age_days > 365:
                old_patches.append(p)
            elif age_days > 90:
                medium_patches.append(p)
            else:
                recent_patches.append(p)

        old_size = sum(p.size_bytes for p in old_patches)
        medium_size = sum(p.size_bytes for p in medium_patches)

        return {
            "can_cleanup": True,
            "total_count": analysis["total_count"],
            "total_size": analysis["total_size"],
            "recommendations": {
                "safe": {
                    "description": "可安全清理 (超过1年)",
                    "count": len(old_patches),
                    "size": old_size,
                    "patches": old_patches[:10]  # 只返回前10个展示
                },
                "caution": {
                    "description": "建议保留 3-12个月",
                    "count": len(medium_patches),
                    "size": medium_size,
                    "patches": medium_patches[:5]
                },
                "recent": {
                    "description": "近期补丁 (建议保留)",
                    "count": len(recent_patches),
                    "size": sum(p.size_bytes for p in recent_patches)
                }
            }
        }


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


if __name__ == "__main__":
    analyzer = PatchCacheAnalyzer()
    result = analyzer.analyze()

    print(f"可用: {result['available']}")
    print(f"已迁移: {result['is_migrated']}")
    print(f"总大小: {format_size(result['total_size'])}")
    print(f"补丁数量: {result['total_count']}")

    if result['patches']:
        print("\n前10个最大的补丁:")
        for p in result['patches'][:10]:
            print(f"  {p.patch_id or p.name[:30]}: {format_size(p.size_bytes)}")

    print("\n清理建议:")
    recs = analyzer.get_cleanup_recommendations()
    if recs['can_cleanup']:
        print(f"  总可清理: {format_size(recs['recommendations']['safe']['size'])}")
