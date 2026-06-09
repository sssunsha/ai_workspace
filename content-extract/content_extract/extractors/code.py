from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Callable

from .base import BaseExtractor, ExtractConfig
from ..registry import Registry
from ..utils.frontmatter import write_frontmatter_file


_SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".cache", ".idea", ".vscode",
    "coverage", ".nyc_output", ".next", ".nuxt",
    ".angular", ".turbo", ".expo",
}

_TEXT_EXTS = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".py", ".java", ".kt", ".swift", ".go", ".rs",
    ".c", ".cpp", ".h", ".hpp",
    ".html", ".css", ".scss", ".less",
    ".json", ".yaml", ".yml", ".toml", ".ini",
    ".md", ".mdx", ".txt", ".rst",
    ".sh", ".bash", ".zsh",
    ".xml", ".graphql", ".proto",
    ".sql",
}

# 配置文件（overview 模式必包含）
_CONFIG_FILES = {
    "package.json", "pyproject.toml", "Cargo.toml", "go.mod",
    "pom.xml", "build.gradle", "setup.py", "setup.cfg",
    "nx.json", "angular.json", "tsconfig.json", "jest.config.js",
    "jest.config.ts", ".eslintrc.json", "eslint.config.mjs",
}

# priority 模式：测试文件
_TEST_PATTERNS = {".test.ts", ".test.tsx", ".test.js", ".spec.ts", ".spec.tsx", ".spec.js"}
_TEST_DIRS = {"test", "tests", "__tests__", "e2e", "spec"}

# priority 模式：接口/类型定义
_TYPE_PATTERNS = {"types.ts", "interfaces.ts", "models.ts", "schema.ts",
                  "types.py", "models.py", "interfaces.py"}
_DTS_EXT = ".d.ts"

_MAX_FILE_BYTES = 500_000

# 架构层关键词映射（目录名启发式识别）
_ARCH_LAYERS: dict[str, set[str]] = {
    "API / 路由层":     {"api", "apis", "routes", "router", "routers", "controllers",
                         "handlers", "endpoints", "rest", "graphql"},
    "业务逻辑层":       {"services", "service", "usecases", "usecase", "use-cases",
                         "domain", "core", "business", "application", "app"},
    "数据访问层":       {"repositories", "repository", "repos", "models", "model",
                         "db", "database", "databases", "store", "stores",
                         "persistence", "dao", "orm"},
    "UI / 展示层":      {"components", "component", "views", "view", "pages", "page",
                         "screens", "screen", "ui", "widgets", "widget", "templates"},
    "工具 / 基础设施层": {"utils", "util", "helpers", "helper", "shared", "common",
                         "lib", "libs", "infrastructure", "infra", "config",
                         "configs", "middleware", "interceptors"},
}

# import 语句提取正则（TypeScript/JavaScript 和 Python）
_TS_IMPORT_RE = re.compile(r"""from\s+['"]([^'"]+)['"]""")
_PY_IMPORT_RE = re.compile(r"""^(?:from\s+(\S+)\s+import|import\s+(\S+))""", re.MULTILINE)


def _repo_slug(path: Path) -> str:
    return path.name


def _is_test_file(rel: Path) -> bool:
    name = rel.name
    if any(name.endswith(p) for p in _TEST_PATTERNS):
        return True
    if any(part in _TEST_DIRS for part in rel.parts[:-1]):
        return True
    if name.startswith("test_") or name.endswith("_test.py"):
        return True
    return False


def _is_type_file(rel: Path) -> bool:
    if rel.suffix == _DTS_EXT or rel.name.endswith(_DTS_EXT):
        return True
    return rel.name in _TYPE_PATTERNS


def _is_entry_file(rel: Path) -> bool:
    name = rel.stem
    return name in ("index", "main", "app", "server", "cli") and len(rel.parts) <= 3


def _collect_all(root: Path) -> list[Path]:
    """全量收集所有文本文件，跳过忽略目录和超大文件。"""
    results: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if fpath.suffix.lower() not in _TEXT_EXTS:
                continue
            try:
                size = fpath.stat().st_size
            except OSError:
                continue
            if size > _MAX_FILE_BYTES:
                continue
            results.append(fpath)
    return results


