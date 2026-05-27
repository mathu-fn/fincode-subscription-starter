# データモデル

このスターターは PostgreSQL 16+、SQLAlchemy 2.x（async）、Alembic migration を使います。fincodeの識別子をローカルに保持し、フロントエンドには決済サービス内部の詳細を露出しない設計です。

JSONB カラム（`plan_snapshot`、`fincode_response`、`audit_logs.before/after`）と partial unique index（active 契約の一意性）を活用するため、SQLite では代替できません。

## ER図

```mermaid
erDiagram
    users ||--o| fincode_customers : "1:1"
    users ||--o{ fincode_cards : "1:N"
    users ||--o{ subscriptions : "1:N"
    users ||--o{ audit_logs : "1:N"
    fincode_customers ||--o{ fincode_cards : "1:N"
    fincode_customers ||--o{ subscriptions : "1:N"
    fincode_cards ||--o{ subscriptions : "1:N"
    subscriptions ||--o{ subscription_results : "1:N"

    users {
        bigint id PK
        string email UK
        string password_hash
        string name
        datetime created_at
        datetime updated_at
    }
    fincode_customers {
        bigint id PK
        bigint user_id FK
        string fincode_customer_id UK
        datetime synced_at
    }
    fincode_cards {
        bigint id PK
        bigint user_id FK
        bigint fincode_customer_id FK
        string fincode_card_id UK
        string brand
        string last4
        int exp_month
        int exp_year
        datetime deleted_at
    }
    subscriptions {
        bigint id PK
        bigint user_id FK
        bigint fincode_customer_id FK
        bigint fincode_card_id FK
        string fincode_subscription_id UK
        string fincode_plan_id
        string plan_name
        int plan_amount
        string plan_interval
        json plan_snapshot
        string status
        datetime cancelled_at
    }
    subscription_results {
        bigint id PK
        bigint subscription_id FK
        string fincode_subscription_id
        string fincode_payment_id
        string status
        int amount
        datetime charged_at
        json fincode_response
    }
    audit_logs {
        bigint id PK
        bigint user_id FK
        string event
        string auditable_type
        bigint auditable_id
        json before
        json after
        datetime created_at
    }
    webhook_events_seen {
        bigint id PK
        string fincode_event_id UK
        string event_type
        datetime received_at
        string dlq_reason
    }
```

## 各テーブルの意図

`users` はアプリ側のアイデンティティとパスワードハッシュを保持します。パスワードは passlib や pwdlib などのPython向けライブラリで bcrypt/argon2 を使って保存します。

`fincode_customers` はローカルユーザーと fincode customer ID を 1:1 で対応させます。初回カード登録または契約操作時に遅延作成します。

`fincode_cards` は brand、last4、有効期限、fincode card ID だけを保持します。PAN と CVC は保存しません。過去契約や監査ログを説明できるよう、カードは物理削除ではなく soft delete を基本にします。

`subscriptions` は現在および過去の契約行を保持します。契約作成時点の fincode プラン情報をスナップショット保存し、後から fincode 側でプラン名や金額が変わっても過去契約の意味が変わらないようにします。

`subscription_results` は課金ごとの webhook または照合結果です。Webhook の冪等性には `(fincode_subscription_id, fincode_payment_id)` をキーにした upsert を使います。

`audit_logs` は業務操作の証跡です。誰が何をいつ変えたかを記録し、HTTPリクエスト本文やシークレットは入れません。

## 制約

- `users.email` は unique。
- `fincode_customers.user_id` は unique にし、1ユーザー1カスタマーを保証する。
- アクティブ契約は1ユーザー1件に制限する。PostgreSQL の partial unique index を使う：
  ```python
  op.create_index(
      "uq_subscriptions_active_user",
      "subscriptions",
      ["user_id"],
      unique=True,
      postgresql_where=sa.text("status = 'active'"),
  )
  ```
- 所有関係には外部キーを張る。
- カード削除後も請求履歴と監査ログは説明可能な状態を残す。

## マイグレーション方針

スキーマ変更は Alembic で行います。共有環境に適用済みの migration は編集せず、新しい migration を追加します。原則として downgrade を実装し、forward-only にする場合は理由を明記します。
