import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <section className="page page-narrow">
      <h1>ページが見つかりません</h1>
      <p>
        <Link to="/" className="primary-link">
          ホームに戻る
        </Link>
      </p>
    </section>
  );
}
