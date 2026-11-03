# 实施计划

1. `scripts/release_package.py`负责打包、严格验证、安装、宿主配置、版本预检与原子切换；不复用带实际NAS地址的旧脚本。
2. 包内保留运行时预期目录结构，可直接用指定Python运行`-m ai_union.server`，Bun运行固定`services/modeld/dist/main.js`，启动不执行npm或供应商认证。
3. `tests/test_release_package.py`先验证失效路径和状态隔离，再完成实际复制安装验证；所有新结果写入`evidence/052-release-package/`。
4. 更新模型服务使用说明、052清单、STATUS/HANDOFF及主账U-060证据；U-054的完整发布和旧部署脚本配置化保持未完成。
