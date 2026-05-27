<!-- タイトルは `feat:` / `fix:` / `docs:` / `test:` / `refactor:` / `chore:` / `security:` のいずれかで始めてください -->

## 概要

<!-- 何を、なぜ変えるか。1〜3 文で。 -->

## 変更内容

<!-- 主な変更点を箇条書きで。コミット粒度（API 契約 / UI / スキーマ / fincode 連携 / テスト）で揃っているか確認 -->

-
-

## 関連 Issue

Closes #<!-- 番号 -->

## 検証コマンド

```bash
# バックエンド
cd backend && uv run pytest

# フロントエンド
cd frontend && npm run test:run && npm run build

# OpenAPI
npx @redocly/cli lint docs/api/openapi.yml
```

## スクリーンショット

<!-- UI 変更がある場合のみ。Before / After を並べてください。 -->

## チェックリスト

- [ ] `main` から切ったトピックブランチで作業している
- [ ] コミットがプレフィックス規約（feat/fix/docs/test/refactor/chore/security）に従う
- [ ] 上記の検証コマンドがすべてローカルで成功した
- [ ] API 契約を変更した場合、`docs/api/openapi.yml` を更新し Redocly lint が通った
- [ ] DB スキーマを変更した場合、Alembic revision を **新規追加** した（既存 revision は編集しない）
- [ ] 機微情報（カード番号 / CVC / 本番 fincode キー / JWT / 個人情報）を diff・ログ・テストデータに含めていない
- [ ] [アーキテクチャ不変条件](../blob/main/CONTRIBUTING.md#アーキテクチャ上の不変条件必読) を壊していない
