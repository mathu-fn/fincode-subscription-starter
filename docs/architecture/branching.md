# ブランチ運用 — GitHub Flow

このリポジトリは **GitHub Flow** で運用します。Git Flow のような長寿命の develop/release ブランチは持たず、`main` を常にデプロイ可能な状態に保ちます。

## 基本ルール

- **`main` は常にデプロイ可能**。直接 push しない。すべての変更は PR を経由する。
- **作業は短命なトピックブランチで**。`main` から分岐し、PR がマージされたら削除する。
- **PR は小さく、レビュー可能な粒度に**。1 PR で複数の関心事を混ぜない（コミットガイドラインも参照）。
- **CI green と承認 1 件以上を必須**にする（リモートのブランチ保護で強制）。

## ブランチ名

`<prefix>/<short-kebab-summary>` 形式を推奨します。プレフィックスは `docs/architecture/commit-guidelines.md` のコミットプレフィックスと揃えます。

| プレフィックス | 例 |
| --- | --- |
| `feat/` | `feat/subscription-pause` |
| `fix/` | `fix/webhook-signature-mismatch` |
| `docs/` | `docs/getting-started-screenshots` |
| `refactor/` | `refactor/fincode-client-retry` |
| `test/` | `test/race-active-subscription` |
| `chore/` | `chore/bump-fastapi-0.115` |
| `security/` | `security/jwt-rotation` |

Issue があれば `feat/123-subscription-pause` のように番号を入れてもよい。

## 標準フロー

```bash
git checkout main
git pull --ff-only origin main
git checkout -b feat/subscription-pause

# ... 編集・コミット ...
git push -u origin feat/subscription-pause

# PR を作成（gh CLI でもブラウザでも可）
gh pr create --base main --head feat/subscription-pause \
  --title "feat: add subscription pause endpoint" \
  --body "..."
```

PR がマージされたら:

```bash
git checkout main
git pull --ff-only origin main
git branch -d feat/subscription-pause
git push origin --delete feat/subscription-pause  # リモート側を自動削除する設定なら不要
```

## マージ方法

**Squash merge を既定**とします。

- main の履歴を 1 PR = 1 コミットに保ち、bisect / revert を容易にする
- コミットメッセージは PR タイトルを使い、`feat: ...` などのプレフィックスを必ず付ける
- 大規模 PR で個々のコミット履歴を残したい場合のみ、レビュアー合意のうえで rebase merge を選ぶ

通常の merge コミット（マージコミット作成）は使いません。

## PR を作る前のチェックリスト

- [ ] `main` を取り込んで rebase / merge 済み（コンフリクト解消済み）
- [ ] バックエンド: `cd backend && uv run pytest` が通る
- [ ] フロントエンド: `cd frontend && npm run test:run` が通る
- [ ] API 仕様変更を含む場合: `npx @redocly/cli lint docs/api/openapi.yml` が通る
- [ ] 秘密情報（`.env`、fincode キー、JWT シークレット、PAN/CVC）が含まれていない
- [ ] 関連ドキュメント（README / `docs/`）を更新済み

## main の保護設定（推奨）

GitHub の Settings → Branches → Branch protection rules で `main` に対して次を有効化:

- Require a pull request before merging
- Require approvals: 1
- Require status checks to pass before merging（CI を追加したら必須にする）
- Require linear history
- Restrict deletions
- Do not allow bypassing the above settings

## ホットフィックス

緊急修正も同じフローで `fix/...` ブランチを作って PR します。GitHub Flow には hotfix 専用の派生ブランチはありません。

## リリース / バージョニング

リリースが必要な段階に来たら、GitHub の Releases 機能と git tag（`v0.1.0` など SemVer）で管理します。リリースブランチは作らず、main からタグを切ります。
