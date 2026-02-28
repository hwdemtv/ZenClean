"""
ZenClean 云端 AI 占位符 (第一阶段)

第三阶段升级路径：新建 ai/cloud_engine.py，实现相同的 query() 签名，
在 local_engine.dispatch() 中将 cloud_mock 替换为 cloud_engine，其余零改动。
"""


def query(path: str) -> dict:
    """第一阶段只做占位，统一对未知项不予操作。"""
    return {
        "risk_level": "UNKNOWN",
        "ai_advice": "云端分析功能将在 VIP 版本开放",
    }


def is_mock() -> bool:
    """供调试/测试判断当前是否处于 mock 模式。"""
    return True
