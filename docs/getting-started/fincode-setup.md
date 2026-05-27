# Fincodeセットアップ手順

このアプリケーションを動作させるには、[Fincode](https://www.fincode.jp/) のアカウントとAPIキーが必要です。テストモードであれば無料で利用できます。

## 1. Fincodeアカウントの取得

1. [Fincode](https://www.fincode.jp/) のサイトから新規登録（テナント作成）
2. メール認証を完了させ、管理画面 [https://management.test.fincode.jp/](https://management.test.fincode.jp/) にログイン

## 2. APIキーの取得

管理画面の `APIキー` メニューから以下を取得します。

| 環境変数                  | 取得元                                                                    | 用途                                                                        |
| ------------------------- | ------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| `FINCODE_API_KEY`         | APIキー → シークレットキー（`m_test_...`）                                | サーバー側からのAPI呼び出し用                                               |
| `FINCODE_PUBLIC_KEY`      | APIキー → 公開鍵（`p_test_...`）                                          | ブラウザでのカードトークン化用                                              |
| `FINCODE_BASE_URL`        | テスト: `https://api.test.fincode.jp` / 本番: `https://api.fincode.jp`    | APIエンドポイント                                                           |
| `FINCODE_TENANT_SHOP_ID`  | プラットフォーム／マルチテナントアカウントのみ                            | `Tenant-Shop-Id` HTTP ヘッダとして送信。単一ショップ運用なら未設定で OK。 |

これらを `.env` に設定してください。

> `FINCODE_TENANT_SHOP_ID` は **Fincode アカウントがプラットフォーム（マルチテナント）構成の場合のみ必須**です。通常の単一ショップ運用では未設定で問題なく、未設定時はヘッダが付きません。CI ではダミー値が設定されており、テスト起動時の参照エラーを防いでいます。

## 3. テスト用プランの作成

このアプリケーションでは、プラン情報はFincode側で管理し、サブスクリプション契約時にAPI経由で取得します。

1. Fincode管理画面 → `定期課金` → `プラン` → `新規作成`
2. プラン名・金額・課金間隔（月次/年次など）を設定
3. 作成されたプランのID（`plan_xxxxxx` 形式）を控える

複数のプランを作成しておくと、アプリケーションのプラン一覧画面で選択できるようになります。

## 4. テスト用カード情報

Fincodeのテストモードで動作確認する際は、以下のテストカード番号が利用できます。

| カード番号           | 種別   |
| -------------------- | ------ |
| `4111111111111111`   | Visa   |
| `5555555555554444`   | MasterCard |
| `3530111333300000`   | JCB    |

- 有効期限・CVCは任意の未来日・任意の3〜4桁数字でOK
- 詳細は [Fincode公式ドキュメント](https://docs.fincode.jp/) を参照

## 5. Webhook（任意）

サブスクリプションの定期課金結果を非同期で受け取る場合、Fincode管理画面でWebhookエンドポイントを設定します。このスターターで推奨するエンドポイントは次の通りです。

```text
https://your-api.example.com/api/webhooks/fincode
```

FastAPI handler の形、署名検証、冪等性要件は [../customization/webhooks.md](../customization/webhooks.md) を参照してください。

## 参考リンク

- [Fincode公式サイト](https://www.fincode.jp/)
- [Fincode開発者ドキュメント](https://docs.fincode.jp/)
- [Fincode APIリファレンス](https://docs.fincode.jp/api)
