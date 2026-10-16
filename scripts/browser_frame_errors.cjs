// Ignore only transient frame-loading errors; real Streamlit failures remain fatal.
function isTransientFrameReadError(error) {
  const message = String(error?.message || error);
  return /detached|Execution context was destroyed|Target closed|frame was detached|Timeout 2500ms exceeded|waiting for locator\('body'\)/i.test(message);
}
module.exports = { isTransientFrameReadError };
