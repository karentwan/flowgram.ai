![Image](https://github.com/user-attachments/assets/4f9dfa0e-e600-4d4e-9e73-c919184f7573)

<div align="center">

[![License](https://img.shields.io/github/license/bytedance/flowgram.ai)](https://github.com/bytedance/flowgram.ai/blob/main/LICENSE) [![@flowgram.ai/editor](https://img.shields.io/npm/dm/%40flowgram.ai%2Fcore)](https://www.npmjs.com/package/@flowgram.ai/editor)

</div>

# FlowGram｜Workflow Studio

[English](README.md) | [中文](README_ZH.md) | [Español](README_ES.md) | [Русский](README_RU.md) | [Português](README_PT.md) | [Deutsch](README_DE.md) | [日本語](README_JA.md)

Визуальный редактор рабочих процессов и бэкенд выполнения, построенный на фреймворке [FlowGram.AI](https://flowgram.ai). Собирайте пайплайны ИИ/агентов на холсте свободного макета — HTTP-запросы, вызовы LLM, код, условия, циклы, узлы MCP/агента — и выполняйте их на сервере.

Репозиторий содержит два приложения:

- **`apps/flow-studio`** — браузерный редактор (React + Rsbuild). Созданные рабочие процессы сохраняются в бэкенде и выполняются в серверном режиме.
- **`apps/flow-backend`** — сервер на tRPC + Prisma (MySQL). Сохраняет рабочие процессы (с шифрованием секретов в покое), выполняет их через среду выполнения и предоставляет API выполнения, который вызывает редактор.

## 🚀 Быстрый старт

### Предварительные требования

- Node.js 18+ и pnpm 10.6.5 (версия enforced Rush)
- База данных MySQL (например, локальный Docker-контейнер)

### 1. Установка зависимостей

```sh
git clone <repo-url> && cd flowgram.ai
npx @microsoft/rush install
```

### 2. Настройка бэкенда

```sh
cd apps/flow-backend
cp .env.example .env        # затем заполните значения (DATABASE_URL, FLOWGRAM_ENCRYPTION_KEY, ...)
```

Сгенерируйте ключ шифрования и выполните миграцию базы данных:

```sh
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"  # -> FLOWGRAM_ENCRYPTION_KEY
rushx db:generate           # сгенерировать клиент Prisma
rushx db:migrate            # создать схему (MySQL)
```

### 3. Запуск

В двух терминалах:

```sh
# Терминал 1 — бэкенд (по умолчанию http://localhost:4000)
cd apps/flow-backend && rushx dev

# Терминал 2 — редактор студии (по умолчанию http://localhost:3000)
cd apps/flow-studio && rushx dev
```

> Редактор по умолчанию обращается к `http://localhost:4100` (см. `apps/flow-studio/src/api/trpc.ts`). Чтобы указать на ваш бэкенд, задайте `window.__FLOW_BACKEND_URL__` или измените эту константу; убедитесь, что `CORS_ORIGIN` в `.env` бэкенда совпадает с источником редактора.

После pull пересоберите все пакеты:

```sh
rush build
```

## ✨ Возможности

| Возможность | Описание |
| --- | --- |
| [Free Layout Canvas](https://flowgram.ai/examples/free-layout/free-feature-overview.html) | Холст свободного макета, где узлы можно размещать где угодно и соединять линиями в свободной форме. |
| [Fixed Layout Canvas](https://flowgram.ai/examples/fixed-layout/fixed-feature-overview.html) | Холст фиксированного макета с перетаскиванием и составными узлами (ветвления, циклы). |
| [Form](https://flowgram.ai/examples/node-form/basic.html) | Движок форм для настройки узлов: рендеринг, валидация, побочные эффекты, связывание, перехват ошибок. |
| [Variable](https://flowgram.ai/guide/variable/basic.html) | Движок переменных с ограничениями области видимости, инспекцией структуры и выводом типов. |
| Серверная среда выполнения | Рабочие процессы выполняются на бэкенде (`task/run`, `task/validate`, ...); редактор вызывает их в серверном режиме. |
| Шифрование секретов | Секреты в заголовках узлов MCP/агента шифруются в покое и прозрачно расшифровываются при чтении. |

## 📦 Структура проекта

```
apps/
  flow-studio/      браузерный редактор (React + Rsbuild)
  flow-backend/     сервер tRPC + Prisma (MySQL)
packages/           библиотеки фреймворка FlowGram (движок холста, движок узлов, среда выполнения, плагины)
common/             инструменты Rush и автоустановщики
config/             общие пресеты eslint / tsconfig
e2e/                наборы Playwright (по сценариям)
```

## 📖 Документация фреймворка

Это приложение построено на фреймворке FlowGram.AI. Документация по фреймворку находится на [flowgram.ai](https://flowgram.ai) (Быстрый старт, Холст, Формы, Переменные, Материалы, Среда выполнения, Справочник по API).

## License

[MIT](LICENSE)
