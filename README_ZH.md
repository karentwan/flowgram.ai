![Image](https://github.com/user-attachments/assets/4f9dfa0e-e600-4d4e-9e73-c919184f7573)

<div align="center">

[![License](https://img.shields.io/github/license/bytedance/flowgram.ai)](https://github.com/bytedance/flowgram.ai/blob/main/LICENSE) [![@flowgram.ai/editor](https://img.shields.io/npm/dm/%40flowgram.ai%2Fcore)](https://www.npmjs.com/package/@flowgram.ai/editor)

</div>

# FlowGram｜工作流工作室

[English](README.md) | [中文](README_ZH.md) | [Español](README_ES.md) | [Русский](README_RU.md) | [Português](README_PT.md) | [Deutsch](README_DE.md) | [日本語](README_JA.md)

基于 [FlowGram.AI](https://flowgram.ai) 框架构建的可视化工作流编辑器与执行后端。在自由布局画布上编排 AI / Agent 流程 —— HTTP 请求、LLM 调用、代码、条件、循环、MCP/Agent 节点 —— 并在服务端运行。

本仓库包含两个应用：

- **`apps/flow-studio`** —— 浏览器端编辑器（React + Rsbuild）。编排好的工作流会持久化到后端，并以服务端模式执行。
- **`apps/flow-backend`** —— 基于 tRPC + Prisma（MySQL）的服务端。持久化工作流（对密钥进行静态加密），通过运行时执行工作流，并对外暴露编辑器调用的执行 API。

## 🚀 快速上手

### 前置条件

- Node.js 18+ 与 pnpm 10.6.5（由 Rush 强制约束版本）
- 一个 MySQL 数据库（例如本地 Docker 容器）

### 1. 安装依赖

```sh
git clone <repo-url> && cd flowgram.ai
npx @microsoft/rush install
```

### 2. 配置后端

```sh
cd apps/flow-backend
cp .env.example .env        # 然后编辑其中的值（DATABASE_URL、FLOWGRAM_ENCRYPTION_KEY 等）
```

生成加密密钥并执行数据库迁移：

```sh
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"  # -> FLOWGRAM_ENCRYPTION_KEY
rushx db:generate           # 生成 Prisma 客户端
rushx db:migrate            # 建表（MySQL）
```

### 3. 运行

在两个终端分别启动：

```sh
# 终端 1 —— 后端（默认 http://localhost:4000）
cd apps/flow-backend && rushx dev

# 终端 2 —— 编辑器（默认 http://localhost:3000）
cd apps/flow-studio && rushx dev
```

> 编辑器默认连接 `http://localhost:4100`（见 `apps/flow-studio/src/api/trpc.ts`）。如需指向你的后端，可设置 `window.__FLOW_BACKEND_URL__` 或修改该常量，并确保后端 `.env` 中的 `CORS_ORIGIN` 与编辑器地址一致。

拉取代码后如需重新构建所有包：

```sh
rush build
```

## ✨ 特性

| 特性 | 说明 |
| --- | --- |
| [Free Layout Canvas](https://flowgram.ai/examples/free-layout/free-feature-overview.html) | 自由布局画布，节点可任意摆放，可在节点间创建边进行链接。 |
| [Fixed Layout Canvas](https://flowgram.ai/examples/fixed-layout/fixed-feature-overview.html) | 固定布局画布，节点可拖拽至指定位置，支持复合节点（如分支与循环）。 |
| [Form](https://flowgram.ai/examples/node-form/basic.html) | 表单引擎管理节点数据的增删改查，提供渲染、验证、副作用、联动和错误捕获等能力，简化节点配置开发。 |
| [Variable](https://flowgram.ai/guide/variable/basic.html) | 变量引擎支持作用域约束、变量结构检查和类型推断，便于管理工作流中的数据流。 |
| 服务端运行时 | 工作流在后端执行（`task/run`、`task/validate` 等），编辑器以服务端模式调用。 |
| 密钥加密 | MCP/Agent 节点的 header 密钥会静态加密，读取时透明解密。 |

## 📦 项目结构

```
apps/
  flow-studio/      浏览器端编辑器（React + Rsbuild）
  flow-backend/     tRPC + Prisma 服务端（MySQL）
packages/           FlowGram 框架库（画布引擎、节点引擎、运行时、插件）
common/             Rush 工具与 autoinstallers
config/             共享的 eslint / tsconfig 预设
e2e/                Playwright 测试套件（按场景）
```

## 📖 框架文档

本应用基于 FlowGram.AI 框架构建。框架层面的文档位于 [flowgram.ai](https://flowgram.ai)（快速入门、画布、表单、变量、物料、运行时、API 参考）。

## License

[MIT](LICENSE)
