# カスタマイズガイド

このスターターは、fork して自社のサブスクリプション製品に取り込んで使う前提です。

## 本番前に変更する箇所

| 領域 | 主なファイル | 補足 |
| --- | --- | --- |
| プロダクト識別子 | `README*`, `pyproject.toml`, `package.json` | package 名、repository、homepage、サポートリンクを変更 |
| 実行時設定 | `.env.example`, `app/core/config.py` | URL、secret、許可する origin のプレースホルダを置き換える |
| ブランディング | `frontend/src/` | ロゴ、色、文言、画面レイアウト |
| 認証ポリシー | `app/core/security.py`, `app/services/google_identity.py`, `app/api/deps.py` | JWT の有効期限、Google クライアント ID、トークン無効化の方針 |
| 法務文言 | frontend の legal ページ | 利用規約、プライバシーポリシー、特商法表記 |
| デプロイ | インフラ関連ファイル | ドメイン、TLS、プロセスマネージャ、secret store |

## プランと料金

サブスクリプションプランのマスター（一次情報）は fincode 側にあります。アプリは実行時に契約可能なプランを取得し、契約した時点のプラン情報を `subscriptions` の行にスナップショット保存します。

プラン追加・変更:

1. fincode管理画面でプランを作成または編集する。
2. `plan_xxx` ID を控える。
3. フロントエンドがラベル、並び順、説明文を固定している場合は表示を更新する。

プロダクト側でプラン設定を管理する明確な理由がない限り、変更可能なローカルの `plans` テーブルは追加しないでください。

## 単一契約のプラン変更

このスターターは `PATCH /api/subscription` で、既存のアクティブ契約を解約せずに同じ `subscriptions` 行のプラン情報を更新します。1ユーザー1アクティブ契約の partial unique index は維持したまま、有料プラン同士の変更では fincode のサブスクリプション更新 API に新しい `plan_id` を渡します。

フリープランはアプリ側の合成プランなので、free から有料プランへ変更する場合だけ `card_id` が必要です。有料プランから free へ変更する場合は fincode 側のサブスクリプションを停止し、ローカル行を free に更新します。

解約予約中（`cancel_at_period_end=true`）の契約は、支払い済み期間の利用権を守るため `current_period_end` まで `active` のまま保持します。この状態ではプラン変更を受け付けません。

このスターターは日割り（proration）を計算しません。即時差額請求、次回請求日からの適用、クレジット残高などを扱う場合は、`app/services/subscription_manager.py` の `change_plan` と `subscription_results` / 監査ログの記録方針を拡張してください。

## 拡張しやすい箇所

| 目的 | 着手地点 |
| --- | --- |
| メール認証 | Auth service、user model、メール送信サービス、保護ルートの dependency |
| 単一契約のプラン変更ルール（日割り・次回更新予約） | `SubscriptionManager.change_plan`、API schema、契約 UI |
| 1 ユーザー複数アクティブ契約 | アクティブ契約の unique 制約と契約 UI を見直す |
| クーポン | マスターを fincode 側に置くか、ローカルに置くかを決めて、優先順位をドキュメント化する |
| Webhook 駆動の支払い催促（Dunning） | [webhooks.md](./webhooks.md) |
| 外部連携 | DB commit 後に、サービス層からドメインイベントを発行する |

## うっかり無効化してはいけないガード

| ガード | 理由 |
| --- | --- |
| fincode ログのマスク | token、カード情報、シークレットの漏洩を防ぐ |
| fincode 書き込みの Idempotency-Key | 再試行時の二重カード登録 / 二重契約を防ぐ |
| 状態変更を囲む DB トランザクション | ローカル DB に中途半端な状態が残るのを防ぐ |
| 監査ログ | 業務上の操作記録を残す |
| JWT 検証 dependency | ユーザーのリソースに匿名でアクセスされないようにする |
| 所有権チェック | 他ユーザーのカード / 契約へのアクセスを防ぐ |
| レート制限 | 総当たり攻撃や課金の悪用を減らす |
| アクティブ契約の一意制約 | 同時アクセスによる二重契約を防ぐ |

## 生成物とvendor

仮想環境、依存キャッシュ、ローカルでのビルド成果物、`.env`、カバレッジレポート、フロントエンドのビルド成果物は、明示的に必要な場合を除いてコミットしません。
