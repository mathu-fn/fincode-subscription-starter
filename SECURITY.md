# Security Policy

このプロジェクトは fincode の定期課金を扱うリファレンス実装です。決済まわりのコードを含むため、脆弱性は **必ず非公開で報告** してください。

## サポート対象バージョン

`main` ブランチの最新コミットのみがサポート対象です。タグ付きリリースを始めるまでは、フォーク先で固定したバージョンに対するサポートは行いません。

## 脆弱性の報告方法

公開 Issue や Pull Request を作成しないでください。代わりに **GitHub の Private Vulnerability Reporting** を使ってください。

1. リポジトリの **Security** タブを開く
2. **Report a vulnerability** をクリック
3. 再現手順・想定される影響範囲・修正案（あれば）を記入して送信

GitHub のドキュメント: <https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability>

報告には次を含めてください。

- 影響を受けるコンポーネント（`backend/app/...` のパス、API エンドポイント、フロント画面など）
- 再現手順（最小の curl / 画面操作）
- 想定される影響（情報漏えい、認可バイパス、決済の二重実行など）
- 既知の回避策・暫定対策があれば

## 報告に含めてはいけない情報

- **本番カード番号 (PAN) / CVC / 有効期限の組み合わせ**。fincode のテストカード番号を使ってください
- 実在ユーザーの JWT・パスワード・個人情報
- fincode の本番 API キー (`m_live_*` / `p_live_*`)。再現は必ずテストキー (`m_test_*` / `p_test_*`) で行ってください

## 対応の流れと想定スケジュール

| ステップ | 目安 |
| --- | --- |
| 受領確認 | 3 営業日以内 |
| 初回トリアージ（影響範囲・深刻度の確認） | 7 営業日以内 |
| 修正方針の共有 | 14 営業日以内 |
| パッチ公開 | 深刻度に応じて 30〜90 日以内を目標 |

修正後は GitHub Security Advisory として公開し、報告者のクレジット記載（希望者のみ）を行います。

## スコープ

このリポジトリで直接管理しているコードのみがスコープです。次のものは **対象外** です。

- fincode 本体の脆弱性 → fincode 提供元に直接報告してください
- ユーザーがフォーク・改変した派生リポジトリ
- このリポジトリ内のサンプル設定値 (`.env.example` など) を、そのまま本番にデプロイした場合の問題

## 既知のセキュリティ前提

設計上の必須ガード（カード情報の取り扱い、JWT、Webhook 署名検証、Idempotency-Key、レート制限など）は次のドキュメントにまとめています。

- [docs/customization/index.md（うっかり無効化してはいけないガード）](./docs/customization/index.md)
- [docs/architecture/error-handling.md](./docs/architecture/error-handling.md)
- [CLAUDE.md（コントリビューター向け制約）](./AGENTS.md)

これらの設計を逸脱する変更は、PR レビュー時に必ず指摘してください。

## フォーク後の自己診断チェックリスト

このリポジトリをフォークして本番投入する前に、少なくとも次を確認してください。

- 依存関係スキャン: Python と Node の lockfile
- Secret scan: `.env`、API key、JWT secret、fincode key
- OpenAPI と実装の差分
- CORS とセキュリティヘッダー
- レート制限が実際に効いているか
- IDOR（他ユーザーのリソースに触れないか）のテスト
- Webhook 署名検証と冪等性のテスト
- ログにシークレットや token が出ていないこと
