# Nocturne Memory — 架构重构优先 TODO

> **分支**: `refactor/maintainability-architecture-review`  
> **目标**: 先把长期维护的结构性债务降下来，再做局部 UI polish。  
> **原则**: 个人 fork，允许主动重构；每个任务必须让边界更清楚、风险更可测、未来修改更便宜。  
> **最后审查**: 2026-05-20，结合后端 / 前端 / 测试运维 / 外部 refactor backlog 模式审查结果。
> 仅本地代办备忘，不进行git跟踪。

---

## 0. 执行规则：不要再写“愿望清单”

本文件不是 bug 备忘录，而是架构债务 register。新增条目必须包含：

- **证据**：具体文件、现象、代码味道。
- **为什么现在做**：影响范围、修改频率、风险。
- **第一切片**：能在 1-2 个会话内完成且可回滚的最小改动。
- **验收标准**：跑什么测试 / 看什么 diff / 删除什么债务才算完成。
- **不做什么**：避免把一次重构膨胀成无边界大爆炸。

优先级按长期维护收益排序，而不是按视觉可见度排序：

| 等级 | 含义 | 处理方式 |
|------|------|----------|
| P0 | 阻塞未来重构或持续误导架构判断 | 当前阶段优先处理 |
| P1 | 高频修改区的结构性债务 | P0 后连续推进 |
| P2 | 需要护栏 / 测试 / 文档沉淀的中期治理 | 随 P0/P1 建立过程逐步做 |
| P3 | 局部体验或低风险清理 | 只能在相关区域被触碰时顺手做 |

---

## P0 — 先拆炸弹：消除最误导维护者的结构债

### - [x] P0-1. 删除或隔离 Neo4j 遗留死代码

- **证据**：`backend/db/neo4j_client.py` 约 2247 行，是后端最大文件；当前活跃路径不使用，仅 `backend/scripts/migrate_neo4j_to_sqlite.py` 这个一次性迁移脚本引用。
- **为什么现在做**：它让搜索、代码地图、依赖理解都误判“项目仍有 Neo4j 后端”。任何架构审查都会被这 2247 行噪音污染。
- **已完成**：Neo4j 迁移相关文件已移入 `backend/archive/neo4j_legacy/`，活跃 `backend/db/` 与 `backend/scripts/` 路径不再包含 Neo4j client / migration script；README 与 AGENTS 路径已更新。
- **验收标准**：
  - 活跃 `backend/db/` 中不再出现 Neo4j client。
  - `grep -R "get_neo4j_client\|Neo4jClient" backend` 只命中归档说明或完全无命中。
  - `pytest backend/tests` 通过。
- **不做什么**：不要顺手重写 SQLite/PostgreSQL 数据模型；这是死代码切除，不是数据层重构。

### - [x] P0-2. 建立单一 ASGI 应用构建器，消除多入口漂移

- **证据**：`backend/main.py`、`backend/mcp_server.py::build_web_app()`、`backend/run_sse.py` 都参与启动；中间件顺序在文档和代码中不一致。
- **为什么现在做**：认证、CORS、namespace 隔离属于安全边界；入口漂移会让“本地 API 正常 / SSE 模式异常”这类 bug 很难诊断。
- **已完成**：新增 `backend/app_builder.py`，集中 REST API router/exception handler、中间件包装、SPA fallback；`main.py` 和 `mcp_server.build_web_app()` 已委托共享 builder。
- **第一切片**：新增 `backend/app.py`，集中：router 注册、CORS、NamespaceMiddleware、BearerTokenAuthMiddleware、exception handler、SPA mount。`main.py` 和 `run_sse.py` 都只调用这个构建器。
- **验收标准**：
  - 中间件顺序在一个地方定义，并与 `AGENTS.md` 一致：`CORSMiddleware → NamespaceMiddleware → BearerTokenAuthMiddleware → App`。
  - `main.py` 不再手写 router / middleware 拼装。
  - `mcp_server.py` 不再承担 Web app 组装职责，只保留 MCP 工具和传输相关逻辑。
  - API smoke tests 与 MCP tests 通过。
- **不做什么**：不要在同一 PR 改 MCP 工具行为。

### - [x] P0-3. 给前端建立最低限度测试与 CI 护栏