def _build_tree(root: Path) -> str:
    """生成 3 层深度的目录树（跳过忽略目录）。"""
    lines: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")
        )
        rel_dir = Path(dirpath).relative_to(root)
        depth = len(rel_dir.parts)
        if depth > 2:
            dirnames.clear()
            continue
        indent = "  " * depth
        if depth == 0:
            lines.append(f"{root.name}/")
        else:
            lines.append(f"{indent}{rel_dir.name}/")
        for fname in sorted(filenames):
            fpath = Path(dirpath) / fname
            if fpath.suffix.lower() in _TEXT_EXTS or fname in _CONFIG_FILES:
                lines.append(f"{indent}  {fname}")
    return "\n".join(lines)


def _read_config_files(root: Path) -> list[str]:
    """读取项目配置文件，返回各文件的 Markdown 代码块列表。"""
    blocks: list[str] = []
    for cfg_name in sorted(_CONFIG_FILES):
        cfg_path = root / cfg_name
        if cfg_path.exists() and cfg_path.stat().st_size < 100_000:
            try:
                text = cfg_path.read_text(encoding="utf-8", errors="replace")
                ext = cfg_path.suffix.lstrip(".")
                blocks.append(f"### {cfg_name}\n\n```{ext}\n{text}\n```")
            except Exception:
                pass
    return blocks


def _read_readme(root: Path) -> str:
    """读取 README 文件内容，找不到返回空字符串。"""
    for readme_name in ("README.md", "README.rst", "README.txt", "README"):
        readme_path = root / readme_name
        if readme_path.exists():
            try:
                return readme_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass
    return ""


def _git_log(root: Path) -> str:
    """获取最近 30 条 git log，失败静默返回空。"""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "log", "--oneline", "-30"],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def _git_hotfiles(root: Path) -> list[tuple[str, int]]:
    """获取近 6 个月高频变更文件，返回 [(filepath, count), ...] 按次数降序。"""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "log", "--since=6 months ago",
             "--name-only", "--format="],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        from collections import Counter
        counts = Counter(f for f in result.stdout.splitlines() if f.strip())
        return counts.most_common(20)
    except Exception:
        return []


def _top_level_dirs(root: Path) -> list[Path]:
    return [d for d in root.iterdir()
            if d.is_dir() and d.name not in _SKIP_DIRS and not d.name.startswith(".")]


def _second_level_dirs(root: Path) -> list[Path]:
    result: list[Path] = []
    for top in _top_level_dirs(root):
        result.extend(
            d for d in top.iterdir()
            if d.is_dir() and d.name not in _SKIP_DIRS and not d.name.startswith(".")
        )
    return result


def _detect_arch_layers(root: Path) -> str:
    """启发式识别项目架构层（基于顶层和次级目录名），返回 Markdown 段落。"""
    found: dict[str, list[str]] = {}
    for d in _top_level_dirs(root) + _second_level_dirs(root):
        low = d.name.lower()
        for layer, keywords in _ARCH_LAYERS.items():
            if low in keywords:
                rel = str(d.relative_to(root))
                found.setdefault(layer, []).append(f"`{rel}`")

    if not found:
        return "（目录命名未匹配到已知架构层，建议手动补充）"
    lines = [f"- **{layer}**: {', '.join(dirs)}" for layer, dirs in found.items()]
    return "\n".join(lines)


def _build_reading_path(
    root: Path,
    hotfiles: list[tuple[int, str]],
    entry_files: list[Path],
) -> str:
    """生成推荐阅读路径（5步），基于配置文件、入口、热力图。"""
    steps: list[str] = []

    # Step 1：配置文件
    cfg_found = [f for f in _CONFIG_FILES if (root / f).exists()]
    if cfg_found:
        cfg_list = "、".join(f"`{f}`" for f in cfg_found[:4])
        steps.append(f"**Step 1 — 了解项目全貌**：读 {cfg_list}，确认技术栈、依赖版本、可用脚本。")
    else:
        steps.append("**Step 1 — 了解项目全貌**：读根目录配置文件，确认技术栈和依赖。")

    # Step 2：入口文件
    if entry_files:
        entries = "、".join(f"`{f.relative_to(root)}`" for f in entry_files[:3])
        steps.append(f"**Step 2 — 找到系统启动点**：读入口文件 {entries}，追踪应用如何启动。")
    else:
        steps.append("**Step 2 — 找到系统启动点**：在根目录和 `src/` 下查找 `main.*` / `index.*` / `app.*`。")

    # Step 3：架构核心（热力图 Top 3）
    if hotfiles:
        top3 = "、".join(f"`{f}`" for _, f in hotfiles[:3])
        steps.append(
            f"**Step 3 — 定位系统核心**：读高频变更文件 {top3}。"
            "这些是系统最复杂、最活跃的区域，也是最需要先理解的部分。"
        )
    else:
        steps.append("**Step 3 — 定位系统核心**：读架构层中业务逻辑层的核心文件。")

    # Step 4：测试文件
    steps.append(
        "**Step 4 — 确认系统契约**：读测试文件（`*.spec.ts` / `*.test.ts` / `test_*.py`）。"
        "测试是唯一明确说明「系统应该做什么、不应该做什么」的文档。"
    )

    # Step 5：类型/接口定义
    steps.append(
        "**Step 5 — 理解数据结构**：读类型定义文件（`*.d.ts` / `types.ts` / `models.py`）。"
        "接口边界是模块间协作的契约，理解它才能安全地修改代码。"
    )

    return "\n\n".join(steps)


