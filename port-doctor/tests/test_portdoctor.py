# -*- coding: utf-8 -*-
"""port-doctor 单元测试：扫描器 / 分配器 / 登记表 / CLI 端到端。

运行：
    cd port-doctor && python -m pytest tests -q
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, SCRIPTS)

import allocator  # noqa: E402
import registry   # noqa: E402
import scanner    # noqa: E402
import portctl    # noqa: E402


# ==========================================================================
# 扫描器
# ==========================================================================
def test_scan_next_default_port(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "demo", "scripts": {"dev": "next dev"}}), encoding="utf-8")
    proj = scanner.scan_project(tmp_path)
    assert 3000 in proj.ports


def test_scan_explicit_ports(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"dev": "vite --port 5180", "api": "PORT=6200 python app.py"}}),
        encoding="utf-8")
    (tmp_path / ".env").write_text("PORT=6100\nDEBUG=1\n", encoding="utf-8")
    proj = scanner.scan_project(tmp_path)
    assert {5180, 6200, 6100} <= set(proj.ports)


def test_scan_python_flask_port(tmp_path):
    (tmp_path / "app.py").write_text(
        "from flask import Flask\napp = Flask(__name__)\n"
        "if __name__ == '__main__':\n    app.run(port=5555)\n", encoding="utf-8")
    proj = scanner.scan_project(tmp_path)
    assert 5555 in proj.ports


def test_scan_docker_compose(tmp_path):
    (tmp_path / "docker-compose.yml").write_text(
        "services:\n  web:\n    ports:\n      - \"8081:80\"\n      - \"5433:5432\"\n",
        encoding="utf-8")
    proj = scanner.scan_project(tmp_path)
    assert {8081, 80, 5433, 5432} <= set(proj.ports)


def test_compose_container_side_is_not_host_port(tmp_path):
    """容器侧端口不占宿主机，不能算进冲突判定"""
    (tmp_path / "docker-compose.yml").write_text(
        "services:\n  web:\n    ports:\n      - \"8081:80\"\n", encoding="utf-8")
    proj = scanner.scan_project(tmp_path)
    assert proj.host_ports == [8081]
    assert proj.container_ports == [80]


def test_scan_vite_config(tmp_path):
    (tmp_path / "vite.config.ts").write_text(
        "export default {\n  server: { port: 4173 }\n}\n", encoding="utf-8")
    proj = scanner.scan_project(tmp_path)
    assert 4173 in proj.ports


def test_scan_bat_script(tmp_path):
    (tmp_path / "start.bat").write_text(
        "@echo off\npython -m uvicorn app:app --port 7777\n", encoding="utf-8")
    proj = scanner.scan_project(tmp_path)
    assert 7777 in proj.ports


def test_scan_skips_node_modules(tmp_path):
    nm = tmp_path / "node_modules" / "pkg"
    nm.mkdir(parents=True)
    (nm / "package.json").write_text(json.dumps({"scripts": {"dev": "next dev -p 9999"}}),
                                      encoding="utf-8")
    (tmp_path / "package.json").write_text(json.dumps({"scripts": {"dev": "next dev"}}),
                                            encoding="utf-8")
    proj = scanner.scan_project(tmp_path)
    assert 9999 not in proj.ports


def test_scan_evidence_has_source_and_line(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"dev": "vite --port 5188"}}), encoding="utf-8")
    proj = scanner.scan_project(tmp_path)
    d = [x for x in proj.decls if x.port == 5188][0]
    assert d.source.endswith("package.json")
    assert d.line >= 1
    assert "5188" in d.evidence


def test_find_project_roots(tmp_path):
    (tmp_path / "projA").mkdir()
    (tmp_path / "projA" / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "notaproject").mkdir()
    roots = scanner.find_project_roots(tmp_path)
    names = [r.name for r in roots]
    assert "projA" in names
    assert "notaproject" not in names


# ==========================================================================
# 分配器
# ==========================================================================
def test_is_port_free_detects_bound_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    port = s.getsockname()[1]
    try:
        assert allocator.is_port_free(port) is False
    finally:
        s.close()


def test_allocate_port_returns_usable_port():
    p = allocator.allocate_port(pool=(5200, 5300))
    assert 5200 <= p <= 5300
    assert allocator.is_port_free(p)


def test_allocate_port_prefers_requested():
    p = allocator.allocate_port(pool=(5200, 5300), prefer=5250)
    assert p == 5250


def test_allocate_port_skips_occupied_prefer():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    busy = s.getsockname()[1]
    try:
        p = allocator.allocate_port(pool=(5200, 5300), prefer=busy)
        assert p != busy
        assert allocator.is_port_free(p)
    finally:
        s.close()


def test_allocate_port_raises_when_pool_exhausted(monkeypatch):
    monkeypatch.setattr(allocator, "is_port_free", lambda *a, **k: False)
    monkeypatch.setattr(allocator, "in_excluded_range", lambda *a, **k: False)
    with pytest.raises(RuntimeError):
        allocator.allocate_port(pool=(5200, 5205))


def test_allocate_port_respects_exclude_set(monkeypatch):
    monkeypatch.setattr(allocator, "in_excluded_range", lambda *a, **k: False)
    p = allocator.allocate_port(pool=(5300, 5310), exclude={5300, 5301, 5302})
    assert p == 5303


def test_write_and_read_port_env(tmp_path):
    p = allocator.write_port_env(tmp_path, 5599)
    assert os.path.exists(p)
    assert allocator.read_port_env(tmp_path) == 5599


# ==========================================================================
# 登记表
# ==========================================================================
@pytest.fixture()
def reg(tmp_path, monkeypatch):
    monkeypatch.setenv("PORTDOCTOR_REGISTRY", str(tmp_path / "reg.json"))
    return tmp_path


def test_register_and_release(reg):
    entry = registry.register(5410, "/tmp/projX", "projX", pid=1234, proc="python")
    assert entry["status"] == "active"
    assert 5410 in registry.active_ports()
    hit = registry.release(project_path="/tmp/projX")
    assert len(hit) == 1
    assert 5410 not in registry.active_ports()


def test_register_same_port_supersedes(reg):
    registry.register(5411, "/tmp/a", "a", pid=1)
    registry.register(5411, "/tmp/b", "b", pid=2)
    active = registry.entries(active_only=True)
    assert len(active) == 1
    assert active[0]["project_name"] == "b"


def test_gc_stale_marks_dead_pid(reg):
    registry.register(5412, "/tmp/dead", "dead", pid=999999)
    changed = registry.gc_stale()
    assert len(changed) == 1
    assert registry.entries(active_only=True) == []


def test_registry_persists_to_file(reg):
    registry.register(5413, "/tmp/p", "p", pid=5)
    assert os.path.exists(registry.registry_path())
    with open(registry.registry_path(), encoding="utf-8") as f:
        data = json.load(f)
    assert data["entries"][0]["port"] == 5413


# ==========================================================================
# CLI 端到端
# ==========================================================================
def _run_cli(args, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "portctl.py")] + args,
                       capture_output=True, text=True, env=e, timeout=120)
    return r


def test_cli_scan_json(tmp_path):
    (tmp_path / "projA").mkdir()
    (tmp_path / "projA" / "package.json").write_text(
        json.dumps({"scripts": {"dev": "next dev"}}), encoding="utf-8")
    r = _run_cli(["scan", "--root", str(tmp_path), "--json"])
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["projects"][0]["ports"] == [3000]


def test_cli_check_reports_port(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"dev": "next dev -p 3011"}}), encoding="utf-8")
    r = _run_cli(["check", str(tmp_path)])
    assert r.returncode == 0
    assert "3011" in r.stdout


def test_cli_alloc_writes_env_and_registers(tmp_path):
    proj = tmp_path / "p1"
    proj.mkdir()
    (proj / "package.json").write_text(json.dumps({"scripts": {"dev": "next dev"}}),
                                        encoding="utf-8")
    regfile = tmp_path / "reg.json"
    r = _run_cli(["alloc", str(proj), "--pool", "5400-5410", "--write"],
                 env={"PORTDOCTOR_REGISTRY": str(regfile)})
    assert r.returncode == 0, r.stderr
    assert allocator.read_port_env(proj) is not None
    with open(regfile, encoding="utf-8") as f:
        data = json.load(f)
    assert data["entries"][0]["status"] == "active"


def test_cli_release_removes_registration(tmp_path):
    proj = tmp_path / "p2"
    proj.mkdir()
    (proj / "package.json").write_text("{}", encoding="utf-8")
    regfile = tmp_path / "reg2.json"
    env = {"PORTDOCTOR_REGISTRY": str(regfile)}
    r = _run_cli(["alloc", str(proj), "--pool", "5420-5430"], env=env)
    assert r.returncode == 0
    r2 = _run_cli(["release", str(proj)], env=env)
    assert r2.returncode == 0
    with open(regfile, encoding="utf-8") as f:
        data = json.load(f)
    assert all(e["status"] != "active" for e in data["entries"])


def test_cli_kill_requires_yes(tmp_path):
    r = _run_cli(["kill", "--pid", "1"])
    assert r.returncode == 2
    assert "--yes" in r.stderr


def test_cli_prelaunch_prints_port(tmp_path):
    proj = tmp_path / "p3"
    proj.mkdir()
    (proj / "package.json").write_text("{}", encoding="utf-8")
    r = _run_cli(["prelaunch", str(proj), "--pool", "5440-5450"],
                 env={"PORTDOCTOR_REGISTRY": str(tmp_path / "reg3.json")})
    assert r.returncode == 0
    assert r.stdout.strip().startswith("PORT=")


# ==========================================================================
# v1.0.1：.port.env 生效端口优先
# ==========================================================================
def test_read_port_env_parses_keys(tmp_path):
    (tmp_path / ".port.env").write_text(
        "# 由 port-doctor 自动生成\nPORT=5100\nFASTAPI_PORT=5109\n", encoding="utf-8")
    env = scanner.read_port_env(tmp_path)
    assert env == {"PORT": 5100, "FASTAPI_PORT": 5109}


def test_read_port_env_missing_file(tmp_path):
    assert scanner.read_port_env(tmp_path) == {}


def test_read_port_env_ignores_invalid(tmp_path):
    (tmp_path / ".port.env").write_text("PORT=abc\nBAD=\nX=1\n", encoding="utf-8")
    env = scanner.read_port_env(tmp_path)
    assert env == {"X": 1}


def test_effective_ports_prefers_port_env(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"dev": "next dev"}}), encoding="utf-8")
    (tmp_path / ".port.env").write_text("PORT=5100\n", encoding="utf-8")
    proj = scanner.scan_project(tmp_path)
    assert proj.host_ports == [3000]          # 声明端口仍在
    assert proj.effective_ports == [5100]     # 生效端口以 .port.env 为准


def test_effective_ports_falls_back_without_env_file(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"dev": "next dev"}}), encoding="utf-8")
    proj = scanner.scan_project(tmp_path)
    assert proj.effective_ports == [3000]


def test_static_conflict_uses_effective_ports(tmp_path):
    """两个项目声明同一端口，但各自 .port.env 已错开 → 不算静态撞车"""
    a = tmp_path / "a"; a.mkdir()
    b = tmp_path / "b"; b.mkdir()
    for d, port in ((a, 5100), (b, 5101)):
        (d / "package.json").write_text(
            json.dumps({"scripts": {"dev": "next dev"}}), encoding="utf-8")
        (d / ".port.env").write_text("PORT=%d\n" % port, encoding="utf-8")
    projects = scanner.scan_root(tmp_path)
    conflicts = portctl.find_static_conflicts(projects)
    assert conflicts == {}
    # 去掉 .port.env 后，同一端口就重新变成撞车
    for d in (a, b):
        os.remove(d / ".port.env")
    projects = scanner.scan_root(tmp_path)
    conflicts = portctl.find_static_conflicts(projects)
    assert 3000 in conflicts


# ==========================================================================
# v1.0.1：.port.env 生效端口优先
# ==========================================================================
def test_read_port_env_parses_keys(tmp_path):
    (tmp_path / ".port.env").write_text(
        "# 由 port-doctor 自动生成\nPORT=5100\nFASTAPI_PORT=5109\n", encoding="utf-8")
    env = scanner.read_port_env(tmp_path)
    assert env == {"PORT": 5100, "FASTAPI_PORT": 5109}


def test_read_port_env_missing_file(tmp_path):
    assert scanner.read_port_env(tmp_path) == {}


def test_read_port_env_ignores_invalid(tmp_path):
    (tmp_path / ".port.env").write_text("PORT=abc\nBAD=\nX=1\n", encoding="utf-8")
    env = scanner.read_port_env(tmp_path)
    assert env == {"X": 1}


def test_effective_ports_prefers_port_env(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"dev": "next dev"}}), encoding="utf-8")
    (tmp_path / ".port.env").write_text("PORT=5100\n", encoding="utf-8")
    proj = scanner.scan_project(tmp_path)
    assert proj.host_ports == [3000]          # 声明端口仍在
    assert proj.effective_ports == [5100]     # 生效端口以 .port.env 为准


def test_effective_ports_falls_back_without_env_file(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"scripts": {"dev": "next dev"}}), encoding="utf-8")
    proj = scanner.scan_project(tmp_path)
    assert proj.effective_ports == [3000]


def test_static_conflict_uses_effective_ports(tmp_path):
    """两个项目声明同一端口，但各自 .port.env 已错开 → 不算静态撞车"""
    a = tmp_path / "a"; a.mkdir()
    b = tmp_path / "b"; b.mkdir()
    for d, port in ((a, 5100), (b, 5101)):
        (d / "package.json").write_text(
            json.dumps({"scripts": {"dev": "next dev"}}), encoding="utf-8")
        (d / ".port.env").write_text("PORT=%d\n" % port, encoding="utf-8")
    projects = scanner.scan_root(tmp_path)
    conflicts = portctl.find_static_conflicts(projects)
    assert conflicts == {}
    # 去掉 .port.env 后，同一端口就重新变成撞车
    for d in (a, b):
        os.remove(d / ".port.env")
    projects = scanner.scan_root(tmp_path)
    conflicts = portctl.find_static_conflicts(projects)
    assert 3000 in conflicts
