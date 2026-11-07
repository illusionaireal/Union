#!/usr/bin/env python3
"""Build and operate a local, versioned UNION candidate release.

This tool deliberately has no SSH, container, or systemctl integration.  A host
operator supplies local paths and performs service restarts under its own
change-control procedure.  It keeps application releases, host configuration,
and mutable organization data separate.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path


PAYLOAD_PATHS = (
    "ai_union", "web/console", "ops/systemd", "scripts", "examples",
    "pyproject.toml", "requirements-harness.lock", "package.json", "package-lock.json",
    ".nvmrc", "README.md",
)
CONFIG_KEYS = {"organization_root", "console_root", "listen_host", "listen_port"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def candidate_name(version: str) -> str:
    if not version or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for char in version):
        raise ValueError("版本只能包含字母、数字、点、下划线或连字符")
    return f"ai-union-{version}"


def build(source: Path, output: Path, version: str) -> Path:
    source = source.resolve()
    if git(source, "status", "--porcelain"):
        raise ValueError("候选包必须从干净工作区构建")
    name = candidate_name(version)
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"{name}.tar.gz"
    manifest = {
        "format": 1,
        "name": name,
        "version": version,
        "commit": git(source, "rev-parse", "HEAD"),
        "built_at": int(time.time()),
        "payload_paths": list(PAYLOAD_PATHS),
        "configuration": "host supplied; never included in the archive",
        "state": "host supplied; never included in the archive",
    }
    with tarfile.open(archive, "w:gz", format=tarfile.PAX_FORMAT) as tar:
        for item in PAYLOAD_PATHS:
            path = source / item
            if not path.exists():
                raise ValueError(f"候选包缺少必需文件: {item}")
            tar.add(path, arcname=f"{name}/payload/{item}", recursive=True)
        encoded = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
        info = tarfile.TarInfo(f"{name}/manifest.json")
        info.size = len(encoded)
        info.mode = 0o644
        tar.addfile(info, io.BytesIO(encoded))
    Path(str(archive) + ".sha256").write_text(f"{sha256(archive)}  {archive.name}\n", encoding="utf-8")
    return archive


def read_archive(archive: Path) -> tuple[str, dict]:
    with tarfile.open(archive, "r:gz") as tar:
        manifests = [member for member in tar.getmembers() if member.name.endswith("/manifest.json")]
        if len(manifests) != 1:
            raise ValueError("候选包必须恰好包含一个 manifest.json")
        member = manifests[0]
        manifest = json.load(tar.extractfile(member))
        prefix = member.name.removesuffix("/manifest.json")
        if manifest.get("format") != 1 or manifest.get("name") != prefix:
            raise ValueError("候选包 manifest 无效")
        if any(not entry.startswith(prefix + "/") for entry in tar.getnames()):
            raise ValueError("候选包包含不安全的顶层路径")
    return prefix, manifest


def verify(archive: Path, checksum_file: Path | None = None) -> dict:
    prefix, manifest = read_archive(archive)
    if checksum_file:
        expected = checksum_file.read_text(encoding="utf-8").split()[0]
        if sha256(archive) != expected:
            raise ValueError("候选包 SHA-256 不匹配")
    return {"name": prefix, "commit": manifest["commit"], "version": manifest["version"]}


def load_config(config: Path) -> dict:
    if not config.is_file():
        raise ValueError("缺少宿主配置；在任何写入或切换前停止")
    value = json.loads(config.read_text(encoding="utf-8"))
    if set(value) != CONFIG_KEYS:
        raise ValueError("宿主配置字段必须且只能为 organization_root、console_root、listen_host、listen_port")
    if value["listen_host"] not in {"127.0.0.1", "::1"}:
        raise ValueError("候选包只允许回环监听；公网暴露由宿主反向代理单独配置")
    if not isinstance(value["listen_port"], int) or not 1 <= value["listen_port"] <= 65535:
        raise ValueError("listen_port 必须是有效端口")
    for key in ("organization_root", "console_root"):
        if not Path(value[key]).is_absolute():
            raise ValueError(f"{key} 必须是绝对宿主路径")
    return value


def safe_extract(archive: Path, destination: Path, prefix: str) -> None:
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            target = destination / member.name
            if not target.resolve().is_relative_to(destination.resolve()) or member.issym() or member.islnk():
                raise ValueError("候选包包含不安全路径或链接")
        tar.extractall(destination, filter="data")
    extracted = destination / prefix / "payload"
    if not extracted.is_dir():
        raise ValueError("候选包缺少 payload")


def stage(archive: Path, install_root: Path, config: Path) -> Path:
    load_config(config)  # Validate all required host inputs before touching release paths.
    name, _ = read_archive(archive)
    releases = install_root / "releases"
    target = releases / name
    if target.exists():
        return target
    releases.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=releases, prefix=f".{name}.") as temporary:
        tmp = Path(temporary)
        safe_extract(archive, tmp, name)
        os.replace(tmp / name, target)
    return target


def current_target(install_root: Path) -> Path | None:
    current = install_root / "current"
    return current.resolve() if current.is_symlink() else None


def activate(install_root: Path, version: str, config: Path) -> Path:
    load_config(config)
    target = install_root / "releases" / candidate_name(version)
    if not (target / "payload").is_dir():
        raise ValueError("目标候选版未完成 stage")
    current = install_root / "current"
    temporary = install_root / ".current.next"
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(target.relative_to(install_root))
    os.replace(temporary, current)
    return current.resolve()


def backup(state_root: Path, backup_root: Path, label: str) -> Path:
    if not state_root.is_dir():
        raise ValueError("状态目录不存在，拒绝创建空备份")
    backup_root.mkdir(parents=True, exist_ok=True)
    destination = backup_root / f"union-state-{label}-{int(time.time())}.tar.gz"
    with tarfile.open(destination, "w:gz", format=tarfile.PAX_FORMAT) as tar:
        tar.add(state_root, arcname="state", recursive=True)
    destination.chmod(0o600)
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build_p = commands.add_parser("build"); build_p.add_argument("--source", type=Path, default=Path.cwd()); build_p.add_argument("--output", type=Path, required=True); build_p.add_argument("--version", required=True)
    verify_p = commands.add_parser("verify"); verify_p.add_argument("--archive", type=Path, required=True); verify_p.add_argument("--checksum", type=Path)
    for command in ("stage", "activate"):
        item = commands.add_parser(command); item.add_argument("--install-root", type=Path, required=True); item.add_argument("--config", type=Path, required=True); item.add_argument("--version", required=command == "activate")
        if command == "stage": item.add_argument("--archive", type=Path, required=True)
    backup_p = commands.add_parser("backup"); backup_p.add_argument("--state-root", type=Path, required=True); backup_p.add_argument("--backup-root", type=Path, required=True); backup_p.add_argument("--label", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "build": result = build(args.source, args.output, args.version)
        elif args.command == "verify": result = verify(args.archive, args.checksum)
        elif args.command == "stage": result = stage(args.archive, args.install_root, args.config)
        elif args.command == "activate": result = activate(args.install_root, args.version, args.config)
        else: result = backup(args.state_root, args.backup_root, args.label)
    except (OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"release: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"ok": True, "result": str(result) if isinstance(result, Path) else result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
