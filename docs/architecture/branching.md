# ブランチ運用 — develop ベースの Git Flow（簡易版）

このリポジトリは **`develop` を統合ブランチとする簡易 Git Flow** で運用します。長寿命ブランチは `main` と `develop` の 2 本だけで、release / hotfix 専用の長寿命ブランチは持ちません。

## 長寿命ブランチ

| ブランチ | 役割 | 直接 push |
| --- | --- | --- |
| `main` | リリース済みの状態。常にデプロイ可能。release-please がここを監視する | 禁止（PR 経由のみ） |
| `develop` | 次リリースの統合ブランチ。トピックブランチの分岐元・マージ先 | 禁止（PR 経由のみ） |

## 基本ルール

- **すべての作業は `develop` から分岐したトピックブランチで行う**。`main` から直接トピックブランチを切らない（例外はホットフィックスのみ、後述）。
- **トピックブランチの PR は `develop` 向け**に作成し、squash merge する。
- **`develop` → `main` はリリース PR**。squash せず**マージコミット**で取り込む（理由は「マージ方法」参照）。
- **トピックブランチは短命に**。マージされたら削除する。
- **PR は小さく、レビュー可能な粒度に**。1 PR で複数の関心事を混ぜない（コミットガイドラインも参照）。
- **CI green を必須**にする（リモートのブランチ保護で強制）。

## ブランチ名

`<prefix>/<short-kebab-summary>` 形式とします。機能追加は `feature/` を使います（コミットプレフィックスは従来どおり `feat:`）。それ以外はコミットプレフィックスと同名です。

| プレフィックス | 対応するコミットプレフィックス | 例 |
| --- | --- | --- |
| `feature/` | `feat:` | `feature/subscription-pause` |
| `fix/` | `fix:` | `fix/webhook-signature-mismatch` |
| `docs/` | `docs:` | `docs/getting-started-screenshots` |
| `refactor/` | `refactor:` | `refactor/fincode-client-retry` |
| `test/` | `test:` | `test/race-active-subscription` |
| `chore/` | `chore:` | `chore/bump-fastapi-0.115` |
| `security/` | `security:` | `security/jwt-rotation` |

Issue があれば `feature/123-subscription-pause` のように番号を入れてもよい。

## 標準フロー

```bash
git checkout develop
git pull --ff-only origin develop
git checkout -b feature/subscription-pause

# ... 編集・コミット ...
git push -u origin feature/subscription-pause

# PR は develop 向けに作成（gh CLI でもブラウザでも可）
gh pr create --base develop --head feature/subscription-pause \
  --title "feat: add subscription pause endpoint" \
  --body "..."
```

PR がマージされたら:

```bash
git checkout develop
git pull --ff-only origin develop
git branch -d feature/subscription-pause
git push origin --delete feature/subscription-pause  # リモート側を自動削除する設定なら不要
```

## マージ方法

| PR | マージ方法 | コミットメッセージ |
| --- | --- | --- |
| トピックブランチ → `develop` | **Squash merge** | PR タイトル（Conventional Commits 必須） |
| `develop` → `main`（リリース PR） | **マージコミット**（squash しない） | 自動生成のマージコミットで可 |

- トピックブランチの squash merge により、`develop` の履歴は 1 PR = 1 Conventional Commit に保たれ、bisect / revert が容易になる。**PR タイトルに `feat:` などのプレフィックスを必ず付ける**。
- `develop` → `main` を squash すると、複数の `feat:` / `fix:` が 1 コミットに潰れて **release-please がバージョンバンプと CHANGELOG を正しく生成できなくなる**。必ずマージコミットで取り込み、`develop` 上の個々のコミットを `main` に残すこと。
- 大規模 PR で個々のコミット履歴を `develop` に残したい場合のみ、レビュアー合意のうえで rebase merge を選ぶ。

## PR を作る前のチェックリスト

- [ ] `develop` を取り込んで rebase / merge 済み（コンフリクト解消済み）
- [ ] バックエンド: `cd backend && uv run pytest` が通る
- [ ] フロントエンド: `cd frontend && npm run test:run` が通る
- [ ] API 仕様変更を含む場合: `npx @redocly/cli lint docs/api/openapi.yml` が通る
- [ ] 秘密情報（`.env`、fincode キー、JWT シークレット、PAN/CVC）が含まれていない
- [ ] 関連ドキュメント（README / `docs/`）を更新済み

## ブランチ保護設定（推奨）

GitHub の Settings → Branches → Branch protection rules で設定する。

`main`:

- Require a pull request before merging
- Require status checks to pass before merging（CI）
- Restrict deletions
- Do not allow bypassing the above settings
- ※ `develop` からのマージコミットを受け入れるため、**Require linear history は有効にしない**

`develop`:

- Require a pull request before merging
- Require approvals: 1（レビュアーがいる体制なら）
- Require status checks to pass before merging（CI）
- Require linear history（squash merge のみなので維持できる）
- Restrict deletions

あわせて Settings → General → Pull Requests で **default branch を `develop`** にしておくと、PR のベース選び間違いを防げる。

## ホットフィックス

リリース済みの `main` に緊急修正が必要な場合のみ、`main` から `fix/...` ブランチを切って `main` 向けに PR を出します（squash merge、PR タイトルは `fix:`）。マージ後、**必ず `main` を `develop` に取り込む** PR を作成し、両ブランチの乖離を解消します。

```bash
git checkout main
git pull --ff-only origin main
git checkout -b fix/critical-webhook-crash
# ... 修正 → PR (base: main) → squash merge ...

# その後 main → develop へ反映
gh pr create --base develop --head main --title "chore: merge main back into develop"
```

## リリース / バージョニング

1. リリースしたい状態になったら `develop` → `main` の PR を作成し、**マージコミット**で取り込む。
2. `main` への push で release-please のワークフローが走り、Release PR（`vX.Y.Z`）が作成・更新される。
3. Release PR をマージすると GitHub Release とタグが自動作成される。
4. release-please が作るリリースコミットも `main` → `develop` に取り込んで同期する。

バンプ規則の詳細は `docs/architecture/commit-guidelines.md` と `release-please-config.json` を参照。
