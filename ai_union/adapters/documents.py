"""Host-registered read-only document roots for V1 work.

The host operator registers roots in `<console-root>/document-roots.json`; the
HTTP surface only ever carries the opaque reference. Nothing here writes,
creates, migrates or follows a link out of an authorized root.
"""
import hashlib
import json
import os
import re
from pathlib import Path, PurePath

from ..domain.work import reference
from ..errors import Rejected, require

REGISTRY = "document-roots.json"
MAX_BYTES = 262144
MAX_FILES = 200
_SPLIT = re.compile(r"[\\/]+")


def _text(value):
    return value if isinstance(value, str) else ""


def registry(console_root):
    """Read the host-owned registry; a malformed file is refused, never guessed."""
    path = Path(console_root) / REGISTRY
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise Rejected("宿主资料目录登记文件无法解析；请由宿主修正后重试") from error
    require(isinstance(value, dict) and value.get("version") == 1 and isinstance(value.get("roots"), dict),
            "宿主资料目录登记文件格式无效")
    roots = {}
    for name, target in value["roots"].items():
        require(reference(name), "宿主资料目录登记包含无效引用标识")
        require(isinstance(target, str) and target, "宿主资料目录登记必须写明绝对目录")
        roots[name] = target
    return roots


def root_for(console_root, name):
    """Return the real, existing directory a registered reference names."""
    require(reference(name), "资料目录须引用宿主已登记的标识，不接受路径或范围外引用")
    roots = registry(console_root)
    require(name in roots, "资料目录引用未由宿主登记")
    raw = roots[name]
    require(os.path.isabs(raw) and not raw.startswith("\\\\"), "宿主资料目录登记必须是本机绝对目录")
    path = Path(raw)
    require(path.exists() and path.is_dir(), "宿主登记的资料目录不存在或不是目录")
    return path.resolve()


def _relative(value):
    """A bounded relative document path; host paths and traversal never qualify."""
    require(isinstance(value, str) and 1 <= len(value) <= 200, "资料路径无效")
    require("\x00" not in value and ":" not in value, "资料路径不得包含驱动器或控制字符")
    require(not value.startswith(("/", "\\")) and not PurePath(value).is_absolute(), "资料路径必须是相对路径")
    parts = [part for part in _SPLIT.split(value)]
    require(all(part and part not in (".", "..") for part in parts), "资料路径不得跳出授权目录")
    return parts


def resolve(root, value):
    """Resolve a document inside the authorized root; escapes through links fail."""
    parts = _relative(value)
    base = Path(root).resolve()
    candidate = base.joinpath(*parts)
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise Rejected("授权目录内不存在该资料") from error
    require(resolved.is_relative_to(base), "资料路径不得跳出授权目录")
    require(resolved.is_file(), "只能读取授权目录内的普通文件")
    return resolved


def list_documents(root):
    """List readable regular files inside the root; escapes are omitted."""
    base = Path(root).resolve()
    found = []
    for current, directories, files in os.walk(base, followlinks=False):
        directories[:] = [name for name in directories
                          if not (Path(current) / name).is_symlink()
                          and (Path(current) / name).resolve().is_relative_to(base)]
        for name in files:
            path = Path(current) / name
            resolved = path.resolve()
            if not resolved.is_relative_to(base) or not resolved.is_file():
                continue
            found.append(resolved.relative_to(base).as_posix())
            require(len(found) <= MAX_FILES, "授权目录文件数量超过本核心版本上限")
    return sorted(found)


def read_text(root, value):
    """Read one authorized document; binary content and oversize files are refused."""
    path = resolve(root, value)
    require(path.stat().st_size <= MAX_BYTES, "资料超过本核心版本允许的读取大小")
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise Rejected("授权目录内该资料无法读取") from error
    require(b"\x00" not in raw, "只能读取文本资料")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise Rejected("只能读取 UTF-8 文本资料") from error
    return text, hashlib.sha256(raw).hexdigest(), len(raw)