- **证据**：`frontend/` 没有 `*.test.*`、Vitest/Jest 配置，也没有 CI 中的 `npm run build`。
- **为什么现在做**：后续要拆 `MemoryBrowser.jsx`、替换原生弹窗、改 namespace 切换；没有测试会让每一步都只能靠肉眼。
- **第一切片**：引入 Vitest + React Testing Library，先覆盖：`App.jsx` 路由 smoke、`TokenAuth` 成功/失败流程、一个纯展示组件。
- **已完成**：新增 Vitest + React Testing Library 测试基础设施；覆盖 `App.jsx` 认证/路由 smoke、`TokenAuth` 成功/401/网络失败流程、`DiffViewer` 纯展示组件；CI 新增 frontend job，执行 `npm ci`、`npm run build`、`npm run test:run`。
- **安全补丁**：P0-3 后复核 `npm audit` 暴露 10 项前端依赖漏洞，已通过非破坏性升级清零：`axios`、`react-router-dom`、`vite`、`postcss`、`diff` 及传递依赖 `follow-redirects`、`rollup`、`picomatch`。
- **验收标准**：
  - `frontend/package.json` 有 `test` / `test:run` 脚本。
  - CI 至少运行 `npm ci`, `npm run build`, `npm run test:run`。
  - 新增测试不依赖真实后端。
- **不做什么**：不要一开始追求高覆盖率；先让前端改动能被 CI 挡住。

### - [ ] P0-4. 把 `demo.db` 从活跃版本控制中移除

- **证据**：`demo.db` 约 1.3MB，被 git 跟踪；`AGENTS.md` 已标为历史问题。
- **为什么现在做**：二进制数据库让 diff 不可审查，也容易把本地数据误提交。长期架构重构不应背着样例数据文件走。
- **第一切片**：`git rm --cached demo.db`，补 `.gitignore`/README 说明；如仍需 demo 数据，改为脚本或压缩 fixture。
- **验收标准**：
  - `git status` 不再把数据库文件作为可提交源码。
  - 首次启动 demo 数据路径仍有明确替代方案。
- **不做什么**：除非专门安排历史清理，不在当前阶段做 filter-repo 改写历史。

---

## P1 — 拆核心 god objects：先切边界，再改行为

### - [ ] P1-1. 分阶段 strangler `GraphService`

- **证据**：`backend/db/graph.py` 约 2149 行，承担 CRUD、查询、GC、路径级联、诊断、版本链、索引重建；公开/私有方法总数约 60+。
- **为什么现在做**：这是所有记忆操作的核心。任何新增功能都会继续堆进神类，导致测试和理解成本线性上升。
- **第一切片**：先抽只读查询边界，不改行为：
  1. 新增 `backend/db/query_service.py`。
  2. 移动纯读取方法，如 path lookup、children 获取、diagnostic 所需只读查询。
  3. `GraphService` 组合 `QueryService`，保持原公共 API 兼容。
- **验收标准**：
  - `GraphService` 行数明显下降。
  - 所有 MCP/API 调用无需修改或只改 import。
  - `pytest backend/tests/service backend/tests/mcp` 通过。
- **下一切片**：抽 `GarbageCollector`：`_gc_node_*`, `_gc_edge_*`, `_cascade_delete_node`。
- **不做什么**：不要一次性把 `GraphService` 全拆完；每个切片必须 behavior-preserving。

### - [ ] P1-2. 统一数据库 session 管理，停止引用私有 `_optional_session`

- **证据**：`GraphService` 捕获 `DatabaseManager._optional_session`；`rollback_to_memory`、`remove_path`、`restore_path` 等公共方法混用“自己开 session”和“调用者传 session”。
- **为什么现在做**：事务边界不清会让 review rollback、MCP 写入、API 写入难以组合。私有方法泄露也阻碍数据库层重构。
- **第一切片**：把 `_optional_session` 升级成公开、命名明确的 `session_scope(session=None)`；所有服务通过同一个上下文管理器进入事务。
- **验收标准**：
  - `grep -R "_optional_session" backend` 无活跃业务命中。
  - 事务内调用 rollback/remove/restore 的测试仍通过。
  - 不新增“裸 session”传递模式。
- **不做什么**：不要同时改 SQLAlchemy engine 初始化策略。

### - [ ] P1-3. 拆 `mcp_server.py`：MCP 工具、Web 生命周期、前端构建分离

- **证据**：`backend/mcp_server.py` 约 1179 行，同时包含 MCP 工具注册、ASGI 构建、前端自动构建、内嵌 uvicorn、system URI 入口。
- **为什么现在做**：MCP 协议层是项目对 agent 的核心接口，不应该被 Dashboard 静态文件服务和启动细节污染。
- **已完成的前置切片**：`backend/app_builder.py` 已抽出 REST API router/exception handler、中间件包装、SPA fallback；`main.py` 与 `mcp_server.build_web_app()` 已共享该 builder。
- **第一切片**：
  - `backend/mcp/tools.py`：7 个工具注册和参数验证。
  - `backend/mcp/system_routes.py`：`system://boot/index/recent/random/diagnostic` 解析。
  - `backend/ui_build.py`：前端构建与 SPA fallback。
