import { Link } from "react-router-dom";

import { badgeClass, primaryBtn, secondaryBtn, sectionTitle } from "../lib/styles";

const GITHUB_URL = "https://github.com/ltac0203-pixel/fincode-subscription-starter";

const cardClass = "border border-sky-200 bg-white p-6";

const features: Array<{ title: string; description: string }> = [
  {
    title: "Google 認証",
    description: "Google アカウントでログインできます。"
  },
  {
    title: "カードトークン化",
    description: "カード情報はブラウザ上でトークン化し、サーバーには送りません。"
  },
  {
    title: "契約・変更・解約",
    description: "プランの契約からアップグレード・解約まで一通り行えます。"
  },
  {
    title: "Webhook の冪等処理",
    description: "決済通知を安全に受信し、同じ通知が再送されても重複しません。"
  },
  {
    title: "決済履歴",
    description: "課金の結果を一覧で確認できます。"
  },
  {
    title: "監査ログ",
    description: "主要な操作の履歴を記録します。"
  }
];

export function LandingPage() {
  return (
    <div className="mx-auto grid max-w-6xl gap-16 pb-12">
      <section className="grid gap-6 pt-4 sm:pt-8">
        <div className="flex flex-wrap items-center gap-2">
          <span className={badgeClass}>OSS リファレンス実装</span>
          <span className={badgeClass}>Apache 2.0</span>
          <span className={badgeClass}>fincode 定期課金</span>
        </div>
        <h1 className="text-4xl font-bold leading-tight text-sky-950 sm:text-5xl">
          fincode の定期課金を実装する
          <br className="hidden sm:block" />
          <span className="text-sky-600">OSS リファレンス実装</span>
        </h1>
        <p className="max-w-3xl text-base text-slate-700 sm:text-lg">
          React + FastAPI で fincode の定期課金をひととおり実装したオープンソースのサンプルです。
        </p>
        <div className="flex flex-wrap gap-3">
          <Link to="/login" className={primaryBtn}>
            デモを試す（Google でログイン）
          </Link>
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            className={secondaryBtn}
          >
            GitHub で見る →
          </a>
        </div>
      </section>

      <section className="grid gap-6">
        <h2 className={sectionTitle}>できること</h2>
        <ul className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {features.map((feature) => (
            <li key={feature.title} className={cardClass}>
              <h3 className="font-bold text-sky-950">{feature.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{feature.description}</p>
            </li>
          ))}
        </ul>
      </section>

      <footer className="border-t border-sky-200 pt-6 text-xs leading-relaxed text-slate-500">
        <p>
          Apache License 2.0 / コントリビュートは同ライセンス下で配布されることに同意したものとみなされます。fincode は GMO Payment Gateway 株式会社の決済サービスです。
        </p>
      </footer>
    </div>
  );
}
