# APIトークン運用

API は `POST /api/login` で発行する JWT Bearer token を使います。

## 既定モデル

- Access token は短命のJWT。
- レスポンスには `access_token`、`token_type`、`expires_at`、`user` を含める。
- リクエストでは `Authorization: Bearer <jwt>` を送る。
- バックエンドは署名、期限、設定している場合はissuer/audience、ユーザー状態を検証する。

## ローテーション

JWTは、サーバー側にトークン状態を持たない限り自然な単体失効ができません。forkでは次のどれかを選び、明記してください。

| 戦略 | トレードオフ |
| --- | --- |
| 短命access tokenのみ | 単純。ただし期限切れで再ログインが必要 |
| access + refresh token | UXは良いが、refresh token保存と失効管理が必要 |
| user行にtoken versionを持つ | パスワード変更やセキュリティ対応時に全tokenを失効可能 |
| サーバー側denylist | 単一token失効が可能。保存先と掃除が必要 |

スターターの既定は短命access tokenです。本番プロダクトでは refresh token または token version を追加することが多いです。

## 長期稼働クライアント

モバイルアプリ、監視ジョブ、botは次に対応してください。

- リクエスト前の期限検知。
- リクエスト後の `401 Unauthorized`。
- ログイン再試行の指数バックオフ。
- refresh token または保存資格情報の安全な保管。

## Secretローテーション

`JWT_SECRET_KEY` を変えると、複数検証キーをサポートしていない限り既存tokenは無効になります。

推奨する本番手順:

1. key ID (`kid`) と複数検証キーを実装。
2. 新しいキーで新規tokenへ署名開始。
3. 古いtoken期限が切れるまで旧キーを検証用に残す。
4. 旧キーを削除。

複数キーを実装しない場合は、再ログインが必要な時間帯を告知し、低トラフィック時に切り替えます。
