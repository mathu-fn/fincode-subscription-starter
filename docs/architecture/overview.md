# アーキテクチャ概要

React + FastAPI のサブスクリプションスターターで、リクエストがどのレイヤを通るかをまとめます。

## 全体構成図

```mermaid
flowchart LR
    Browser["ブラウザ (React + Vite)"]
    Api["FastAPI router<br/>app/api/*"]
    Deps["Dependency<br/>auth / DB session / rate limit"]
    Managers["ドメインサービス<br/>SubscriptionManager / CardManager / CustomerSyncService / AuditLogger"]
    Fincode["Fincodeサービス<br/>FincodeClient / CustomerService / CardService / PlanService / SubscriptionService"]
    Breaker["CircuitBreaker"]
    DB[("PostgreSQL<br/>users / fincode_customers / fincode_cards<br/>subscriptions / subscription_results / audit_logs / webhook_events_seen")]
    FincodeApi(("fincode API"))
    Worker["バックグラウンドワーカー<br/>webhook / ドメインイベント副作用"]

    Browser -->|REST + JWT| Api
    Api --> Deps
    Deps --> Managers
    Managers --> DB
    Managers --> Fincode
    Fincode --> Breaker
    Fincode --> FincodeApi
    Managers -. events .-> Worker
    Worker --> DB
```

ブラウザが fincode を直接呼び出すのはカードトークン化だけです。FastAPI はトークンのみを受け取り、カスタマー、カード、プラン、サブスクリプション、Webhook処理をサーバー側で行います。

## レイヤごとの責務

| レイヤ | 主な場所 | 責務 | やってはいけないこと |
| --- | --- | --- | --- |
| React UI | `frontend/src/` | 画面、フォーム、fincode.jsトークン化、API呼び出し | カード番号やCVCを保持する |
| API router | `app/api/` | ルート定義、request/response schema、dependency接続 | 業務ワークフローを持つ |
| Dependency | `app/api/deps.py`, `app/core/security.py` | JWT検証、current user、DB session、rate limit | fincodeを直接呼ぶ |
| ドメインサービス | `app/services/` | 契約・カード操作、トランザクション、監査ログ | HTTPリクエスト詳細を知る |
| Fincodeサービス | `app/services/fincode/` | 業務呼び出しをfincode APIへ変換 | ローカルDBを直接触る |
| Model | `app/models/` | SQLAlchemy永続化マッピング | 公開APIレスポンスを直接担う |
| Schema | `app/schemas/` | Pydanticバリデーションとレスポンス契約 | DBクエリを発行する |

## シーケンス: カード登録

```mermaid
sequenceDiagram
    autonumber
    participant U as ユーザー
    participant FJS as fincode.js
    participant API as FastAPI Card Router
    participant CM as CardManager
    participant CSS as CustomerSyncService
    participant CS as CardService
    participant FC as FincodeClient
    participant FA as fincode API
    participant DB as PostgreSQL

    U->>FJS: PAN / 有効期限 / CVC 入力
    FJS->>FA: ブラウザでカードトークン化
    FA-->>FJS: card token
    U->>API: POST /api/subscription/cards { token }
    API->>API: Pydantic schema と JWT を検証
    API->>CM: register(user, token)
    CM->>DB: トランザクション開始
    CM->>CSS: ensure_fincode_customer(user)
    CSS->>FC: POST /v1/customers with Idempotency-Key
    FC->>FA: カスタマー作成または取得
    CSS->>DB: fincode_customers upsert
    CM->>CS: create_card(customer_id, token)
    CS->>FC: POST /v1/customers/.../cards
    FC->>FA: カード登録
    CM->>DB: fincode_cards と audit_logs を保存
    CM->>DB: commit
    API-->>U: 201 Created
```

不変条件:

- PAN と CVC は FastAPI に到達しない。
- 1回のfincode書き込みに対する再試行では同じ Idempotency-Key を使う。
- ローカルDB更新は1トランザクションで行う。
- fincode成功後にローカル保存が失敗した場合は、同期ジョブまたは運用ツールで突合する。

## シーケンス: サブスクリプション登録

```mermaid
sequenceDiagram
    autonumber
    participant U as ユーザー
    participant API as FastAPI Subscription Router
    participant SM as SubscriptionManager
    participant PS as PlanService
    participant SS as SubscriptionService
    participant FC as FincodeClient
    participant FA as fincode API
    participant DB as PostgreSQL
    participant W as Worker

    U->>API: POST /api/subscription { fincode_plan_id, card_id }
    API->>API: schema、JWT、所有権を検証
    API->>SM: subscribe(user, plan_id, card_id)
    SM->>DB: アクティブ契約を確認
    SM->>PS: fetch_plan(plan_id)
    PS->>FC: GET /v1/plans/{plan_id}
    FC->>FA: プラン取得
    SM->>DB: トランザクション開始
    SM->>SS: create_subscription(customer, card, plan)
    SS->>FC: POST /v1/subscriptions
    FC->>FA: 契約作成
    SM->>DB: 契約スナップショットと監査ログを保存
    SM->>DB: commit
    SM-.->W: ドメインイベント発行
    API-->>U: 201 Created
```

不変条件:

- 1ユーザーは最大1つのアクティブ契約だけを持つ。
- プラン名、金額、間隔、fincodeの生ペイロードは契約行へスナップショット保存する。
- ドメインイベントはトランザクション commit 後に発火する。

## バックグラウンド処理

Webhook処理、通知、照合、下流プロビジョニングなどの遅い副作用はワーカープロセスで扱います。Celery、RQ、Dramatiq、軽量なasync task runnerなどを選べますが、API契約はワーカー実装に依存させません。

## 次に読むもの

- [data-model.md](./data-model.md)
- [error-handling.md](./error-handling.md)
- [../api/openapi.yml](../api/openapi.yml)
