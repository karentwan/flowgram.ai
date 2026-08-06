# Repository Guidelines

## Project Structure & Module Organization
FlowGram is a Rush-managed monorepo. Production-ready libraries live under `packages/*` (canvas engine, node engine, runtime, plugins). Applications live under `apps/*` (`apps/flow-studio` editor and `apps/flow-backend` server). Shared tooling, config, and scripts live under `common/` and `config/`. End-to-end Playwright suites are isolated in `e2e/<scenario>` so they can be installed and run independently. New code should land in the closest existing package; create additional Rush projects only when a module needs its own version and publish cycle.

## Build, Test, and Development Commands
Use Node.js 18 LTS with pnpm 10.6.5 (Rush enforces versions). Install dependencies via `rush install`. Run `rush build` to compile every registered project. `rush lint`, `rush lint:fix`, and `rush ts-check` keep lint/TS diagnostics consistent. `rush test` aggregates unit tests; `rush e2e:test` runs Playwright suites, while `rush e2e:update-screenshot` refreshes snapshots.

## Coding Style & Naming Conventions
We write TypeScript with React, sharing configs from `config/eslint-config`. ESLint enforces 2-space indentation, semicolons, and import order; run `rush lint:fix` before committing. Use `PascalCase` for React components and classes, `camelCase` for variables/functions, and `SCREAMING_SNAKE_CASE` only for constants exported from config files. File names follow kebab-case (e.g., `flow-node-form.tsx`). Keep public API surfaces documented via barrel files such as `packages/canvas-engine/core/src/index.ts`.

## Testing Guidelines
Unit tests use Vitest and live beside source in `__tests__` folders or `*.test.ts` files; prefer descriptive names like `node-service.test.ts`. Ensure new logic is covered by `rush test`, and include data fixtures where possible. Playwright specs under `e2e/*/tests` cover critical workflows—coordinate UI changes with updated snapshots and run `rush e2e:test --to <package>` to scope failures.

## Commit & Pull Request Guidelines
Follow conventional commits (`type(scope): subject`) as seen in history (`fix(auto-layout): ...`). Keep subjects imperative and ≤72 characters, with optional bodies for context. PRs must describe the change, link GitHub issues, and attach before/after screenshots for UI updates. Confirm CI status, note any follow-ups, and request reviewers from the owning package tags (see `rush.json`).
