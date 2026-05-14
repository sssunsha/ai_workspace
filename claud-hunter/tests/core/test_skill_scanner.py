from pathlib import Path
from app.core.skill_scanner import scan_skills, get_builtin_commands


def test_scan_skills_finds_skill_dirs(tmp_path):
    plugins = tmp_path / "plugins"
    plugin_a = plugins / "my-plugin" / "skills" / "code-review"
    plugin_b = plugins / "my-plugin" / "skills" / "python-dev"
    plugin_a.mkdir(parents=True)
    plugin_b.mkdir(parents=True)

    skills = scan_skills(base_dir=plugins)

    assert "code-review" in skills
    assert "python-dev" in skills


def test_scan_skills_deduplicates(tmp_path):
    plugins = tmp_path / "plugins"
    (plugins / "plugin-a" / "skills" / "debug").mkdir(parents=True)
    (plugins / "cache" / "plugin-b" / "skills" / "debug").mkdir(parents=True)

    skills = scan_skills(base_dir=plugins)

    assert skills.count("debug") == 1


def test_scan_skills_returns_sorted(tmp_path):
    plugins = tmp_path / "plugins"
    (plugins / "p" / "skills" / "zzz").mkdir(parents=True)
    (plugins / "p" / "skills" / "aaa").mkdir(parents=True)

    skills = scan_skills(base_dir=plugins)

    assert skills == sorted(skills)


def test_scan_skills_missing_dir_returns_empty(tmp_path):
    skills = scan_skills(base_dir=tmp_path / "nonexistent")
    assert skills == []


def test_scan_skills_ignores_files_in_skills_dir(tmp_path):
    plugins = tmp_path / "plugins"
    skills_dir = plugins / "p" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "readme.md").write_text("not a skill")

    skills = scan_skills(base_dir=plugins)

    assert skills == []


def test_get_builtin_commands_returns_list():
    commands = get_builtin_commands()
    assert "/help" in commands
    assert "/new" in commands
    assert isinstance(commands, list)
