![Image](https://github.com/user-attachments/assets/4f9dfa0e-e600-4d4e-9e73-c919184f7573)

<div align="center">

[![License](https://img.shields.io/github/license/bytedance/flowgram.ai)](https://github.com/bytedance/flowgram.ai/blob/main/LICENSE) [![@flowgram.ai/editor](https://img.shields.io/npm/dm/%40flowgram.ai%2Fcore)](https://www.npmjs.com/package/@flowgram.ai/editor)

</div>

# FlowGram｜Workflow Studio

[English](README.md) | [中文](README_ZH.md) | [Español](README_ES.md) | [Русский](README_RU.md) | [Português](README_PT.md) | [Deutsch](README_DE.md) | [日本語](README_JA.md)

[FlowGram.AI](https://flowgram.ai) フレームワーク上に構築された、ビジュアルワークフローエディターと実行バックエンド。フリーレイアウトキャンバス上で AI / エージェントパイプライン（HTTP リクエスト、LLM 呼び出し、コード、条件分岐、ループ、MCP / エージェントノード）を組み立て、サーバー側で実行できます。

本リポジトリは 2 つのアプリケーションで構成されています：

- **`apps/flow-studio`** — ブラウザエディター（React + Rsbuild）。編集したワークフローはバックエンドに永続化され、サーバーモードで実行されます。
- **`apps/flow-backend`** — tRPC + Prisma（MySQL）サーバー。ワークフローを永続化し（保存時のシークレット暗号化付き）、ランタイムで実行し、エディターが呼び出す実行 API を提供します。

## 🚀 クイックスタート

### 前提条件

- Node.js 18+ および pnpm 10.6.5（Rush がバージョンを強制します）
- MySQL データベース（例：ローカルの Docker コンテナ）

### 1. 依存関係のインストール

```sh
git clone <repo-url> && cd flowgram.ai
npx @microsoft/rush install
```

### 2. バックエンドの設定

```sh
cd apps/flow-backend
cp .env.example .env        # その後、値を編集します（DATABASE_URL、FLOWGRAM_ENCRYPTION_KEY、...）
```

暗号化キーを生成し、データベースマイグレーションを実行します：

```sh
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"  # -> FLOWGRAM_ENCRYPTION_KEY
rushx db:generate           # Prisma クライアントを生成
rushx db:migrate            # スキーマを作成（MySQL）
```

### 3. 起動

2 つのターミナルで実行します：

```sh
# ターミナル 1 — バックエンド（デフォルト http://localhost:4000）
cd apps/flow-backend && rushx dev

# ターミナル 2 — スタジオエディター（デフォルト http://localhost:3000）
cd apps/flow-studio && rushx dev
```

> エディターはデフォルトで `http://localhost:4100` に通信します（`apps/flow-studio/src/api/trpc.ts` を参照）。バックエンド向けに変更するには、`window.__FLOW_BACKEND_URL__` を設定するか定数を編集してください。また、バックエンドの `.env` の `CORS_ORIGIN` をエディターのオリジンに合わせてください。

プル後にすべてのパッケージを再ビルドするには：

```sh
rush build
```

## ✨ 特徴

| 特徴 | 説明 |
| --- | --- |
| [Free Layout Canvas](https://flowgram.ai/examples/free-layout/free-feature-overview.html) | フリーレイアウトキャンバス。ノードは任意の位置に配置でき、自由形式の線で接続できます。 |
| [Fixed Layout Canvas](https://flowgram.ai/examples/fixed-layout/fixed-feature-overview.html) | 固定レイアウトキャンバス。ドラッグで位置調整でき、分岐やループなどの複合ノードをサポートします。 |
| [Form](https://flowgram.ai/examples/node-form/basic.html) | ノード設定用のフォームエンジン：レンダリング、バリデーション、副作用、連動、エラー捕捉を提供します。 |
| [Variable](https://flowgram.ai/guide/variable/basic.html) | 変数エンジン。スコープ制約、構造検査、型推論をサポートします。 |
| サーバーランタイム | ワークフローはバックエンドで実行され（`task/run`、`task/validate`、...）、エディターはサーバーモードで呼び出します。 |
| シークレット暗号化 | MCP / エージェントノードのヘッダーシークレットは保存時に暗号化され、読み取り時に透過的に復号されます。 |

## 📦 プロジェクト構成

```
apps/
  flow-studio/      ブラウザエディター（React + Rsbuild）
  flow-backend/     tRPC + Prisma サーバー（MySQL）
packages/           FlowGram フレームワークライブラリ（キャンバスエンジン、ノードエンジン、ランタイム、プラグイン）
common/             Rush ツールと自動インストーラー
config/             共有 eslint / tsconfig プリセット
e2e/                Playwright スイート（シナリオ別）
```

## 📖 フレームワークドキュメント

本アプリは FlowGram.AI フレームワーク上に構築されています。フレームワークレベルのドキュメントは [flowgram.ai](https://flowgram.ai) にあります（クイックスタート、キャンバス、フォーム、変数、マテリアル、ランタイム、API リファレンス）。

## License

[MIT](LICENSE)
