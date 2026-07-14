import { Link } from "react-router-dom";

import { primaryLinkClass } from "../lib/styles";

export function NotFoundPage() {
  return (
    <section className="mx-auto grid max-w-md gap-8 py-10">
      <div className="grid gap-3">
        <p className="font-dot text-7xl leading-none tracking-tight text-black sm:text-8xl">404</p>
        <h1 className="text-lg font-medium text-black">ページが見つかりません</h1>
      </div>
      <p>
        <Link to="/" className={primaryLinkClass}>
          ホームに戻る
        </Link>
      </p>
    </section>
  );
}
