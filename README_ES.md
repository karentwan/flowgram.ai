![Image](https://github.com/user-attachments/assets/4f9dfa0e-e600-4d4e-9e73-c919184f7573)

<div align="center">

[![License](https://img.shields.io/github/license/bytedance/flowgram.ai)](https://github.com/bytedance/flowgram.ai/blob/main/LICENSE) [![@flowgram.ai/editor](https://img.shields.io/npm/dm/%40flowgram.ai%2Fcore)](https://www.npmjs.com/package/@flowgram.ai/editor)

</div>

# FlowGram｜Workflow Studio

[English](README.md) | [中文](README_ZH.md) | [Español](README_ES.md) | [Русский](README_RU.md) | [Português](README_PT.md) | [Deutsch](README_DE.md) | [日本語](README_JA.md)

Un editor de flujos de trabajo visual y un backend de ejecución, construido sobre el framework [FlowGram.AI](https://flowgram.ai). Compón pipelines de IA/agentes en un lienzo de diseño libre — peticiones HTTP, llamadas LLM, código, condiciones, bucles, nodos MCP/agente — y ejecútalos en el servidor.

El repositorio contiene dos aplicaciones:

- **`apps/flow-studio`** — el editor del navegador (React + Rsbuild). Los flujos de trabajo creados se persisten en el backend y se ejecutan en modo servidor.
- **`apps/flow-backend`** — un servidor tRPC + Prisma (MySQL). Persiste flujos de trabajo (con cifrado de secretos en reposo), los ejecuta a través del runtime y expone la API de ejecución que el editor invoca.

## 🚀 Inicio rápido

### Requisitos previos

- Node.js 18+ y pnpm 10.6.5 (versión exigida por Rush)
- Una base de datos MySQL (p. ej., un contenedor Docker local)

### 1. Instalar dependencias

```sh
git clone <repo-url> && cd flowgram.ai
npx @microsoft/rush install
```

### 2. Configurar el backend

```sh
cd apps/flow-backend
cp .env.example .env        # luego edita los valores (DATABASE_URL, FLOWGRAM_ENCRYPTION_KEY, ...)
```

Genera una clave de cifrado y ejecuta la migración de la base de datos:

```sh
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"  # -> FLOWGRAM_ENCRYPTION_KEY
rushx db:generate           # generar el cliente de Prisma
rushx db:migrate            # crear el esquema (MySQL)
```

### 3. Ejecutar

En dos terminales:

```sh
# Terminal 1 — backend (por defecto http://localhost:4000)
cd apps/flow-backend && rushx dev

# Terminal 2 — editor de estudio (por defecto http://localhost:3000)
cd apps/flow-studio && rushx dev
```

> El editor se comunica por defecto con `http://localhost:4100` (ver `apps/flow-studio/src/api/trpc.ts`). Para apuntarlo a tu backend, define `window.__FLOW_BACKEND_URL__` o edita esa constante; asegúrate de que `CORS_ORIGIN` en el `.env` del backend coincida con el origen del editor.

Tras hacer pull, reconstruye todos los paquetes con:

```sh
rush build
```

## ✨ Características

| Característica | Descripción |
| --- | --- |
| [Free Layout Canvas](https://flowgram.ai/examples/free-layout/free-feature-overview.html) | Lienzo de diseño libre donde los nodos se pueden colocar en cualquier posición y conectarse con líneas libres. |
| [Fixed Layout Canvas](https://flowgram.ai/examples/fixed-layout/fixed-feature-overview.html) | Lienzo de diseño fijo con posicionamiento por arrastre y nodos compuestos (ramas, bucles). |
| [Form](https://flowgram.ai/examples/node-form/basic.html) | Motor de formularios para la configuración de nodos: renderizado, validación, efectos, enlace y captura de errores. |
| [Variable](https://flowgram.ai/guide/variable/basic.html) | Motor de variables con restricciones de ámbito, inspección de estructura e inferencia de tipos. |
| Runtime de servidor | Los flujos de trabajo se ejecutan en el backend (`task/run`, `task/validate`, ...); el editor los invoca en modo servidor. |
| Cifrado de secretos | Los secretos en las cabeceras de nodos MCP/agente se cifran en reposo y se descifran de forma transparente al leerlos. |

## 📦 Estructura del proyecto

```
apps/
  flow-studio/      editor del navegador (React + Rsbuild)
  flow-backend/     servidor tRPC + Prisma (MySQL)
packages/           librerías del framework FlowGram (motor de canvas, motor de nodos, runtime, plugins)
common/             herramientas de Rush y autoinstaladores
config/             preajustes compartidos de eslint / tsconfig
e2e/                suites de Playwright (por escenario)
```

## 📖 Documentación del framework

Esta aplicación está construida sobre el framework FlowGram.AI. La documentación del framework está en [flowgram.ai](https://flowgram.ai) (Inicio rápido, Canvas, Form, Variable, Material, Runtime, Referencia de API).

## License

[MIT](LICENSE)
