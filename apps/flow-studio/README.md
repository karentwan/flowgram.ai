# Flowgram Studio

可视化工作流编辑器（基于 `@flowgram.ai/free-layout-editor`），配合 [`flow-backend`](../flow-backend) 做工作流持久化与运行时执行。在原 `demo-free-layout` 基础上新增了登录鉴权、工具栏（保存 / 另存为 / 打开 / 新建），以及 **MCP 工具节点** 和 **Agent 节点**。

- 前端（本项目）：`http://localhost:3000`
- 后端（`apps/flow-backend`）：`http://localhost:4100`

## 前置条件

- **Node.js 22**（仓库用 Rush + pnpm 管理；本机用 `nvm use 22`）
- **MySQL** 可达（后端用 Prisma 连 MySQL）
- 已在仓库根目录执行过 `rush install` / `rush build`（至少构建过 `@flowgram.ai/runtime-*` 与 free-layout-editor 相关包）

## 一、配置后端（`apps/flow-backend`）

1. 复制环境文件并填值：

   ```bash
   cd apps/flow-backend
   cp .env.example .env
   ```

   编辑 `.env`：

   ```dotenv
   PORT=4100
   HOST=0.0.0.0
   NODE_ENV=development

   # 改成你自己的 MySQL 连接串
   DATABASE_URL=mysql://root:password@127.0.0.1:3306/flowgram

   # 32 字节 base64 主密钥，用于加密节点里的 secrets（server.headers）。
   # 生成方式：
   #   node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
   FLOWGRAM_ENCRYPTION_KEY=<上面生成的串>

   # 允许的前端来源（CORS）。studio 默认跑在 3000。
   CORS_ORIGIN=http://localhost:3000
   ```

   > 如果你要把 studio 跑在别的端口（如 3100），把那个 origin 也加进 `CORS_ORIGIN`，逗号分隔：
   > `CORS_ORIGIN=http://localhost:3000,http://localhost:3100`

2. 初始化数据库 & 生成 Prisma Client：

   ```bash
   cd apps/flow-backend
   npx prisma db push          # 把 schema 同步到 MySQL（建表）
   npx prisma generate         # 生成 Prisma Client
   ```

3. 创建登录用户（会打印 API Key，**只显示一次，请保存**）：

   ```bash
   npx tsx --env-file=.env src/scripts/seed.ts
   # 或指定用户名：
   npx tsx --env-file=.env src/scripts/seed.ts -- --name alice
   ```

   输出示例：

   ```
   Created user "admin".
     id: user_xxx
     apiKey: fk_d3aa432d24be68414fdcda6dea692e578f4d91efbc7c22f5
   ```

   再次运行同名用户是幂等的（保留原 key）。

4. 启动后端：

   ```bash
   cd apps/flow-backend
   npx tsx watch --env-file=.env src/index.ts
   # 看到 "> flow-backend listening on http://0.0.0.0:4100" 即成功
   ```

   健康检查：`curl http://localhost:4100/health` → `{"status":"ok",...}`

## 二、启动前端（`apps/flow-studio`）

```bash
cd apps/flow-studio
nvm use 22
npx cross-env MODE=app NODE_ENV=development rsbuild dev
# 默认监听 http://localhost:3000
```

> 想换端口：在命令后加 `--port 3100`，并记得把 `http://localhost:3100` 加进后端 `CORS_ORIGIN`。

浏览器打开 **http://localhost:3000**，进入登录页，粘贴上一步 seed 打印的 `fk_...` API Key 即可。

## 三、使用流程

1. **登录**：粘贴 API Key → Sign in（调用 `auth.whoami` 校验）。
2. **画流程**：从左侧节点面板拖入节点。除原有 LLM / HTTP / Code / Loop / Condition 等节点外，现在还有：
   - **mcp**：调用 MCP 工具
   - **agent**：调用 Agent 的对话接口