def _extract_imports(fpath: Path) -> list[str]:
    """从单个文件提取 import 目标，返回原始 import 路径列表。"""
    try:
        content = fpath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    ext = fpath.suffix.lower()
    if ext in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}:
        return _TS_IMPORT_RE.findall(content)
    if ext == ".py":
        matches = _PY_IMPORT_RE.findall(content)
        return [m[0] or m[1] for m in matches if m[0] or m[1]]
    return []


def _write_file(
    fpath: Path,
    rel: Path,
    out_dir: Path,
    slug: str,
    registry: Registry,
    force: bool,
    log: Callable[[str], None],
) -> bool:
    """写入单个源文件到 raw/。返回是否实际写入（跳过已处理返回 False）。"""
    source_key = str(fpath)
    if not force and registry.is_processed(source_key):
        return False
    try:
        raw = fpath.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        log(f"  读取失败: {rel} — {e}")
        return False

    rel_slug = str(rel).replace(os.sep, "__").replace("/", "__")
    out_file = out_dir / f"{rel_slug}.md"
    lang = fpath.suffix.lstrip(".")
    content = f"# {rel}\n\n```{lang}\n{raw}\n```\n"
    content_hash = write_frontmatter_file(
        path=out_file,
        content=content,
        source=source_key,
        type="code",
        extra_fields={"repo": slug, "rel_path": str(rel)},
    )
    registry.mark(source_key, "done", output_file=f"{slug}/{out_file.name}", content_hash=content_hash)
    return True


def _validate_source(source: str, mode: str) -> Path:
    """校验 source 路径和 mode，合法时返回 resolved Path，否则 raise ValueError。"""
    repo_path = Path(source).expanduser().resolve()
    if not repo_path.exists():
        raise ValueError(f"路径不存在: {repo_path}")
    if not repo_path.is_dir():
        raise ValueError(f"路径不是目录: {repo_path}")
    if mode not in ("overview", "priority", "full"):
        raise ValueError(f"不支持的模式: {mode}，可选 overview / priority / full")
    return repo_path


