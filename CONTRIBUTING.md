# Contributing

fincode Subscription Starter への貢献に興味を持っていただきありがとうございます。このドキュメントはバグ報告から Pull Request までの流れを最短でまとめます。詳細な開発ガイドは [`AGENTS.md`](./AGENTS.md) と [`docs/`](./docs/) を参照してください。

## 行動規範

このプロジェクトは [Contributor Covenant v2.1](./CODE_OF_CONDUCT.md) を採用しています。Issue / PR / Discussions すべての場で適用されます。

## 報告のしかた

| 種別 | 経路 |
| --- | --- |
| バグ報告 | GitHub Issue（`bug_report` テンプレート） |
| 機能要望 | GitHub Issue（`feature_request` テンプレート） |
| 脆弱性 | **公開せず** [SECURITY.md](./SECURITY.md) の手順で報告 |
| 質問・相談 | GitHub Discussions（有効化されていれば） |

再現条件には fincode テスト環境キー (`m_test_*` / `p_test_*`) と fincode の **テストカード番号** を使ってください。本番 PAN / CVC は絶対に Issue へ貼り付けないでください。

## 開発環境セットアップ

前提と起動コマンドは [README のクイックスタート](./README.md#クイックスタート) に従ってください。最低限の流れは次のとおりです。

```bash
git clone https://github.com/ltac0203-pixel/fincode-subscription-starter.git
cd fincode-subscription-starter
cp .env.example .env   # FINCODE_API_KEY / FINCODE_PUBLIC_KEY / FINCODE_WEBHOOK_SECRET を埋める

docker compose up -d postgres
cd backend && uv sync && uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# 別ターミナル
cd frontend && npm install && npm run dev
```

## ブランチとコミット

- **ブランチ戦略**: GitHub Flow。`main` は常にデプロイ可能。短命なトピックブランチを切り、PR で squash merge。詳細は [`docs/architecture/branching.md`](./docs/architecture/branching.md)。
- **コミットプレフィックス**: `feat / fix / docs / test / refactor / chore / security`。詳細は [`docs/architecture/commit-guidelines.md`](./docs/architecture/commit-guidelines.md)。
- **コミット粒度**: API 契約 (`docs/api/openapi.yml`) / React UI / SQLAlchemy・Alembic スキーマ / fincode 連携 / テストは独立してリバート可能になるように分けてください。

## 変更を出す前にローカルで通すもの

```bash
# バックエンド
cd backend
uv run pytest

# フロントエンド
cd ../frontend
npm run test:run
npm run build       # 型チェックも兼ねる

# OpenAPI
npx @redocly/cli lint docs/api/openapi.yml
```

バックエンドの統合テストは `testcontainers-python` で PostgreSQL 16 を起動するため、Docker Desktop が動いている必要があります。

## Pull Request チェックリスト

PR を出す前に確認してください。

- [ ] `main` から切ったトピックブランチで作業している
- [ ] コミットがプレフィックス規約に従い、粒度が分かれている
- [ ] 上記「ローカルで通すもの」がすべて成功している
- [ ] API 契約を変更した場合 `docs/api/openapi.yml` を更新し、Redocly lint が通る
- [ ] DB スキーマを変更した場合 Alembic revision を新規追加した（既存 revision は編集しない）
- [ ] UI 変更には Before / After スクリーンショットを添付
- [ ] PR 本文に **検証コマンド** と **関連 Issue** を明記

## アーキテクチャ上の不変条件（必読）

これらに反する変更はマージできません。

- PAN / CVC / 生のカードトークン化情報はバックエンドに来ない（ブラウザの `fincode.js` がトークン化）
- fincode 直接呼び出しは `app/services/fincode/` だけ（Manager / API ルートから `httpx` を直接呼ばない）
- fincode 4xx / 429 はリトライしない。5xx / タイムアウトのみリトライし、Idempotency-Key を再利用する
- fincode の生レスポンスをクライアントへ返さない（`app/core/exceptions.py` の型付き例外に翻訳）
- 1 ユーザー = 最大 1 アクティブ契約。partial unique index で保証
- カードは soft delete（`fincode_cards.deleted_at`）

詳細は [`AGENTS.md`](./AGENTS.md) と [`docs/architecture/overview.md`](./docs/architecture/overview.md) を参照してください。

## リリースとバージョニング

バージョン管理は [release-please](https://github.com/googleapis/release-please) で自動化しています。仕組み:

1. **コミットメッセージが Conventional Commits 準拠であること**。GitHub Flow + squash merge では **PR のタイトル** が main 上のコミットメッセージになるため、PR タイトルを `feat:` / `fix:` / `security:` などのプレフィックスで始めること（[コミットガイドライン](./docs/architecture/commit-guidelines.md)）。
2. main へマージするたびに release-please のワークフロー（`.github/workflows/release-please.yml`）が走り、**Release PR** を自動で作成・更新する。`CHANGELOG.md`、`backend/pyproject.toml`、`frontend/package.json` のバージョンがその PR で同期更新される。
3. Release PR を **マージすると GitHub Release とタグ（`vX.Y.Z`）が自動作成される**。

### バージョン番号の決まり方

- [Semantic Versioning](https://semver.org/spec/v2.0.0.html) に従う
- `0.x` の間（pre-1.0）は、`feat:` で **minor** が、`fix:` で **patch** が上がる設定（`bump-minor-pre-major`）
- 破壊的変更は `feat!:` / `fix!:` のように `!` を付けるか、コミット本文に `BREAKING CHANGE: ...` を含める。pre-1.0 でも minor 扱いになる
- `docs:` / `test:` / `chore:` 単独ではバージョンは上がらない（CHANGELOG にも非表示）

### 1.0.0 を切るタイミング

API（`docs/api/openapi.yml`）と DB スキーマが本番運用に耐える形で安定したと判断したタイミングで、Release PR を手動で 1.0.0 に書き換えてマージするか、コミットで `Release-As: 1.0.0` を指定します。

## ライセンス

このリポジトリへの貢献は [Apache License, Version 2.0](./LICENSE) のもとで配布されることに同意したものとみなされます。