3. **配置 MCP 节点**：
   - **URL**：MCP 服务端 HTTP 端点（Streamable-HTTP 传输）
   - **Headers**：鉴权头（如 `api_key`），键值对形式
   - **Tool**：填完 URL 后会自动调用 `tools/list` 发现可用工具并下拉选择；发现失败也可手动输入工具名
   - **Args**：工具入参（flow value，可引用上游变量）
   - **Timeout / Retry**：超时与重试次数
4. **配置 Agent 节点**：
   - **URL**：Agent 服务的 `/chat/process` 端点
   - **Agent ID / User ID**：对应 body 里的 `agent_id` / `user_id`
   - **Input**：本轮用户消息，支持 `{` 插入上游变量
   - **Session**：勾选「Auto-generate」则每次运行用新 session（新对话）；否则用固定 id 续接已有对话
5. **保存 / 另存为 / 打开 / 新建**：右上角工具栏。保存走乐观锁（带 `version`，冲突会被后端拒绝）。
6. **运行**：MCP / Agent 的真正执行发生在**后端**（`task.run` 等 tRPC 过程，由 `@flowgram.ai/runtime-nodejs` 的 `MCPExecutor` / `AgentExecutor` 执行），所以浏览器不会有 CORS 问题、secret 也不会下发到前端。

## 四、架构要点

```
┌─────────────────────┐        tRPC (HTTP)        ┌──────────────────────────┐
│  flow-studio (3000) │  ───────────────────────► │  flow-backend (4100)     │
│  rsbuild + React    │  ◄─────────────────────── │  Fastify + tRPC + Prisma │
│  free-layout-editor │   auth.whoami             │                          │
│  + StudioBar        │   workflow.{list,get,     │  → MySQL (Workflow/User) │
│  + AuthGate         │     create,update,delete} │  → runtime-nodejs        │
│                     │   task.{run,report,...}   │    (MCP/Agent Executor)  │
└─────────────────────┘                           └──────────────────────────┘
```

- **鉴权**：API Key 作为 Bearer token 存在 `localStorage`，每个请求带上 `Authorization` 头。
- **节点密钥**：节点里的 `server.headers`（含 api_key 等）在后端用 `FLOWGRAM_ENCRYPTION_KEY` 加密后入库；读取时解密。
- **乐观锁**：`workflow.update` 必须带当前 `version`；冲突返回 `409 CONFLICT`。
- **节点注册**：编辑器节点定义在 `src/nodes/`，运行时执行器在 `packages/runtime/js-core/src/nodes/`，节点 schema 在 `packages/runtime/interface/src/node/`。

## 五、常见问题

- **登录提示 Invalid API key**：确认用的是 seed 打印的 `fk_...`，且后端 `.env` 指向正确的库。
- **前端请求被 CORS 拦**：把前端实际访问的 origin 加进后端 `CORS_ORIGIN`，重启后端。
- **`prisma generate` 报错**：确认 `DATABASE_URL` 可达，且 MySQL 里已 `CREATE DATABASE flowgram`。
- **节点面板看不到 mcp / agent**：确认 `src/nodes/index.ts` 的 `nodeRegistries` 里已 import 并加入这两个 registry（默认已加）。

## 六、相关代码位置

| 模块 | 路径 |
|------|------|
| 前端入口 | `src/app.tsx`、`src/editor.tsx` |
| 登录 / 工具栏 | `src/studio/auth-gate.tsx`、`src/studio/studio-bar.tsx` |
| tRPC 客户端 | `src/api/trpc.ts` |
| MCP 编辑器节点 | `src/nodes/mcp/`（registry + form + components） |
| Agent 编辑器节点 | `src/nodes/agent/` |
| 后端入口 | `apps/flow-backend/src/index.ts`、`server.ts` |
| 路由 | `apps/flow-backend/src/trpc-root.ts`、`src/routers/` |
| MCP 执行器 | `packages/runtime/js-core/src/nodes/mcp/index.ts` |
| Agent 执行器 | `packages/runtime/js-core/src/nodes/agent/index.ts` |
| 节点 schema | `packages/runtime/interface/src/node/mcp|agent/index.ts` |
