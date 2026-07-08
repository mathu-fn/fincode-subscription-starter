# Changelog

このファイルは [release-please](https://github.com/googleapis/release-please) が自動で更新します。手動編集はしないでください。

書式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) を参照し、バージョン番号は [Semantic Versioning](https://semver.org/spec/v2.0.0.html) に従います。

## [0.2.0](https://github.com/mathu-fn/fincode-subscription-starter/compare/v0.1.0...v0.2.0) (2026-07-08)


### ⚠ BREAKING CHANGES

* POST /api/register と POST /api/login を削除。 ログイン手段は POST /api/auth/google（Google 認証）のみになる。

### Features

* 0円フリープランの表示と契約に対応 ([#22](https://github.com/mathu-fn/fincode-subscription-starter/issues/22)) ([927c803](https://github.com/mathu-fn/fincode-subscription-starter/commit/927c8039c7efd45200266658e364881d9ff420b9))
* add ConfirmDialog component for modal confirmations ([8a16508](https://github.com/mathu-fn/fincode-subscription-starter/commit/8a165080aad4fe3ce6980a0fe5d349d00ff01c0f))
* add subscription plan changes ([9125a7b](https://github.com/mathu-fn/fincode-subscription-starter/commit/9125a7b0a95ab16d4a6d5b91531bb50ae9a29062))
* collapse new card form behind add-card button and tighten layout ([#18](https://github.com/mathu-fn/fincode-subscription-starter/issues/18)) ([32c0019](https://github.com/mathu-fn/fincode-subscription-starter/commit/32c001963c4e8dce605fa468170bb35241efd1db))
* confirm important actions (logout, card delete, cancel) via modal ([9997845](https://github.com/mathu-fn/fincode-subscription-starter/commit/999784504c09e3bf18bc7e2f1e71b1fa447a86c4))
* confirm logout, card deletion and cancellation via modal ([2de4f6f](https://github.com/mathu-fn/fincode-subscription-starter/commit/2de4f6f1c66b933d90ff97abe0a473b59f081784))
* expose /metrics endpoint via prometheus-fastapi-instrumentator ([3bd521d](https://github.com/mathu-fn/fincode-subscription-starter/commit/3bd521d9d3883e2f061c2c9b4dd12552e1874e5e))
* fincode アカウント不要のモックモードを追加し README を刷新 ([919f5b4](https://github.com/mathu-fn/fincode-subscription-starter/commit/919f5b44b5fcf608364e468dc0b6b6d60f80aa2e))
* Google 認証への一本化とバックエンド堅牢化 ([#57](https://github.com/mathu-fn/fincode-subscription-starter/issues/57)) ([31d7749](https://github.com/mathu-fn/fincode-subscription-starter/commit/31d7749f81875fd96c9ae0252694b82431d5ba3e))
* support cancel at period end ([#34](https://github.com/mathu-fn/fincode-subscription-starter/issues/34)) ([76fa170](https://github.com/mathu-fn/fincode-subscription-starter/commit/76fa170a91affcb688ac6ea828ad034f2d7c3372))
* カード追加フォームの読み込み中にローディングオーバーレイを表示 ([#20](https://github.com/mathu-fn/fincode-subscription-starter/issues/20)) ([e47df52](https://github.com/mathu-fn/fincode-subscription-starter/commit/e47df52fba4cc3d651a6391a87a71b265a2ca9e2))
* ホーム画面にステータスバッジ・スケルトン・確認ダイアログを導入 ([38ef0e3](https://github.com/mathu-fn/fincode-subscription-starter/commit/38ef0e334934b94ce552fe0f1c8166c7202c0bc1))


### Bug Fixes

* plan service とサブスク周りのタイムゾーン/整合性修正 ([#49](https://github.com/mathu-fn/fincode-subscription-starter/issues/49)) ([867c3bd](https://github.com/mathu-fn/fincode-subscription-starter/commit/867c3bd380d3a9963f72dc6199678a1b6dca32ca))
* repair fincode subscription cancel and paid plan change flows ([#35](https://github.com/mathu-fn/fincode-subscription-starter/issues/35)) ([002981e](https://github.com/mathu-fn/fincode-subscription-starter/commit/002981e055216d3fb4e38d74567006b69530adbe))


### Security

* guard production backend settings ([2f1cd13](https://github.com/mathu-fn/fincode-subscription-starter/commit/2f1cd134fafda80db7ad0298cdd7fc8cefbed481))
* harden authentication against enumeration and forged tokens ([#36](https://github.com/mathu-fn/fincode-subscription-starter/issues/36)) ([6168c84](https://github.com/mathu-fn/fincode-subscription-starter/commit/6168c8425cdf28f46e56dad5d01655a65328620f))
* カード ID 列挙防止と決済フロー周辺の脆弱性・堅牢性修正 ([#56](https://github.com/mathu-fn/fincode-subscription-starter/issues/56)) ([6e998b5](https://github.com/mathu-fn/fincode-subscription-starter/commit/6e998b5f69ea4cc705a8c9b3376fc97e3d1bd154))


### Code Refactoring

* add domain enums/TypedDict and tidy auth and client code ([#19](https://github.com/mathu-fn/fincode-subscription-starter/issues/19)) ([603c859](https://github.com/mathu-fn/fincode-subscription-starter/commit/603c85972a209d020e2e6aabc92853465662a8b8))
* centralize backend app wiring ([69d23a6](https://github.com/mathu-fn/fincode-subscription-starter/commit/69d23a6953d4f89d19d5d1bfa03710f8b1802ac0))
* consolidate business exceptions and tidy frontend structure ([#23](https://github.com/mathu-fn/fincode-subscription-starter/issues/23)) ([bcf2e03](https://github.com/mathu-fn/fincode-subscription-starter/commit/bcf2e0381d9ca0d2f388aa8b3dadb8667333076d))
* remove redundant frontend guards ([#51](https://github.com/mathu-fn/fincode-subscription-starter/issues/51)) ([dd2a676](https://github.com/mathu-fn/fincode-subscription-starter/commit/dd2a67647bcf92786273c73ac40a679e527c8718))
* remove unreachable guards and redundant comments ([#50](https://github.com/mathu-fn/fincode-subscription-starter/issues/50)) ([23eec47](https://github.com/mathu-fn/fincode-subscription-starter/commit/23eec471c48c2f1ae22cee5f8c61a5d79edd6ce3))
* tighten backend typing and time handling ([c6ea525](https://github.com/mathu-fn/fincode-subscription-starter/commit/c6ea5252996e052586e63321df044ff59e936981))


### Documentation

* add OSS community files and GitHub issue templates ([00d845d](https://github.com/mathu-fn/fincode-subscription-starter/commit/00d845df9ca003bd5663870e35a648c7750ced4d))
* adopt GitHub Flow as branching policy ([0d4b5b8](https://github.com/mathu-fn/fincode-subscription-starter/commit/0d4b5b8e408533b179e5b80b356f97295b7c3688))
* align landing page copy and drop unused assets and deps ([#37](https://github.com/mathu-fn/fincode-subscription-starter/issues/37)) ([dd13c8b](https://github.com/mathu-fn/fincode-subscription-starter/commit/dd13c8bc308fb0c56723dcf978857f68f6b0d5d8))
* refine Japanese phrasing across all documentation ([767b196](https://github.com/mathu-fn/fincode-subscription-starter/commit/767b1966c8b2ccfbfb6d8dd75704c96259c60c6f))
* refresh architecture/testing/deployment notes and add configuration reference ([7f68f4e](https://github.com/mathu-fn/fincode-subscription-starter/commit/7f68f4e67d7dad7752ced6793d54be14b8a6e660))
* 重複ドキュメントを統合し古い脆弱性診断メモを削除する ([#58](https://github.com/mathu-fn/fincode-subscription-starter/issues/58)) ([3801141](https://github.com/mathu-fn/fincode-subscription-starter/commit/3801141932376fd5caf62195c3c6e152130af579))

## [Unreleased]

リリース PR は `main` へのマージごとに release-please が自動生成・更新します。マージしたコミットの Conventional Commits プレフィックスから内容が分類されます（[コミットガイドライン](./docs/architecture/commit-guidelines.md) 参照）。
