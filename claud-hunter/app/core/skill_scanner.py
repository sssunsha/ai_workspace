from pathlib import Path

_BUILTIN_COMMANDS = [
    "/help", "/new", "/clear", "/review", "/cost",
    "/compact", "/config", "/quit", "/exit", "/memory",
]


def scan_skills(base_dir: Path = None) -> list[str]:
    if base_dir is None:
        base_dir = Path.home() / ".claude" / "plugins"

    skills: set[str] = set()

    for search_path in [base_dir, base_dir / "cache"]:
        if not search_path.exists():
            continue
        for plugin_dir in search_path.iterdir():
            if not plugin_dir.is_dir():
                continue
            skills_dir = plugin_dir / "skills"
            if skills_dir.exists():
                for entry in skills_dir.iterdir():
                    if entry.is_dir():
                        skills.add(entry.name)

    return sorted(skills)


def get_builtin_commands() -> list[str]:
    return list(_BUILTIN_COMMANDS)
