import json
import pytest
from pathlib import Path
from app.core.task_loader import Task, load_tasks


def test_load_json_task(tmp_path):
    task_file = tmp_path / "审查.json"
    task_file.write_text(json.dumps({
        "name": "🔍 代码审查",
        "prompt": "请审查代码",
        "cli_args": "--model sonnet"
    }), encoding="utf-8")

    tasks, warnings = load_tasks(tmp_path)

    assert len(tasks) == 1
    assert tasks[0].name == "🔍 代码审查"
    assert tasks[0].prompt == "请审查代码"
    assert tasks[0].cli_args == "--model sonnet"
    assert warnings == []


def test_load_md_task(tmp_path):
    task_file = tmp_path / "查bug.md"
    task_file.write_text("帮我找bug\n1. 根源\n2. 修复", encoding="utf-8")

    tasks, warnings = load_tasks(tmp_path)

    assert len(tasks) == 1
    assert tasks[0].name == "查bug"
    assert tasks[0].prompt == "帮我找bug\n1. 根源\n2. 修复"
    assert tasks[0].cli_args == ""


def test_load_tasks_creates_dir_if_missing(tmp_path):
    missing = tmp_path / "nonexistent"
    tasks, warnings = load_tasks(missing)
    assert tasks == []
    assert warnings == []
    assert missing.exists()


def test_load_tasks_skips_bad_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json}", encoding="utf-8")

    tasks, warnings = load_tasks(tmp_path)

    assert tasks == []
    assert len(warnings) == 1
    assert "bad.json" in warnings[0]


def test_load_tasks_json_without_cli_args(tmp_path):
    task_file = tmp_path / "simple.json"
    task_file.write_text(json.dumps({
        "name": "简单任务",
        "prompt": "做点什么"
    }), encoding="utf-8")

    tasks, _ = load_tasks(tmp_path)

    assert tasks[0].cli_args == ""


def test_load_tasks_ignores_non_json_md_files(tmp_path):
    (tmp_path / "readme.txt").write_text("ignore me")
    (tmp_path / ".DS_Store").write_bytes(b"\x00")

    tasks, warnings = load_tasks(tmp_path)

    assert tasks == []
    assert warnings == []
