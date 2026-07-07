# docs — ドキュメント目次

このディレクトリは **fincode Subscription Starter** のドキュメントを集約しています。React + FastAPI で Webアプリ向けサブスクリプション課金を実装するためのOSSリファレンスです。

想定する利用導線は次の通りです。

```text
クローン -> ローカル起動 -> fincodeテストアカウント接続 -> 自社サービスへ取り込み
```

プロジェクト全体の概要は [リポジトリ直下の README.md](../README.md) を参照してください。

## はじめての方へ

| ドキュメント | 内容 |
| --- | --- |
| [getting-started/quickstart.md](./getting-started/quickstart.md) | 起動コマンドと画面ごとの使い方を 1 ページに集約（最短経路） |
| [getting-started/local-development.md](./getting-started/local-development.md) | Python、uv、Node、DB、Alembic、FastAPI、React 開発サーバーのセットアップ |
| [getting-started/fincode-setup.md](./getting-started/fincode-setup.md) | Fincode テストアカウント、APIキー、プラン、テストカード |
| [getting-started/testing.md](./getting-started/testing.md) | pytest、Vitest、テストDB、fincodeモック方針 |

## アーキテクチャ

| ドキュメント | 内容 |
| --- | --- |
| [architecture/overview.md](./architecture/overview.md) | レイヤ責務、カード登録／契約登録のシーケンス図 |
| [architecture/data-model.md](./architecture/data-model.md) | ERモデル、各テーブルの意図、削除方針、外部キー |
| [architecture/error-handling.md](./architecture/error-handling.md) | 例外階層、Circuit Breaker、HTTPマッピング、再試行方針 |
| [architecture/commit-guidelines.md](./architecture/commit-guidelines.md) | コミット粒度・プレフィックス規約 |
| [architecture/branching.md](./architecture/branching.md) | ブランチ運用（GitHub Flow）、PR フロー、main 保護設定 |

## APIリファレンス

| ドキュメント | 内容 |
| --- | --- |
| [api/README.md](./api/README.md) | JWT認証、エンドポイント早見表、エラー形式、fincodeとの関係 |
| [api/openapi.yml](./api/openapi.yml) | 本アプリ REST API の OpenAPI 3.0.3 仕様 |

## カスタマイズ

| ドキュメント | 内容 |
| --- | --- |
| [customization/index.md](./customization/index.md) | 自社サービスへ取り込む際に変更する箇所 |
| [customization/webhooks.md](./customization/webhooks.md) | Fincode Webhook の設計と実装方針 |

## 運用

このスターターは特定のデプロイ環境を強制しません。以下は Linux でセルフホストする場合の参考資料です。

| ドキュメント | 内容 |
| --- | --- |
| [operations/configuration.md](./operations/configuration.md) | 環境変数リファレンス（`.env` の全キーと既定値・用途） |
| [operations/deployment.md](./operations/deployment.md) | 本番チェックリスト、Uvicorn、Nginx、マイグレーション、Webhook 受信 |
| [operations/api-token-rotation.md](./operations/api-token-rotation.md) | JWT寿命、更新・ローテーション、長期稼働クライアントの注意点 |

## セキュリティ

| ドキュメント | 内容 |
| --- | --- |
| [security/2026-05-vulnerability-audit.md](./security/2026-05-vulnerability-audit.md) | 脆弱性診断メモと FastAPI 実装時の確認ポイント |

## 紹介記事

| ドキュメント | 内容 |
| --- | --- |
| [articles/README.md](./articles/README.md) | Zenn / Qiita / dev.to 投稿用記事の下書きディレクトリ |

## リポジトリ直下

- [../README.md](../README.md) — プロジェクト概要・クイックスタート