class CodeExtractor(BaseExtractor):
    """
    提取本地代码工程目录。支持三种模式：

    overview（默认）
        输出 __overview.md：目录树（3层）、架构层识别、推荐阅读路径、
        配置文件全文、README、git log（最近30条）、git 热力图（Top 20）。
        适合快速建立全局认知，不写入任何源代码文件。

    priority
        overview 基础上，额外提取：
        - 测试文件（*.test.ts / *.spec.ts / test_*.py 等，最多 80 个）
        - 接口/类型定义（*.d.ts / types.ts / models.py 等，最多 50 个）
        - 入口文件（index.ts / main.py 等，仅前 3 层，最多 20 个）
        同时生成 __imports.json：已提取文件的 import 依赖关系图。
        适合准备修改代码前建立"系统契约"认知。

    full
        全量提取所有文本文件（增量跳过已处理），同时生成 __imports.json。
        适合深度阅读。
    """

    @property
    def supported_domains(self) -> list[str]:
        return []

    def extract(self, source: str, mode: str = "overview") -> Path:
        """
        source: 本地目录路径。
        mode:   "overview" | "priority" | "full"
        返回 overview 文件路径。
        """
        repo_path = _validate_source(source, mode)

        slug = _repo_slug(repo_path)
        out_dir = self.config.output_dir / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        registry = Registry(self.config.output_dir / ".processed.json")

        self.log(f"提取模式: {mode}  目录: {repo_path}")

        hotfiles = _git_hotfiles(repo_path)
        overview_file = self._write_overview(repo_path, slug, out_dir, registry, hotfiles)

        if mode == "overview":
            self.log("✓ overview 模式完成（如需代码细节，选择 priority 或 full 模式）")
            return overview_file

        # priority / full 模式：收集源文件
        all_files = _collect_all(repo_path)
        self.log(f"  扫描到 {len(all_files)} 个源文件")

        if mode == "priority":
            selected = self._select_priority(repo_path, all_files)
            self.log(
                f"  优先级筛选: 测试 {selected['test']} + "
                f"类型 {selected['type']} + "
                f"入口 {selected['entry']} = {selected['total']} 个文件"
            )
            files_to_write = selected["files"]
        else:
            files_to_write = all_files

        written = sum(
            _write_file(f, f.relative_to(repo_path), out_dir, slug,
                        registry, self.config.force, self.log)
            for f in files_to_write
        )
        skipped = len(files_to_write) - written
        self.log(f"✓ 写入 {written} 个文件（跳过已处理 {skipped} 个）")

        # 生成 __imports.json（依赖关系图）
        self._write_imports_json(repo_path, files_to_write, out_dir)

        return overview_file

    def _write_overview(
        self,
        repo_path: Path,
        slug: str,
        out_dir: Path,
        registry: Registry,
        hotfiles: list[tuple[str, int]],
    ) -> Path:
        """生成 __overview.md：架构层 + 推荐阅读路径 + 目录树 + 配置 + README + git 信息。"""
        sections: list[str] = [f"# {slug} — 项目概览\n"]

        sections.append(f"## 架构层识别\n\n{_detect_arch_layers(repo_path)}")

        entry_files = [f for f in _collect_all(repo_path) if _is_entry_file(f.relative_to(repo_path))][:5]
        sections.append(f"## 推荐阅读路径\n\n{_build_reading_path(repo_path, hotfiles, entry_files)}")

        sections.append("## 目录结构（前 3 层）\n\n```\n" + _build_tree(repo_path) + "\n```")

        cfg_blocks = _read_config_files(repo_path)
        if cfg_blocks:
            sections.append("## 配置文件\n\n" + "\n\n".join(cfg_blocks))

        readme = _read_readme(repo_path)
        if readme:
            sections.append(f"## README\n\n{readme}")

        git_log = _git_log(repo_path)
        if git_log:
            sections.append(f"## 最近 30 条提交\n\n```\n{git_log}\n```")

        if hotfiles:
            hotfiles_str = "\n".join(f"  {c:3d}x  {f}" for f, c in hotfiles)
            sections.append(f"## 高频变更文件（近 6 个月 Top 20）\n\n```\n{hotfiles_str}\n```")

        overview_file = out_dir / "__overview.md"
        content_hash = write_frontmatter_file(
            path=overview_file,
            content="\n\n".join(sections),
            source=str(repo_path),
            type="code",
            extra_fields={"repo": slug, "mode": "overview"},
        )
        registry.mark(str(repo_path), "done",
                      output_file=f"{slug}/__overview.md",
                      content_hash=content_hash)
        self.log(f"  已生成 overview: {overview_file.name}")
        return overview_file

    def _write_imports_json(
        self,
        repo_path: Path,
        files: list[Path],
        out_dir: Path,
    ) -> None:
        """生成 __imports.json：已提取文件的 import 关系图。"""
        graph: dict[str, list[str]] = {}
        for fpath in files:
            if fpath.suffix.lower() not in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".py"}:
                continue
            rel = str(fpath.relative_to(repo_path))
            imports = _extract_imports(fpath)
            if imports:
                graph[rel] = imports

        if not graph:
            return

        out_file = out_dir / "__imports.json"
        out_file.write_text(
            json.dumps(graph, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.log(f"  已生成 imports 关系图: {out_file.name}（{len(graph)} 个文件）")

    def _select_priority(self, repo_path: Path, all_files: list[Path]) -> dict:
        tests, types, entries = [], [], []
        for fpath in all_files:
            rel = fpath.relative_to(repo_path)
            if _is_test_file(rel):
                tests.append(fpath)
            elif _is_type_file(rel):
                types.append(fpath)
            elif _is_entry_file(rel):
                entries.append(fpath)

        files = tests[:80] + types[:50] + entries[:20]
        return {
            "test": len(tests[:80]),
            "type": len(types[:50]),
            "entry": len(entries[:20]),
            "total": len(files),
            "files": files,
        }
