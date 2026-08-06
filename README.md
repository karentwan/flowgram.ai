![Image](https://github.com/user-attachments/assets/4f9dfa0e-e600-4d4e-9e73-c919184f7573)

<div align="center">

[![License](https://img.shields.io/github/license/bytedance/flowgram.ai)](https://github.com/bytedance/flowgram.ai/blob/main/LICENSE) [![@flowgram.ai/editor](https://img.shields.io/npm/dm/%40flowgram.ai%2Fcore)](https://www.npmjs.com/package/@flowgram.ai/editor)

</div>

# FlowGram｜Workflow Studio

[English](README.md) | [中文](README_ZH.md) | [Español](README_ES.md) | [Русский](README_RU.md) | [Português](README_PT.md) | [Deutsch](README_DE.md) | [日本語](README_JA.md)

A visual workflow editor and execution backend, built on the [FlowGram.AI](https://flowgram.ai) framework. Compose AI/agent pipelines on a free-layout canvas — HTTP requests, LLM calls, code, conditions, loops, MCP/agent nodes — then run them server-side.

The repo contains two applications:

- **`apps/flow-studio`** — the browser editor (React + Rsbuild). Authored workflows are persisted to the backend and executed in server mode.
- **`apps/flow-backend`** — a tRPC + Prisma (MySQL) server. Persists workflows (with at-rest secret encryption), runs workflows through the runtime, and exposes the execution API the editor calls.

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and pnpm 10.6.5 (enforced by Rush)
- A MySQL database (e.g. a local Docker container)

### 1. Install dependencies

```sh
git clone <repo-url> && cd flowgram.ai
npx @microsoft/rush install
```

### 2. Configure the backend

```sh
cd apps/flow-backend
cp .env.example .env        # then edit values (DATABASE_URL, FLOWGRAM_ENCRYPTION_KEY, ...)
```

Generate an encryption key and run the database migration:

```sh
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"  # -> FLOWGRAM_ENCRYPTION_KEY
rushx db:generate           # generate the Prisma client
rushx db:migrate            # create the schema (MySQL)
```

### 3. Run

In two terminals:

```sh
# terminal 1 — backend (default http://localhost:4000)
cd apps/flow-backend && rushx dev

# terminal 2 — studio editor (default http://localhost:3000)
cd apps/flow-studio && rushx dev
```

> The editor talks to the backend at `http://localhost:4100` by default (see `apps/flow-studio/src/api/trpc.ts`). Point it at your backend by setting `window.__FLOW_BACKEND_URL__` or editing that constant; make sure the `CORS_ORIGIN` in the backend `.env` matches the studio origin.

To rebuild all packages after pulling changes:

```sh
rush build
```

## ✨ Features

| Feature | Description |
| --- | --- |
| [Free Layout Canvas](https://flowgram.ai/examples/free-layout/free-feature-overview.html) | Free-layout canvas where nodes can be placed anywhere and connected with free-form lines. |
| [Fixed Layout Canvas](https://flowgram.ai/examples/fixed-layout/fixed-feature-overview.html) | Fixed-layout canvas with drag-to-snap positioning and compound nodes (branches, loops). |
| [Form](https://flowgram.ai/examples/node-form/basic.html) | Form engine for node config: rendering, validation, side effects, linkage, error capture. |
| [Variable](https://flowgram.ai/guide/variable/basic.html) | Variable engine with scope constraints, structure inspection, and type inference. |
| Server runtime | Workflows execute on the backend (`task/run`, `task/validate`, ...); the editor calls it in server mode. |
| Secret encryption | MCP/Agent node header secrets are encrypted at rest and decrypted transparently on read. |

## 📦 Project Layout

```
apps/
  flow-studio/      browser editor (React + Rsbuild)
  flow-backend/     tRPC + Prisma server (MySQL)
packages/           FlowGram framework libraries (canvas engine, node engine, runtime, plugins)
common/             Rush tooling and autoinstallers
config/             Shared eslint / tsconfig presets
e2e/                Playwright suites (per scenario)
```

## 📖 Framework docs

This application is built on the FlowGram.AI framework. Framework-level documentation lives at [flowgram.ai](https://flowgram.ai) (Quick Start, Canvas, Form, Variable, Material, Runtime, API Reference).

## License

[MIT](LICENSE)
