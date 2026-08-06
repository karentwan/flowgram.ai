![Image](https://github.com/user-attachments/assets/4f9dfa0e-e600-4d4e-9e73-c919184f7573)

<div align="center">

[![License](https://img.shields.io/github/license/bytedance/flowgram.ai)](https://github.com/bytedance/flowgram.ai/blob/main/LICENSE) [![@flowgram.ai/editor](https://img.shields.io/npm/dm/%40flowgram.ai%2Fcore)](https://www.npmjs.com/package/@flowgram.ai/editor)

</div>

# FlowGram｜Workflow Studio

[English](README.md) | [中文](README_ZH.md) | [Español](README_ES.md) | [Русский](README_RU.md) | [Português](README_PT.md) | [Deutsch](README_DE.md) | [日本語](README_JA.md)

Ein visueller Workflow-Editor und Ausführungs-Backend, aufgebaut auf dem [FlowGram.AI](https://flowgram.ai)-Framework. Komponieren Sie KI-/Agent-Pipelines auf einer Free-Layout-Canvas — HTTP-Aufrufe, LLM-Aufrufe, Code, Conditions, Loops, MCP-/Agent-Knoten — und führen Sie sie serverseitig aus.

Dieses Repository enthält zwei Anwendungen:

- **`apps/flow-studio`** — der Browser-Editor (React + Rsbuild). Erstellte Workflows werden im Backend persistiert und im Server-Modus ausgeführt.
- **`apps/flow-backend`** — ein tRPC + Prisma (MySQL) Server. Persistiert Workflows (mit Verschlüsselung der Secrets at-rest), führt sie über die Runtime aus und stellt die Ausführungs-API bereit, die der Editor aufruft.

## 🚀 Quick Start

### Voraussetzungen

- Node.js 18+ und pnpm 10.6.5 (von Rush erzwungen)
- Eine MySQL-Datenbank (z. B. ein lokaler Docker-Container)

### 1. Abhängigkeiten installieren

```sh
git clone <repo-url> && cd flowgram.ai
npx @microsoft/rush install
```

### 2. Backend konfigurieren

```sh
cd apps/flow-backend
cp .env.example .env        # dann Werte eintragen (DATABASE_URL, FLOWGRAM_ENCRYPTION_KEY, ...)
```

Verschlüsselungsschlüssel erzeugen und Datenbank-Migration ausführen:

```sh
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"  # -> FLOWGRAM_ENCRYPTION_KEY
rushx db:generate           # Prisma-Client generieren
rushx db:migrate            # Schema anlegen (MySQL)
```

### 3. Starten

In zwei Terminals:

```sh
# Terminal 1 — Backend (standardmäßig http://localhost:4000)
cd apps/flow-backend && rushx dev

# Terminal 2 — Studio-Editor (standardmäßig http://localhost:3000)
cd apps/flow-studio && rushx dev
```

> Der Editor spricht standardmäßig `http://localhost:4100` an (siehe `apps/flow-studio/src/api/trpc.ts`). Um auf Ihr Backend zu zeigen, setzen Sie `window.__FLOW_BACKEND_URL__` oder passen Sie die Konstante an; stellen Sie sicher, dass `CORS_ORIGIN` in der Backend-`.env` mit der Studio-Origin übereinstimmt.

Nach einem Pull alle Pakete neu bauen:

```sh
rush build
```

## ✨ Features

| Feature | Beschreibung |
| --- | --- |
| [Free Layout Canvas](https://flowgram.ai/examples/free-layout/free-feature-overview.html) | Free-Layout-Canvas, auf der Knoten beliebig platziert und mit Freiform-Linien verbunden werden. |
| [Fixed Layout Canvas](https://flowgram.ai/examples/fixed-layout/fixed-feature-overview.html) | Fixed-Layout-Canvas mit Drag-to-Snap-Positionierung und Verbundknoten (Verzweigungen, Schleifen). |
| [Form](https://flowgram.ai/examples/node-form/basic.html) | Form-Engine für Knotenkonfiguration: Rendering, Validierung, Side-Effects, Linkage, Error-Capture. |
| [Variable](https://flowgram.ai/guide/variable/basic.html) | Variablen-Engine mit Scope-Beschränkungen, Strukturinspektion und Typ-Inferenz. |
| Server-Runtime | Workflows werden im Backend ausgeführt (`task/run`, `task/validate`, ...); der Editor ruft sie im Server-Modus auf. |
| Secret-Verschlüsselung | Secrets in den Headern von MCP-/Agent-Knoten werden at-rest verschlüsselt und beim Lesen transparent entschlüsselt. |

## 📦 Projektstruktur

```
apps/
  flow-studio/      Browser-Editor (React + Rsbuild)
  flow-backend/     tRPC + Prisma Server (MySQL)
packages/           FlowGram-Framework-Bibliotheken (Canvas-Engine, Node-Engine, Runtime, Plugins)
common/             Rush-Tooling und Autoinstaller
config/             Gemeinsame eslint-/tsconfig-Presets
e2e/                Playwright-Suiten (pro Szenario)
```

## 📖 Framework-Doku

Diese Anwendung baut auf dem FlowGram.AI-Framework auf. Framework-Dokumentation finden Sie auf [flowgram.ai](https://flowgram.ai) (Quick Start, Canvas, Form, Variable, Material, Runtime, API-Referenz).

## License

[MIT](LICENSE)
