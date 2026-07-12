/**
 * MemoryRouter でラップして HomePage をレンダリングする共通ヘルパー。
 * （LoginPage.test.tsx の renderLoginPage() と同じパターン。）
 */

import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { HomePage } from "../pages/HomePage";

export function renderHomePage() {
  return render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>
  );
}