- **验收标准**：
  - `mcp_server.py` 变成薄入口。
  - 7 个 MCP 工具数量不变。
  - `pytest backend/tests/mcp` 通过。
- **不做什么**：不要修改 MCP tool schema 或工具语义。

### - [ ] P1-3a. 收敛后端 import 运行模型，消除 basedpyright implicit-relative 噪音

- **证据**：后端当前靠 `backend/` 加入 `sys.path` 后使用 `from db import ...`、`from api import ...` 这类顶层导入；basedpyright 会把新增文件中的同类导入报告为 implicit relative import。
- **为什么现在不做**：这会牵动全后端 import 体系，超出 P0-2 app builder 抽取范围。
- **第一切片**：新增明确的包入口策略（二选一）：要么正式让 `backend` 成为包并使用 `backend.db` 绝对导入；要么在 pyright 配置中声明 backend 为 execution environment/source root。
- **验收标准**：新增 Python 文件不再需要用 `importlib.import_module("db")` 规避 LSP；LSP error 基线下降而不破坏运行命令。

### - [ ] P1-3b. 处理 Neo4j PowerShell 备份脚本遗留物

- **证据**：P0-1 复核发现根目录 `scripts/backup_memory.ps1` 仍是 pre-1.0 Neo4j Desktop 备份脚本，且含硬编码 Windows/Neo4j 路径；它与活跃 `scripts/setup_docker.py` 并列，容易误导。
- **为什么现在不做**：这是 P0-1 旁支清理，不属于 P0-2 ASGI app builder。
- **第一切片**：移动到 `backend/archive/neo4j_legacy/backup_memory.ps1`，或删除并在 archive README 中说明旧备份脚本不再维护。
- **验收标准**：根目录 `scripts/` 只保留活跃部署脚本；Neo4j 字样只出现在 archive 和 README 旧版迁移说明中。

### - [ ] P1-4. 拆 `review.py` 并修复私有符号依赖

- **证据**：`backend/api/review.py` 约 845 行，导入 `db.snapshot._make_row_key`，混合 diff、changeset group、rollback、deprecated cleanup。
- **为什么现在做**：Review/Audit 是人类回滚 AI 写入的安全网；这里的逻辑必须可测、可替换、边界清楚。
- **第一切片**：先把 `_make_row_key` 变成 `ChangesetStore` 的公开方法，review API 不直接拼内部 key。
- **下一切片**：拆出 `review/diff.py`、`review/rollback.py`、`review/groups.py`。
- **验收标准**：
  - `api/review.py` 不再 import `_` 前缀私有成员。
  - 新增 rollback/group 单元测试。
  - Review API 集成测试通过。
- **不做什么**：不要在拆文件时改变 UI 响应 shape。

---

## P1 — 前端架构债：先可测，再拆组件，再修体验

### - [ ] P1-5. 替换全站 `alert` / `confirm` / `window.prompt`

- **证据**：前端多个文件使用浏览器原生弹窗；`MaintenancePage.jsx` 明确有 `window.prompt()`；`ReviewPage.jsx`、settings sections、memory 管理组件也有 `alert/confirm`。
- **为什么现在做**：项目已经把原生 prompt/alert 记为反模式；继续保留会让 UI 状态、无障碍、测试都卡住。
- **第一切片**：实现共享 `ConfirmDialog`、`PromptDialog`、`Toast/ErrorBanner`，先替换 `MaintenancePage.jsx` 与 `ReviewPage.jsx`。
- **验收标准**：
  - `grep -R "window\.prompt\|window\.alert\|window\.confirm\|alert(\|confirm(" frontend/src` 无业务命中。
  - 相关流程有组件测试或最少 smoke test。
- **不做什么**：不要顺手重设计所有页面视觉；先消除阻塞 API。

### - [ ] P1-6. 拆 `MemoryBrowser.jsx` 单体组件

