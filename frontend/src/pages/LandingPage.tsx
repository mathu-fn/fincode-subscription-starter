import { Link } from "react-router-dom";

import { Card } from "../components/Card";
import { Label } from "../components/Label";
import { StatusDot } from "../components/StatusDot";
import { badgeClass, sectionTitle } from "../lib/styles";

const GITHUB_URL = "https://github.com/ltac0203-pixel/fincode-subscription-starter";

// 暗面（bg-black）上のボタン。共有の primaryBtn / secondaryBtn は黒地のため黒背景に
// 埋もれる。ここだけ白黒を反転させた版をローカルに定義する（配色の反転のみ）。
const heroPrimaryBtn =
  "inline-flex min-h-11 items-center justify-center border border-white bg-white px-6 py-3 font-mono text-xs uppercase tracking-[0.1em] text-black transition-colors duration-150 hover:bg-black hover:text-white focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-black";
const heroSecondaryBtn =
  "inline-flex min-h-11 items-center justify-center border border-white bg-black px-6 py-3 font-mono text-xs uppercase tracking-[0.1em] text-white transition-colors duration-150 hover:bg-white hover:text-black focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-black";

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
      <section className="grid gap-8 bg-black p-8 text-white sm:p-12 lg:p-16">
        <div className="flex flex-wrap items-center gap-2">
          <span className={badgeClass}>OSS リファレンス実装</span>
          <span className={badgeClass}>Apache 2.0</span>
          <span className={badgeClass}>fincode 定期課金</span>
        </div>
        <h1 className="font-dot text-4xl leading-tight tracking-tight text-white sm:text-6xl">
          fincode の定期課金を実装する
          <br className="hidden sm:block" />
          OSS リファレンス実装
        </h1>
        <p className="max-w-2xl text-base text-neutral-400 sm:text-lg">
          React + FastAPI で fincode の定期課金をひととおり実装したオープンソースのサンプルです。
        </p>
        <div className="flex flex-wrap gap-3">
          <Link to="/login" className={heroPrimaryBtn}>
            デモを試す（Google でログイン）
          </Link>
          <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className={heroSecondaryBtn}>
            GitHub で見る →
          </a>
        </div>
      </section>

      <section className="grid gap-6">
        <div className="grid gap-3">
          <StatusDot variant="live" label="features" />
          <h2 className={sectionTitle}>できること</h2>
        </div>
        <ul className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {features.map((feature, index) => (
            <li key={feature.title}>
              <Card className="grid h-full gap-3 p-6">
                <Label>{`feature (${index + 1})`}</Label>
                <h3 className="text-base font-medium text-black">{feature.title}</h3>
                <p className="text-sm leading-relaxed text-muted">{feature.description}</p>
              </Card>
            </li>
          ))}
        </ul>
      </section>

      <footer className="border-t border-line pt-6 text-xs leading-relaxed text-muted">
        <p>
          Apache License 2.0 / コントリビュートは同ライセンス下で配布されることに同意したものとみなされます。fincode は GMO Payment Gateway 株式会社の決済サービスです。
        </p>
      </footer>
    </div>
  );
}
