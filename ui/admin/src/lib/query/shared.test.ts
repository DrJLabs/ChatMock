import { describe, expect, it } from "vitest";

import { toErrorMessage } from "./shared";

describe("toErrorMessage", () => {
  it("extracts Flask-style nested JSON error messages", () => {
    expect(toErrorMessage('{"error":{"message":"Prompt file path must stay within repo root"}}')).toBe(
      "Prompt file path must stay within repo root",
    );
  });

  it("returns raw strings when they are not JSON", () => {
    expect(toErrorMessage("plain failure")).toBe("plain failure");
  });
});
