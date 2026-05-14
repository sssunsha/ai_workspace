# claude-hunter 设计文档

## 概述

claude-hunter 是 Claude Code CLI 的可视化超集工具，运行于 Mac 系统。核心定位：完整保留 CLI 原生能力，同时提供图形界面，解决操作繁琐、记忆负担重、交互割裂三大痛点。

## 技术栈

- **语言**：Python 3.8+
- **UI 框架**：PyQt6
- **CLI 驱动**：ptyprocess（PTY 伪终端，替代 QProcess）
- **打包**：pyinstaller → .app

## 项目结构

```
claud-hunter/
├── main.py
├── requirements.txt          # ptyprocess, PyQt6
├── claude-hunter.spec        # pyinstaller 配置
├── tasks/                    # 用户自定义任务
│   ├── 代码审查.json
│   └── 查bug.md
├── assets/
│   └── icon.icns
└── app/
    ├── ui/
    │   ├── main_window.py    # QMainWindow + QSplitter
    │   ├── sidebar.py        # 左侧面板
    │   ├── chat_panel.py     # 右侧主区域
    │   └── autocomplete.py  # 补全下拉控件
    └── core/
        ├── pty_worker.py     # QThread + ptyprocess
        ├── skill_scanner.py  # 扫描本地 skill
        └── task_loader.py    # 加载 tasks/ 配置
```

## 架构

### 线程模型

- **UI 线程**：所有 Qt widgets，只做渲染，不阻塞
- **PtyWorker（QThread）**：持续读取 PTY 输出，通过 `pyqtSignal(str)` 发给 UI 线程，绝不直接操作 widget

### 数据流

```
用户输入 Enter → input_box → PtyWorker.write(stdin)
                                      ↓
PTY stdout → PtyWorker.read() → strip_ansi → output_received(signal)
                                                     ↓
                                           chat_panel.append_output()
```

## 模块设计

### `app/core/pty_worker.py`

```
PtyWorker(QThread)
├── output_received(str)   # 剥离 ANSI 的输出
├── process_finished()
├── process_error(str)
├── spawn: ptyprocess.PtyProcess.spawn(['claude'], env=os.environ)
├── run(): read(4096) → decode UTF-8 → strip_ansi → emit
├── write(text): process.write(text.encode()) + \n
└── restart(): terminate → re-spawn
```

ANSI 剥离：正则 `\x1b\[[0-9;]*[mGKHF]` 移除所有颜色/光标控制码，保留换行和制表符。

`CLAUDE_CLI = "claude"` 常量在 `main_window.py` 顶部，用户可修改。

### `app/core/skill_scanner.py`

扫描路径：
- `~/.claude/plugins/`
- `~/.claude/plugins/cache/`

提取各路径下 `skills/` 子目录的文件夹名作为 skill 名，去重。内置 CLI 命令列表：`/help /new /clear /review /cost /compact /config`。

### `app/core/task_loader.py`

```python
@dataclass
class Task:
    name: str
    prompt: str
    cli_args: str = ""
```

- JSON 格式：解析 `name`、`prompt`、`cli_args` 字段
- MD 格式：文件名（去扩展名）为任务名，文件全文为 prompt
- 解析失败：跳过该文件，记录警告

**任务执行行为：**
- 有 `cli_args`：重启 PTY 附加参数，然后发送 prompt
- 无 `cli_args`：直接向当前会话发送 prompt

### `app/ui/main_window.py`

```
MainWindow (初始 900×650)
└── QSplitter(Horizontal)
    ├── Sidebar (固定 220px)
    └── ChatPanel (stretch)
```

### `app/ui/sidebar.py`

```
Sidebar
└── QVBoxLayout
    ├── 标题 "claude-hunter"
    ├── [新对话] → 重启 PtyWorker
    ├── [清空输出] → 清空 output_area
    ├── "快速技能" + QScrollArea → skill 按钮（点击填充 ":name"）
    └── "自定义任务" + QScrollArea → task 按钮（点击发送 prompt）
```

### `app/ui/chat_panel.py`

```
ChatPanel
└── QVBoxLayout
    ├── output_area (QTextEdit 只读, 深色, 等宽字体, 自动滚底)
    ├── QHBoxLayout: [解释代码] [找 Bug] [重构代码]（填充输入框）
    ├── input_box (QTextEdit, max-height 120px)
    │   ├── Enter 发送，Shift+Enter 换行
    │   └── : / 触发 AutoCompleteWidget
    └── [发送] QPushButton
```

### `app/ui/autocomplete.py`

```
AutoCompleteWidget (QListWidget, 浮动)
├── ":" → 显示 skill 列表，前缀匹配
├── "/" → 显示命令列表，前缀匹配
├── 其他 / ESC → 隐藏
├── 定位：输入框上方
├── 点击 / Tab / Enter → 填充到输入框
└── 最多 8 条，可滚动
```

## UI 颜色主题（深色）

| 元素 | 颜色 |
|------|------|
| 主背景 | `#1e1e1e` |
| Sidebar | `#252526` |
| 输出框 | `#1e1e1e` |
| 输出文字 | `#d4d4d4` |
| 输入框 | `#2d2d2d` |
| 按钮 | `#0e639c` / hover `#1177bb` |
| 分隔线 | `#3a3a3a` |
| 字体 | 输出区等宽 Menlo 13px，UI 系统字体 13px |

## 错误处理

| 场景 | 处理 |
|------|------|
| `claude` 命令不存在 | 启动时 QMessageBox 提示 + 安装说明 |
| PTY 进程意外退出 | 输出区红色提示，"新对话"按钮高亮 |
| tasks/ 文件解析失败 | 跳过文件，侧边栏底部显示警告标签 |
| skill 扫描目录不存在 | 静默跳过，补全仅显示内置命令 |

## 打包

```bash
pyinstaller -w -n claude-hunter --icon assets/icon.icns main.py
```

生成 `dist/claude-hunter.app`，拖入应用程序文件夹双击启动。

## 任务配置示例

**JSON 格式** `tasks/代码审查.json`：
```json
{
  "name": "🔍 代码审查",
  "cli_args": "",
  "prompt": "请帮我严格审查这段代码，找出bug、性能问题、安全风险，并给出修复后的完整代码。"
}
```

**MD 格式** `tasks/查bug.md`：
```
帮我快速定位代码bug，告诉我：
1. 问题根源
2. 修复方案
3. 改好的完整代码
```

## 后续可扩展（已预留接口）

- 对话导出为 MD 文件
- 代码高亮（QSyntaxHighlighter）
- UI 内文件选择按钮（替代手动输入 @）
- 自定义字体大小和主题色
