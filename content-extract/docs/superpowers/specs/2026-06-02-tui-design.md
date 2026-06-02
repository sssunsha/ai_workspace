# Content Extract TUI 设计文档

> 创建日期：2026-06-02
> 范围：Textual TUI 实现（Phase 2 UI 层）
> 参考：content-extraction-tool-plan.md 第四章、第九章

---

## 一、目标

在 `content-extract`（无参数）时启动全屏 Textual TUI，替换当前的占位提示。CLI 子命令行为不变。

---

## 二、文件结构

```
content_extract/
├── ui/
│   ├── __init__.py
│   └── tui.py          ← 全部 TUI 代码
tests/
└── test_tui.py
```

`cli.py` 第 18-19 行替换：
```python
if ctx.invoked_subcommand is None:
    from .ui.tui import TUIApp
    TUIApp().run()
```

---

## 三、数据模型

```python
@dataclass
class TaskEntry:
    source: str
    source_type: str          # web / video / bilibili / ...
    status: str               # extracting / done / failed / needs_transcription
    output_file: str = ""
    error: str = ""
    extracted_at: str = ""
```

TUIApp 维护 `_tasks: list[TaskEntry]`：
- 启动时从 `./raw/.processed.json` 加载历史记录
- 新任务追加到内存列表
- 任务完成后同步 registry + 刷新面板

---

## 四、布局

```
┌─ Content Extract ─────────── ~/my-project ────────────────────┐
├───────────────────────────────────────────────────────────────┤
│  ┌── 添加来源（60%）──────────────┐  ┌── 处理队列（40%）────┐  │
│  │  URL / 路径: [Input          ] │  │ ✓ web__example.md    │  │
│  │  类型: [自动识别      ▾]      │  │ ⟳ bili__BV123.md     │  │
│  │  [提取]  [提取并更新Wiki]      │  │ ✗ web__fail.md       │  │
│  └────────────────────────────────┘  └─────────────────────┘  │
│  ┌── 实时日志（全宽）──────────────────────────────────────┐   │
│  │  [10:32:01] 正在提取: https://...                        │   │
│  │  [10:32:04] ✓ 完成 → raw/web__example.md                │   │
│  └──────────────────────────────────────────────────────────┘   │
├───────────────────────────────────────────────────────────────┤
│  [E]提取  [R]重试  [O]打开Obsidian  [Q]退出                     │
└───────────────────────────────────────────────────────────────┘
```

---

## 五、组件设计

### TUIApp(App)

- CSS_PATH：内联 DEFAULT_CSS，无外部文件
- `BINDINGS`：q/Q 退出、r/R 重试选中失败项、o/O 打开 Obsidian
- `on_mount`：加载 registry 历史 → 填充 `_tasks` → 刷新 QueuePanel
- `log_message(msg)`：线程安全写 LogPanel，供 worker 回调使用

### AddSourcePanel(Widget)

- `Input` id=url-input：绑定 `on_input_changed`，触发类型自动识别
- `Select` id=type-select：选项为 `自动识别/web/video/ebook/code/docs/github/article`
- `Button` id=btn-extract：点击发 `ExtractRequested`
- `Button` id=btn-extract-wiki：点击发 `ExtractRequested(update_wiki=True)`

### QueuePanel(Widget)

- `DataTable` id=queue-table：列 `[状态, 来源, 输出文件, 时间]`
- `refresh_table(tasks)`：清空并重绘，状态图标映射：
  - extracting → `⟳`，done → `✓`，failed → `✗`，needs_transcription → `⏳`
- 失败行高亮红色（通过 CSS class）

### LogPanel(Widget)

- `RichLog` id=log：`highlight=True, markup=True, auto_scroll=True`
- `write(msg)`：追加带时间戳的日志行

### WikiModal(ModalScreen)

- 占位弹窗，显示「Wiki 更新功能将在 Skill 实现后可用」
- 两个按钮：确认（关闭弹窗）/ 取消

---

## 六、消息定义

```python
class ExtractRequested(Message):
    def __init__(self, source: str, source_type: str, update_wiki: bool = False):
        ...

class ExtractDone(Message):
    def __init__(self, source: str, success: bool, output_file: str = "", error: str = ""):
        ...
```

---

## 七、Worker 线程方案

```python
@work(thread=True)
def _run_extract(self, source: str, source_type: str) -> None:
    def on_progress(msg: str):
        self.app.call_from_thread(self.app.log_message, msg)

    cfg = ExtractConfig(output_dir=Path("./raw"), cookies=self._cookies)

    if source_type == "web":
        from .extractors.web import WebExtractor
        extractor = WebExtractor(config=cfg, on_progress=on_progress)
        out = extractor.extract(source)
    elif source_type in ("video", "bilibili"):
        from .extractors import auto_detect_video
        out = auto_detect_video(source, config=cfg)
    else:
        self.post_message(ExtractDone(source=source, success=False, error=f"类型 {source_type} 尚未实现"))
        return

    self.post_message(ExtractDone(source=source, success=True, output_file=str(out)))
```

---

## 八、类型自动识别

```python
def detect_source_type(source: str) -> str:
    if source.startswith(("http://", "https://")):
        if "bilibili.com" in source or "b23.tv" in source:
            return "video"
        if "github.com" in source:
            return "github"
        return "article"
    p = Path(source)
    if p.suffix in {".epub", ".pdf", ".mobi"}:
        return "ebook"
    if p.is_dir():
        if (p / "package.json").exists() or (p / "pyproject.toml").exists():
            return "code"
        return "docs"
    return "docs"
```

`on_input_changed` 时调用此函数，自动更新 Select 组件的值（仅当用户选择「自动识别」时）。

---

## 九、测试策略

`tests/test_tui.py` 使用 `textual.testing.Pilot`，所有 `extract()` 调用用 `unittest.mock.patch` mock：

1. `test_app_launches`：app 启动后按 q 能正常退出
2. `test_input_url_detection`：输入 bilibili URL → Select 值变为 video
3. `test_queue_empty_on_start`：初始 DataTable 行数为 0（无 registry 文件时）
4. `test_log_panel_exists`：DOM 中存在 `#log` 节点
5. `test_keyboard_quit`：按 Q 不抛异常

---

## 十、依赖

```
textual>=0.61.0
```

加入 `pyproject.toml` optional-dependencies `[ui]`，`requirements.txt` 新增 `# ui` 分组。

---

## 十一、不做的事

- 不实现 Streamlit Web UI
- 不修改任何 extractor 代码
- Wiki 管理只有「打开 Obsidian」+ 占位弹窗
- 配置面板留空（Phase 4）
