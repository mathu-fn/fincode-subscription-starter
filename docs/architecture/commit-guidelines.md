# コミットガイドライン

コミットはレビューしやすく、単独でrevertできる粒度にします。

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

- UI刷新とAPI契約変更を同じコミットに混ぜる。
- DBマイグレーションを無関係な機能コミットに隠す。
- フォーマットのみの変更と挙動変更を混ぜる。
- fincodeキー、JWTシークレット、`.env` などの秘密情報をコミットする。

## レビュー観点

- タイトルが実際の変更内容を表しているか。
- 無関係な副作用なくrevertできるか。
- API/schema変更がドキュメント化されているか。
- migration と model が同期しているか。
- 変更箇所に近いテストがあるか。
