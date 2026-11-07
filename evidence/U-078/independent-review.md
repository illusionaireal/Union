# U-078 独立工程复核

2026-11-08，codex-home 复核 DSH 提交 d5e779f1021810cc70d88411b8c55e3c39a707a9。范围：tests/links.py 和三处边界用例、ai_union/workspace.py 首次绑定校验。

Windows 无符号链接权限时用目录联接准备测试；POSIX 不调用 cmd。产品校验新增 lstat reparse-point 检查，拒绝链接根/后代，并核对解析后包含关系。它收紧首次绑定边界，不增加任意宿主执行权限，不声称消除外部文件系统竞争。

独立 Windows 验证：32 tests，OK，3 个 Linux 平台用例跳过；链接越界用例实际运行。NAS 隔离 Linux 验证：从确切 d5e779f 导出干净源码，在已安装工具镜像、network none、只读源码挂载运行同一 32 tests，全部通过、无跳过。未挂载现有 AU 私有数据，未替换运行服务。

命令：`python -m unittest tests.test_links tests.test_workspace tests.test_documents tests.test_core_creation_failures -v`。原始输出仅在宿主私有运维目录；DSH 的历史输出仍保留原路径。

结论：该提交在所审查的链接准备/首次目录绑定边界范围内可集成。当前重写分支另外的 S03 提交不属于此次独立复核。
