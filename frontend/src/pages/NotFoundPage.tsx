import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <section className="mx-auto grid max-w-md gap-6">
      <h1 className="text-3xl font-bold text-sky-950">ページが見つかりません</h1>
      <p>
        <Link
          to="/"
          className="inline-flex min-h-11 items-center justify-center border border-sky-600 bg-sky-500 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2"
        >
          ホームに戻る
        </Link>
      </p>
    </section>
  );
}
