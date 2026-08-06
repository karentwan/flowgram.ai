![Image](https://github.com/user-attachments/assets/4f9dfa0e-e600-4d4e-9e73-c919184f7573)

<div align="center">

[![License](https://img.shields.io/github/license/bytedance/flowgram.ai)](https://github.com/bytedance/flowgram.ai/blob/main/LICENSE) [![@flowgram.ai/editor](https://img.shields.io/npm/dm/%40flowgram.ai%2Fcore)](https://www.npmjs.com/package/@flowgram.ai/editor)

</div>

# FlowGram｜Workflow Studio

[English](README.md) | [中文](README_ZH.md) | [Español](README_ES.md) | [Русский](README_RU.md) | [Português](README_PT.md) | [Deutsch](README_DE.md) | [日本語](README_JA.md)

Um editor de fluxos de trabalho visual e um backend de execução, construído sobre o framework [FlowGram.AI](https://flowgram.ai). Componha pipelines de IA/agentes em uma tela de layout livre — requisições HTTP, chamadas de LLM, código, condições, loops, nós MCP/agente — e execute-os no servidor.

O repositório contém dois aplicativos:

- **`apps/flow-studio`** — o editor do navegador (React + Rsbuild). Os fluxos de trabalho criados são persistidos no backend e executados em modo servidor.
- **`apps/flow-backend`** — um servidor tRPC + Prisma (MySQL). Persiste fluxos de trabalho (com criptografia de segredos em repouso), executa-os através do runtime e expõe a API de execução que o editor chama.

## 🚀 Início rápido

### Pré-requisitos

- Node.js 18+ e pnpm 10.6.5 (versão imposta pelo Rush)
- Um banco de dados MySQL (ex.: um container Docker local)

### 1. Instalar dependências

```sh
git clone <repo-url> && cd flowgram.ai
npx @microsoft/rush install
```

### 2. Configurar o backend

```sh
cd apps/flow-backend
cp .env.example .env        # depois edite os valores (DATABASE_URL, FLOWGRAM_ENCRYPTION_KEY, ...)
```

Gere uma chave de criptografia e execute a migração do banco de dados:

```sh
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"  # -> FLOWGRAM_ENCRYPTION_KEY
rushx db:generate           # gerar o cliente Prisma
rushx db:migrate            # criar o esquema (MySQL)
```

### 3. Executar

Em dois terminais:

```sh
# Terminal 1 — backend (por padrão http://localhost:4000)
cd apps/flow-backend && rushx dev

# Terminal 2 — editor do studio (por padrão http://localhost:3000)
cd apps/flow-studio && rushx dev
```

> O editor fala por padrão com `http://localhost:4100` (ver `apps/flow-studio/src/api/trpc.ts`). Para apontá-lo ao seu backend, defina `window.__FLOW_BACKEND_URL__` ou edite essa constante; garanta que o `CORS_ORIGIN` no `.env` do backend corresponda à origem do editor.

Após um pull, reconstrua todos os pacotes com:

```sh
rush build
```

## ✨ Recursos

| Recurso | Descrição |
| --- | --- |
| [Free Layout Canvas](https://flowgram.ai/examples/free-layout/free-feature-overview.html) | Tela de layout livre onde os nós podem ser colocados em qualquer posição e conectados com linhas livres. |
| [Fixed Layout Canvas](https://flowgram.ai/examples/fixed-layout/fixed-feature-overview.html) | Tela de layout fixo com posicionamento por arrasto e nós compostos (ramos, loops). |
| [Form](https://flowgram.ai/examples/node-form/basic.html) | Motor de formulários para configuração de nós: renderização, validação, efeitos, ligação e captura de erros. |
| [Variable](https://flowgram.ai/guide/variable/basic.html) | Motor de variáveis com restrições de escopo, inspeção de estrutura e inferência de tipos. |
| Runtime de servidor | Os fluxos de trabalho são executados no backend (`task/run`, `task/validate`, ...); o editor os chama em modo servidor. |
| Criptografia de segredos | Segredos nos cabeçalhos de nós MCP/agente são criptografados em repouso e descriptografados de forma transparente na leitura. |

## 📦 Estrutura do projeto

```
apps/
  flow-studio/      editor do navegador (React + Rsbuild)
  flow-backend/     servidor tRPC + Prisma (MySQL)
packages/           bibliotecas do framework FlowGram (motor de canvas, motor de nós, runtime, plugins)
common/             ferramentas do Rush e autoinstaladores
config/             predefinições compartilhadas de eslint / tsconfig
e2e/                suítes do Playwright (por cenário)
```

## 📖 Documentação do framework

Este aplicativo é construído sobre o framework FlowGram.AI. A documentação do framework está em [flowgram.ai](https://flowgram.ai) (Início rápido, Canvas, Form, Variável, Material, Runtime, Referência de API).

## License

[MIT](LICENSE)
