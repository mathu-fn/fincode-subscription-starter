---
title: "Fincode × FastAPI でサブスク決済を実装する — OSS スターター fincode-subscription-starter"
emoji: "💳"
type: "tech"
topics: ["fastapi", "python", "react", "fincode", "決済", "oss"]
published: false
---

> この記事は公開用の下書きです。Zenn を想定したフロントマターを付けています。Qiita / dev.to などへ転載する場合は、投稿先の形式へ置き換えてください。

## はじめに

[Fincode](https://www.fincode.jp/) は GMO ペイメントゲートウェイが提供する決済APIです。クレジットカード決済からサブスクリプション課金まで扱えるため、日本向けWebサービスの決済基盤として有力な選択肢です。

一方で、カード登録、定期課金、解約、決済履歴、Webhookまでを1つのWebアプリとしてどう組み立てるかは、公式APIリファレンスだけでは見えにくい領域です。

そこで、React + FastAPI で動くサブスクリプション課金のOSSスターターを用意しました。

**fincode-subscription-starter**
https://github.com/ltac0203-pixel/fincode-subscription-starter

## fincode-subscription-starter とは

Fincode 決済APIと統合した、サブスクリプション管理Webアプリのリファレンス実装です。

| レイヤ | 技術 |
| --- | --- |
| バックエンド | FastAPI + Python |
| フロントエンド | React + Vite + TypeScript |
| APIスキーマ | Pydantic |
| 認証 | JWT Bearer |
| データベース | PostgreSQL 16+ |
| ORM / マイグレーション | SQLAlchemy + Alembic |
| 決済 | fincode |
| テスト | pytest + Vitest |

## 何ができるか

- ユーザー登録 / ログイン
- fincode のプラン一覧取得
- fincode.js によるカードトークン化
- カード登録・削除
- サブスクリプション登録・解約
- 決済履歴
- 監査ログ
- Fincode Webhook の受信設計
- OpenAPI仕様

## 動かしてみる

```bash
git clone https://github.com/ltac0203-pixel/fincode-subscription-starter.git
cd fincode-subscription-starter

uv sync
npm install
cp .env.example .env
```

`.env` にDB接続情報、JWT secret、fincodeテストキーを入れます。

```bash
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

別ターミナルで:

```bash
npm run dev
```

ブラウザで `http://localhost:5173` を開きます。FastAPIのAPIドキュメントは `http://localhost:8000/docs` で確認できます。

## アーキテクチャ

リクエストは一方向に流れます。

```text
React -> FastAPI router -> Domain service -> FincodeClient -> fincode API
```

- FastAPI router は薄く保ち、Pydantic schema と dependency wiring を担当する。
- 業務ロジックは service 層に置く。
- fincode API へのHTTP呼び出しは FincodeClient に集約する。
- DB更新は SQLAlchemy session のトランザクションで囲む。

## 設計のポイント

### カード情報をサーバーに渡さない

カード番号とCVCはブラウザ上で fincode.js によりトークン化します。FastAPI にはトークンだけを送るため、アプリケーションサーバーはカード番号のフル値を扱いません。

### Idempotency-Key と Circuit Breaker

fincode の書き込みAPIには Idempotency-Key を付与し、ネットワーク再試行による二重登録を防ぎます。timeoutや5xxには指数バックオフを使い、連続失敗時は Circuit Breaker で fail fast します。

### 契約時点のプランスナップショット

プランの正本は fincode 管理画面です。ただし契約時点の金額や名称は `subscriptions` 行へスナップショット保存し、後からプランが編集されても過去契約の意味が変わらないようにします。

### 監査ログ

カード登録、契約、解約などの状態変更は `audit_logs` に記録します。誰が、いつ、何を変えたかを後から追えることは、決済を扱うサービスでは重要です。

## テスト

自動テストから実際の fincode API は呼びません。`FincodeClient` や service 層をモックし、FastAPI route、DB状態、監査ログ、例外のHTTPマッピングを検証します。

```bash
uv run pytest
npm run test
npx @redocly/cli lint docs/api/openapi.yml
```

## おわりに

Fincodeでサブスクリプション課金を実装したい人が、ゼロから設計を考える時間を減らせる出発点になればと思っています。
