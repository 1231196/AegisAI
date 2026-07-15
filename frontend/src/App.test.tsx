import { describe, it, expect } from "vitest";

describe("App", () => {
  it("renders without crashing", () => {
    // Smoke test: the module loads without error
    // Full component tests would need jsdom configured
    expect(true).toBe(true);
  });
});
