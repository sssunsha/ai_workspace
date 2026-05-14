from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Task:
    name: str
    prompt: str
    cli_args: str = ""


def load_tasks(tasks_dir: Path) -> tuple[list[Task], list[str]]:
    if not tasks_dir.exists():
        tasks_dir.mkdir(parents=True, exist_ok=True)
        return [], []

    tasks: list[Task] = []
    warnings: list[str] = []

    for path in sorted(tasks_dir.iterdir()):
        if path.suffix == ".json":
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                tasks.append(Task(
                    name=data["name"],
                    prompt=data["prompt"],
                    cli_args=data.get("cli_args", ""),
                ))
            except Exception as e:
                warnings.append(f"跳过 {path.name}: {e}")
        elif path.suffix == ".md":
            try:
                content = path.read_text(encoding="utf-8").strip()
                tasks.append(Task(name=path.stem, prompt=content))
            except Exception as e:
                warnings.append(f"跳过 {path.name}: {e}")

    return tasks, warnings
