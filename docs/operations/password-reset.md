# パスワードリセット

スターターでは、メールプロバイダ、token保存、アカウント復旧ポリシーを採用側が選べるよう、完全なパスワードリセットフローを同梱しない場合があります。

## 推奨設計

- 単回利用のreset tokenを生成する。
- tokenはハッシュだけを保存し、user ID、期限、使用済み時刻を持つ。
- 生tokenはメールの期限付きreset URLとして送る。
- reset時はtoken hash、期限、未使用状態を検証する。
- パスワードハッシュを更新し、認証モデルが対応していれば既存tokenを失効する。
- token自体をログに出さず、完了イベントだけを監査ログに残す。

## 推奨エンドポイント

```text
POST /api/password/forgot
POST /api/password/reset
```

登録済みメールの列挙を防ぐため、forgot-password endpoint は汎用レスポンスを返します。

## セキュリティ注意点

- 有効期限は30分から60分など短くする。
- email と IP でレート制限する。
- reset tokenをログに出さない。
- 使用済みtokenは失効する。
- パスワードリセット後は、既存JWTのtoken version失効を検討する。
