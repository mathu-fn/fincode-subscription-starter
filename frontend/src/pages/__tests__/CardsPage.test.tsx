import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HomePage } from "../HomePage";

const mocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  initFincodeUi: vi.fn(),
  mountFincodeUi: vi.fn(),
  unmountFincodeUi: vi.fn()
}));

vi.mock("../../lib/apiClient", async () => {
  const actual = await vi.importActual<typeof import("../../lib/apiClient")>("../../lib/apiClient");
  return {
    ...actual,
    apiFetch: mocks.apiFetch
  };
});

vi.mock("../../lib/fincodeJs", () => ({
  initFincodeUi: mocks.initFincodeUi,
  mountFincodeUi: mocks.mountFincodeUi,
  unmountFincodeUi: mocks.unmountFincodeUi,
  tokenizeViaUi: vi.fn()
}));

vi.mock("../../hooks/useAuth", () => ({
  useAuth: () => ({
    user: { id: 1, email: "alice@example.com", name: "Alice", created_at: "2026-01-01T00:00:00Z" }
  })
}));

beforeEach(() => {
  mocks.apiFetch.mockImplementation((path: string) => {
    if (path === "/api/subscription") return Promise.resolve(null);
    if (path === "/api/subscription/plans") return Promise.resolve([]);
    if (path === "/api/subscription/cards") return Promise.resolve([]);
    if (path.startsWith("/api/subscription/history")) {
      return Promise.resolve({ data: [], page: 1, per_page: 10, total: 0 });
    }
    return Promise.resolve(null);
  });
  mocks.initFincodeUi.mockResolvedValue({ fincode: {}, ui: {} });
  mocks.mountFincodeUi.mockReset();
  mocks.unmountFincodeUi.mockReset();
});

describe("HomePage cards section", () => {
  it("renders the fincode-required wrapper and mounts the card input UI", async () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    );

    expect(screen.getByText("新規カードを追加")).toBeInTheDocument();
    expect(screen.queryByText(/テストトークンを直接入力/)).not.toBeInTheDocument();
    expect(document.getElementById("fincode-ui-mount-form")).toBeInTheDocument();
    expect(document.getElementById("fincode-ui-mount")).toBeInTheDocument();

    await waitFor(() => {
      expect(mocks.mountFincodeUi).toHaveBeenCalledWith({}, "fincode-ui-mount");
    });
  });
});
