"""
ZenClean 本地 AI 规则引擎

读取 config/file_kb.json，对输入路径进行正则规则匹配，
返回风险等级、分类、AI 建议与默认勾选状态。

规则按 JSON 中的顺序依次匹配，第一个命中的规则即为最终结果。
未命中任何规则时由 dispatch() 路由至 cloud_mock（第一阶段返回 UNKNOWN）。

公开 API（供 scanner.py 调用）：
    dispatch(path, size_bytes) -> NodeDict   # 统一调度入口
    sanitize_path(path)        -> str        # 路径脱敏（云端上报前调用）
    reload_rules()                           # 热重载规则库
"""

import json
import os
import re
import time
from typing import TypedDict

from config.settings import FILE_KB_PATH, USER_DOWNLOADS_DIR
from core import whitelist


# ── 返回结构 ──────────────────────────────────────────────────────────────────

class NodeDict(TypedDict):
    path: str
    size_bytes: int
    risk_level: str       # LOW | MEDIUM | HIGH | CRISIS | UNKNOWN
    category: str
    is_checked: bool
    ai_advice: str
    is_whitelisted: bool
    scan_ts: float


# ── 规则加载 ──────────────────────────────────────────────────────────────────

class _Rule(TypedDict):
    id: str
    pattern: str
    risk_level: str
    category: str
    ai_advice: str
    is_checked_default: bool


def _load_rules() -> list[tuple[re.Pattern, _Rule]]:
    """加载并编译 file_kb.json 中的所有规则，返回 (compiled_pattern, rule) 列表。"""
    with open(FILE_KB_PATH, encoding="utf-8") as f:
        kb = json.load(f)

    # 生成动态目录的正则（处理含有特殊字符的路径）
    # 注意尾部加上双反斜杠以确保匹配的是目录内文件
    downloads_regex = "^" + re.escape(USER_DOWNLOADS_DIR) + r"\\"

    compiled: list[tuple[re.Pattern, _Rule]] = []
    for rule in kb["rules"]:
        pat_str = rule["pattern"]
        
        # 动态替换特定 category 的正则以支持用户迁移的系统目录
        if rule.get("category") == "downloads":
            pat_str = downloads_regex
            
        pattern = re.compile(pat_str, re.IGNORECASE)
        compiled.append((pattern, rule))
    return compiled


# 模块级缓存：规则只加载一次
_RULES: list[tuple[re.Pattern, _Rule]] = _load_rules()

# CRISIS 默认回复（白名单命中时使用）
_CRISIS_ADVICE = "系统核心文件，白名单守卫已拦截，禁止任何清理操作。"

# 脱敏替换表：将真实用户名/用户目录替换为占位符
# 顺序重要：越具体的模式越靠前
_SANITIZE_PATTERNS: list[tuple[re.Pattern, str]] = [
    # C:\Users\<真实用户名>\ → C:\Users\%USERNAME%\
    (re.compile(r"(?i)^([A-Za-z]:\\Users\\)[^\\]+\\"), r"\1%USERNAME%\\"),
    # C:\Documents and Settings\<用户名>\ （XP 遗留）
    (re.compile(r"(?i)^([A-Za-z]:\\Documents and Settings\\)[^\\]+\\"), r"\1%USERNAME%\\"),
]


# ── 路径脱敏 ──────────────────────────────────────────────────────────────────

def sanitize_path(path: str) -> str:
    """
    对路径字符串进行脱敏处理，剥除真实用户名等身份标识。
    结果仅用于发送至云端 API，本地存储/日志仍使用原始路径。

    例：
        C:\\Users\\张三\\AppData\\...
        → C:\\Users\\%USERNAME%\\AppData\\...
    """
    result = path
    for pattern, replacement in _SANITIZE_PATTERNS:
        result = pattern.sub(replacement, result, count=1)
    return result


# ── 本地规则引擎（内部） ──────────────────────────────────────────────────────

def analyze(path: str, size_bytes: int = 0) -> NodeDict:
    """
    对单个路径执行本地规则匹配，返回 NodeDict。
    UNKNOWN 路径不在此函数内处理，由 dispatch() 路由至 cloud_mock。

    Args:
        path:       文件或目录的绝对路径字符串。
        size_bytes: 文件大小（字节），由 scanner.py 传入；引擎本身不做 IO。
    """
    # ── 最高优先级：白名单守卫 ────────────────────────────────────────────────
    if whitelist.is_protected(path):
        return NodeDict(
            path=path,
            size_bytes=size_bytes,
            risk_level="CRISIS",
            category="protected",
            is_checked=False,
            ai_advice=_CRISIS_ADVICE,
            is_whitelisted=True,
            scan_ts=time.time(),
        )

    # ── 规则引擎匹配 ──────────────────────────────────────────────────────────
    for pattern, rule in _RULES:
        if pattern.search(path):
            return NodeDict(
                path=path,
                size_bytes=size_bytes,
                risk_level=rule["risk_level"],
                category=rule["category"],
                is_checked=False,  # 用户偏好：扫描完后默认不勾选，由用户自主决定
                ai_advice=rule["ai_advice"],
                is_whitelisted=False,
                scan_ts=time.time(),
            )

    # ── 未命中本地规则，标记为 UNKNOWN 交由调度器处理 ─────────────────────────
    return NodeDict(
        path=path,
        size_bytes=size_bytes,
        risk_level="UNKNOWN",
        category="unknown",
        is_checked=False,
        ai_advice="",          # dispatch() 会用 cloud_mock 的结果覆盖此字段
        is_whitelisted=False,
        scan_ts=time.time(),
    )


# ── 统一调度入口（scanner.py 唯一调用点） ────────────────────────────────────

def dispatch(path: str, size_bytes: int = 0) -> NodeDict:
    """
    统一分析调度入口，scanner.py 只调用此函数，不直接调用 analyze()。

    路由逻辑：
        1. 调用本地 analyze()。
        2. 若结果为 UNKNOWN，将脱敏路径交给 cloud_mock（第一阶段）或
           cloud_engine（第三阶段接入后替换）补充 ai_advice。
        3. 返回最终 NodeDict。

    第三阶段升级时，仅需将 cloud_mock 替换为真实 cloud_engine，
    此函数签名与调用方代码无需改动。
    """
    node = analyze(path, size_bytes)

    if node["risk_level"] == "UNKNOWN":
        # 正式接入真实云端引擎
        from ai import cloud_engine
        sanitized = sanitize_path(path)
        cloud_result = cloud_engine.query(sanitized)
        node["ai_advice"] = cloud_result["ai_advice"]
        # 第二阶段及以后，采用云模型真实的危机研判
        node["risk_level"] = cloud_result.get("risk_level", "UNKNOWN")

    return node


def reload_rules() -> None:
    """热重载规则库（供设置页"更新规则"按钮调用）。"""
    global _RULES
    _RULES = _load_rules()
