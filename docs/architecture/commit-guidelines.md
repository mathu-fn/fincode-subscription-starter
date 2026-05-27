# コミットガイドライン

コミットは、レビューしやすく、単独で revert できる粒度にします。

## プレフィックス

| Prefix | 用途 |
| --- | --- |
| `feat` | ユーザーから見える機能追加 |
| `fix` | バグ修正 |
| `docs` | ドキュメントのみ |
| `test` | テスト追加・修正 |
| `refactor` | 挙動を変えない構造変更 |
| `chore` | ツール、依存、保守作業 |
| `security` | セキュリティ強化 |

## 粒度

次の変更は分けることを推奨します。

- API契約変更
- FastAPIバックエンドの挙動
- React UIの挙動
- SQLAlchemy/Alembic のスキーマ変更
- fincode連携変更
- テストとfixture

例:

```text
feat: add subscription status API
test: cover subscription status API
docs: document subscription status response
```

## 避けること

- UI リニューアルと API 契約変更を同じコミットに混ぜる。
- DB マイグレーションを、無関係な機能コミットに紛れ込ませる。
- フォーマットだけの変更と、挙動の変更を混ぜる。
- fincode キー、JWT シークレット、`.env` などの秘密情報をコミットする。

## レビュー観点

- タイトルが実際の変更内容を表しているか。
- 無関係な副作用を伴わずに revert できるか。
- API / schema の変更がドキュメントに反映されているか。
- migration と model が同期しているか。
- 変更箇所の近くにテストがあるか。

## release-please との関係

このリポジトリは [release-please](https://github.com/googleapis/release-please) でバージョン管理を自動化しています。コミットメッセージは Conventional Commits 互換である必要があります。

- GitHub Flow + squash merge では **PR のタイトル** が main 上のコミットメッセージになる。プレフィックスは必ず PR タイトルに付ける。
- `feat:` → pre-1.0 では minor バンプ、1.0 以降は minor バンプ
- `fix:` → patch バンプ
- `security:` → CHANGELOG の "Security" セクションに表示（バンプ規則は patch 相当）
- `docs:` / `refactor:` → CHANGELOG に表示するがバンプはしない（pre-1.0 設定）
- `test:` / `chore:` → CHANGELOG 非表示・バンプなし
- 破壊的変更は `feat!:` のように `!` を付けるか、本文に `BREAKING CHANGE: ...` を含める

CHANGELOG のセクション分け・バンプ規則は `release-please-config.json` を正とします。