- **证据**：`frontend/src/features/memory/MemoryBrowser.jsx` 约 600+ 行，混合路由、数据获取、编辑、搜索、删除、boot toggle、create modal。
- **为什么现在做**：它是 Dashboard 核心页面，继续堆功能会让每次交互修复变成全局风险。
- **第一切片**：提取纯展示 / 局部状态组件：`MemoryDetailPanel`、`SearchResultsOverlay`、`DeleteConfirmModal`。数据获取先不动。
- **验收标准**：
  - `MemoryBrowser.jsx` 行数下降到可读范围。
  - 提取组件通过 props，不直接读 router/searchParams。
  - 现有浏览、编辑、搜索、删除流程可手测/测试通过。
- **不做什么**：不要在第一切片同时引入全局状态库。

### - [ ] P1-7. 统一前端 API 层，停止 raw axios 与 wrapper 混用

- **证据**：`frontend/src/lib/api.js` 同时导出 raw `api` 和若干具名 wrapper；`MemoryBrowser.jsx` 同时使用 `api.get('/browse/node')` 与 `renameNode/deleteNode/searchMemories`。
- **为什么现在做**：API shape 的知识散落在视图里，未来后端 endpoint 调整会扩大 blast radius。
- **第一切片**：按领域拆 wrapper：`memoryApi`, `reviewApi`, `settingsApi`, `maintenanceApi`；页面不直接拼 URL。
- **验收标准**：
  - feature 组件不再直接调用 `api.get('/...')`，除非是临时迁移白名单。
  - API wrapper 有最小测试或 mock 验证。
- **不做什么**：不要在同一 PR 改接口返回格式。

### - [ ] P1-8. 修复 TokenAuth 持久化竞态

- **证据**：`TokenAuth.jsx` 在验证 token 前先写 localStorage；401 interceptor 会立刻清除并广播 auth error。
- **为什么现在做**：登录入口的小竞态会污染所有 API 流程，也会影响之后的测试稳定性。
- **第一切片**：先用临时 header 验证 token，成功后才持久化。
- **验收标准**：
  - 失败 token 不会写入 localStorage。
  - TokenAuth 测试覆盖成功和失败。

---

## P2 — 架构护栏：把“约定”变成会失败的检查

### - [ ] P2-1. 建立架构 fitness functions

- **目标**：把 AGENTS.md 中的反模式变成自动检查，而不是靠 agent 自觉。
- **第一批规则**：
  - `api/` 不得直接读 `os.environ` 或 `config.json`。
  - `api/` 不得 import `db.snapshot._*` 私有成员。
  - `frontend/src` 不得使用 `window.prompt/alert/confirm`。
  - `backend/db/` 不得新增文件级 pyright 抑制。
  - 活跃路径不得 import `backend/db/neo4j_client.py`。
- **第一切片**：用一个 Python 脚本或 pytest AST 检查实现上述 5 条，并加入 CI。
- **验收标准**：违规时 CI fail；每条规则有一条故意违规 fixture 或注释说明。

### - [ ] P2-2. 重整测试金字塔

- **证据**：后端测试集中且薄；前端此前无测试；review/rollback、migration、config、snapshot 等高风险模块覆盖不足。
- **第一切片顺序**：
  1. `review.py` rollback/group tests。
  2. `GraphService` 写路径参数化测试。
  3. `snapshot.py` 文件损坏/并发/namespace tests。
  4. `config.py` cache invalidation tests。
  5. migration runner smoke tests。
- **验收标准**：每次重构一个边界，先补 characterization test，再移动代码。

### - [ ] P2-3. 拆配置全局可变缓存

- **证据**：`backend/config.py` 使用模块级 `_cache` 与私有 `_invalidate()`；测试直接调用私有方法重置。
- **为什么现在做**：设置面板和服务启动都依赖配置；未来多进程/SSE 模式会放大陈旧缓存问题。
- **第一切片**：公开 `reload()`，停止测试访问 `_invalidate()`；给 `get()/set_value()` 加线程锁。
- **验收标准**：`grep -R "config\._invalidate" backend/tests` 无命中。
- **不做什么**：不要立即引入复杂 watcher。

### - [ ] P2-4. 快照存储从全局 JSON 文件转向可隔离模型

- **证据**：`backend/db/snapshot.py` 使用单个 `changeset.json`；注释明确所有 namespace 共用。
- **为什么现在做**：Review/Audit 是核心安全网，长期应支持 namespace 隔离、轮换、查询、损坏恢复。
- **第一切片**：先按 namespace 分片文件：`snapshots/{namespace}/changeset.json`，不改存储格式。
- **下一切片**：设计 DB-backed changeset table，并写 ADR。
- **验收标准**：不同 namespace 的变更不会进入同一 changeset 文件。

### - [ ] P2-5. 建立 ADR / CHANGELOG / 技术债 register

