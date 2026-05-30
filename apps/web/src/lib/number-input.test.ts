import assert from "node:assert/strict";
import test from "node:test";

import { parseRequiredNumberInput, requiredNumberInputValue } from "./number-input.ts";

test("required number inputs can stay empty while the user is editing", () => {
  const parsed = parseRequiredNumberInput("");

  assert.equal(Number.isNaN(parsed), true);
  assert.equal(requiredNumberInputValue(parsed), "");
});

test("required number inputs keep entered numeric values", () => {
  assert.equal(parseRequiredNumberInput("32000"), 32000);
  assert.equal(requiredNumberInputValue(32000), 32000);
});
