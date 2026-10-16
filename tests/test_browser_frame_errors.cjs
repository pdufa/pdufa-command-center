const assert = require("node:assert/strict");
const { isTransientFrameReadError } = require("../scripts/browser_frame_errors.cjs");
for (const message of [
  "locator.innerText: Timeout 2500ms exceeded.\nCall log:\n  - waiting for locator('body')",
  "Frame was detached",
  "Execution context was destroyed",
  "Target closed",
]) assert.equal(isTransientFrameReadError(new Error(message)), true, message);
for (const message of [
  "Streamlit application exception",
  "Source integration failed",
  "KeyError: missing data column",
  "Browser could not connect",
]) assert.equal(isTransientFrameReadError(new Error(message)), false, message);
console.log("Bounded frame-warmup error classification passed");
