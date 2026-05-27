# カスタマイズガイド

このスターターはforkして自社のサブスクリプション製品へ取り込む前提です。

## 本番前に変更する箇所

| 領域 | 主なファイル | 補足 |
| --- | --- | --- |
| プロダクト識別子 | `README*`, `pyproject.toml`, `package.json` | package名、repository、homepage、support linkを変更 |
| 実行時設定 | `.env.example`, `app/core/config.py` | URL、secret、allowed origins のplaceholderを置換 |
| ブランディング | `frontend/src/` | ロゴ、色、文言、画面レイアウト |
| 認証ポリシー | `app/core/security.py`, `app/api/deps.py` | JWT寿命、パスワードポリシー、トークン失効方針 |
| 法務文言 | frontendのlegal pages | 利用規約、プライバシーポリシー、特商法表記 |
| デプロイ | infrastructure files | ドメイン、TLS、プロセスマネージャ、secret store |

## プランと料金

サブスクリプションプランの正本は fincode です。アプリは実行時に契約可能プランを取得し、契約時点のプラン情報を `subscriptions` 行へスナップショット保存します。

プラン追加・変更:

1. fincode管理画面でプランを作成または編集する。
2. `plan_xxx` ID を控える。
3. フロントエンドがラベル、並び順、説明文を固定している場合は表示を更新する。

プロダクト側でプラン設定を所有する明確な理由がない限り、可変のローカル `plans` テーブルは追加しないでください。

## 拡張しやすい箇所

| 目的 | 着手地点 |
| --- | --- |
| メール認証 | Auth service、user model、email sender、保護route dependency |
| 1ユーザー複数アクティブ契約 | active subscription unique制約と契約UIを見直す |
| クーポン | 権威をfincode側に置くかローカルに置くか決め、優先順位を文書化 |
| Webhook駆動のDunning | [webhooks.md](./webhooks.md) |
| 外部連携 | DB commit後にserviceからdomain eventを発行 |

## 静かに無効化しないガード

| ガード | 理由 |
| --- | --- |
| fincodeログのマスク | token、カード情報、secret漏洩を防ぐ |
| fincode書き込みのIdempotency-Key | 再試行時の二重カード/二重契約を防ぐ |
| 状態変更を囲むDBトランザクション | ローカルDBの部分書き込みを防ぐ |
| 監査ログ | 業務証跡を残す |
| JWT検証dependency | ユーザーリソースへの匿名アクセスを防ぐ |
| 所有権チェック | 他ユーザーのカード/契約アクセスを防ぐ |
| レート制限 | ブルートフォースと課金濫用を減らす |
| アクティブ契約の一意制約 | レースによる二重契約を防ぐ |

## 生成物とvendor

仮想環境、依存キャッシュ、ローカルビルド成果物、`.env`、coverage report、frontend build artifact は、リポジトリで明示的に必要とされない限りコミットしません。
