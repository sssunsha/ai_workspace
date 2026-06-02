"""URL 语言识别与过滤工具。

仅支持中文（zh 系列）和英文（en 系列），检测到其他语言时抛出 ValueError。
检测优先级：路径前缀 > 子域名 > Query 参数 > 无信号（默认英文）。
"""
from __future__ import annotations

import re
from urllib.parse import urlparse, parse_qs

# 匹配路径语言段：/zh/、/zh-CN/、/en-US/、/zh-Hans/ 等
_LANG_PATH_RE = re.compile(r"^/([a-zA-Z]{2,3}(?:-[a-zA-Z]{2,8})?)(?:/|$)")

# zh 系列全部归一化为 "zh"
_ZH_CODES = frozenset({
    "zh", "zh-cn", "zh-tw", "zh-hk", "zh-sg", "zh-mo",
    "zh-hans", "zh-hant",
})

# en 系列全部归一化为 "en"
_EN_CODES = frozenset({
    "en", "en-us", "en-gb", "en-au", "en-ca", "en-nz",
    "en-ie", "en-in", "en-sg", "en-za", "en-ph",
})

# 常见非语言子域名，不触发语言检测
_SAFE_SUBDOMAINS = frozenset({
    "www", "api", "static", "cdn", "blog", "docs", "mail", "app",
    "dev", "staging", "test", "beta", "alpha", "m", "mobile",
    "admin", "dashboard", "auth", "login", "support", "help",
    "shop", "store", "news", "media", "assets", "img", "images",
    "video", "download", "search", "s3", "files",
})

# 用于 Query 参数检测的键名
_LANG_QUERY_KEYS = ("lang", "language", "locale", "l")


def _normalize(raw: str) -> str | None:
    """将原始语言代码归一化为 'zh' 或 'en'，不支持返回 None。"""
    code = raw.lower()
    if code in _ZH_CODES:
        return "zh"
    if code in _EN_CODES:
        return "en"
    return None


def detect_lang(url: str) -> str:
    """从 URL 检测内容语言，返回 'zh' 或 'en'。

    检测优先级：路径前缀 > 子域名 > Query 参数 > 无信号（默认英文）。

    Raises:
        ValueError: 检测到不支持的语言（仅支持 zh / en）。
    """
    parsed = urlparse(url)

    # 1. 路径前缀：/zh/、/en-US/ 等
    m = _LANG_PATH_RE.match(parsed.path)
    if m:
        code = m.group(1)
        lang = _normalize(code)
        if lang is None:
            raise ValueError(
                f"不支持的语言 '{code}'，当前仅支持中文（zh 系列）和英文（en 系列）：{url}"
            )
        return lang

    # 2. 子域名：zh.example.com / en.example.com
    host = parsed.netloc.split(":")[0]
    parts = host.split(".")
    if len(parts) >= 3:
        sub = parts[0].lower()
        # 只检测 2-3 位字母的经典 ISO 语言代码，忽略常见非语言子域名
        if sub not in _SAFE_SUBDOMAINS and re.fullmatch(r"[a-z]{2,3}", sub):
            lang = _normalize(sub)
            if lang is not None:
                return lang
            raise ValueError(
                f"不支持的语言子域名 '{sub}'，当前仅支持中文（zh 系列）和英文（en 系列）：{url}"
            )

    # 3. Query 参数：?lang=zh、?language=en、?locale=zh-CN
    if parsed.query:
        params = parse_qs(parsed.query, keep_blank_values=False)
        for key in _LANG_QUERY_KEYS:
            if key in params:
                code = params[key][0]
                lang = _normalize(code)
                if lang is None:
                    raise ValueError(
                        f"不支持的语言参数 '{key}={code}'，当前仅支持中文（zh 系列）和英文（en 系列）：{url}"
                    )
                return lang

    # 4. 无语言信号 → 默认英文
    return "en"


def should_follow(link_url: str, seed_lang: str) -> bool:
    """整站爬取时判断是否应跟进某个内链。

    规则：链接语言与 seed_lang 一致则跟进，否则静默跳过。
    遇到不支持的语言链接也只是跳过，不抛异常。
    """
    try:
        link_lang = detect_lang(link_url)
        return link_lang == seed_lang
    except ValueError:
        # 不支持的语言链接静默跳过，不影响整体爬取
        return False