- **证据**：关键架构知识散落在 README、AGENTS.md、代码注释，没有 ADR；当前 TODO 也是临时草稿。
- **第一切片**：新增：
  - `docs/adr/0001-node-memory-edge-path-model.md`
  - `docs/adr/0002-config-json-ssot.md`
  - `docs/td/REGISTER.md`
- **验收标准**：本 TODO 中每个 P0/P1 条目都有稳定 ID，并能迁移到 `docs/td/`。

---

## P2 — 运维与依赖卫生

### - [ ] P2-6. 清理 Python 依赖边界

- **证据**：`backend/requirements.txt` 可能包含非后端核心依赖：`requests`/`Pillow` 偏 `desktop_pet`，`pydantic-settings`/`pypinyin` 未见活跃使用。
- **第一切片**：用 import 扫描确认依赖归属；移动 `desktop_pet` 专用依赖到 `desktop_pet/requirements.txt`。
- **验收标准**：后端 Docker image 只安装后端实际需要的包。

### - [ ] P2-7. Docker runtime 瘦身与 compose CI

- **证据**：`backend/Dockerfile` runtime 安装 build-essential/libpq-dev/postgresql-client 等重依赖；compose 未在 CI 验证。
- **第一切片**：添加 CI 的 `docker compose config` + build smoke；后续再做 multi-stage Dockerfile。
- **验收标准**：CI 能捕获 compose 语法和镜像构建失败。

### - [ ] P2-8. 固定 Node 版本和贡献流程

- **证据**：无 `.nvmrc`、无 `CONTRIBUTING.md`、`SECURITY.md`、PR template。
- **第一切片**：新增 `.nvmrc` 与最小 `CONTRIBUTING.md`，记录本 fork 的重构优先原则和验证命令。

---

## P3 — 从旧 Dashboard TODO 继承的局部体验问题

这些问题仍有效，但不应该压过架构债。处理它们时必须顺手消除相关结构问题。

### - [ ] P3-1. 侧栏树展开无加载反馈

- **位置**：`frontend/src/features/memory/components/MemorySidebar.jsx`
- **重构前置**：先解决 `MemoryBrowser` / `MemorySidebar` 重复请求边界，再补 loading 状态。
- **验收标准**：展开节点时有 per-node loading，错误可重试。

### - [ ] P3-2. `/browse/node` 的 `nav_only` 与 glossary 扫描边界不清

- **位置**：`backend/api/browse.py`，`frontend/src/features/memory/MemoryBrowser.jsx`
- **重构前置**：先建立统一 memory formatter；再让 `nav_only` 真正跳过非导航字段。

### - [ ] P3-3. 编辑模式导航离开无未保存确认

- **位置**：`MemoryBrowser.jsx`
- **重构前置**：先引入共享 ConfirmDialog；再给编辑状态加 dirty guard。

### - [ ] P3-4. 快速导航 / refreshData 竞态

- **位置**：`MemoryBrowser.jsx`
- **重构前置**：统一前端 API wrapper 后，为 browse 请求加 AbortController。

### - [ ] P3-5. 搜索 overlay / textarea 高度 / 本地化

- **位置**：`MemoryBrowser.jsx`、全局文案
- **处理方式**：只在拆 `MemoryBrowser` 或建立 i18n 时顺手处理，不单独开大任务。

旧 TODO 中“Vite 代理硬编码 8233”已过期：当前 `frontend/vite.config.js` 默认指向开发后端 8234，并支持环境变量覆盖。

---

## 建议执行顺序

1. **P0-2 单一 ASGI 应用构建器**：先消除入口漂移和中间件不一致。
2. **P0-1 Neo4j 死代码隔离**：降低搜索噪音和误导。
3. **P0-3 前端测试 + CI**：为后续 UI 重构建立安全网。
4. **P1-4 Review API 私有依赖修复 + rollback tests**：保护审计安全网。
5. **P1-1 GraphService 查询切片**：开始 strangler 核心神类。
6. **P1-5 原生弹窗替换**：解除前端测试和交互一致性的阻碍。
7. **P1-6 MemoryBrowser 拆分**：在测试存在后再动核心页面。
8. **P2-1 fitness functions**：把已经修过的规则固化成 CI 护栏。

每完成一个 P0/P1 条目，都应同步：

- 补 characterization test。
- 更新 `AGENTS.md` 或 ADR（如果规则变化）。
- 删除对应旧债务，而不是只新增抽象。
- 检查是否可以把本文件条目迁移成 `docs/td/TD-xxx.md` 稳定登记项。
