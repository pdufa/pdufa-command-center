/* Progressive NCT renderer for the PREDICTION tab.
 * Call mountPredictionStream({input, output, endpoint, headers}) after mounting UI.
 * Authentication stays server-side or is provided by the hosting app.
 * Saved-evidence replay events never imply active research.
 */
export function mountPredictionStream({ input, output, endpoint, headers = {} }) {
  if (!input || !output || typeof endpoint !== "function") {
    throw new Error("Input, output and endpoint function are required");
  }
  let generation = 0;
  let controller = null;
  const render = (event) => {
    if (event.type === "started") {
      output.replaceChildren();
      output.dataset.nct = event.nct_id;
      return;
    }
    if (event.type === "leaf") {
      const row = document.createElement("div");
      row.dataset.nodeId = event.node_id;
      row.dataset.state = event.status;
      const icon = document.createElement("span");
      icon.textContent = event.research_running ? "◌" : (event.status === "AVAILABLE" ? "✓" : "!");
      icon.className = event.research_running ? "research-spinner" : "";
      icon.setAttribute("aria-label", event.research_running ? "Researching" : event.status);
      const label = document.createElement("strong");
      label.textContent = event.label + ": ";
      const value = document.createElement("span");
      value.textContent = event.value == null ? "Unavailable" : JSON.stringify(event.value);
      row.append(icon, label, value);
      output.append(row);
      return;
    }
    if (event.type === "complete") {
      output.dataset.decision = event.decision;
    }
  };
  async function load(nct) {
    generation += 1;
    const current = generation;
    controller?.abort();
    controller = new AbortController();
    output.replaceChildren();
    output.dataset.nct = nct;
    if (!/^NCT[0-9]{8}$/.test(nct)) {
      output.textContent = "Enter an exact NCT identifier.";
      return;
    }
    try {
      const response = await fetch(endpoint(nct), { headers, signal: controller.signal });
      if (!response.ok || !response.body) throw new Error("Trial evidence stream unavailable");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let cut;
        while ((cut = buffer.indexOf("\n\n")) !== -1) {
          const frame = buffer.slice(0, cut);
          buffer = buffer.slice(cut + 2);
          const data = frame.split("\n").find(line => line.startsWith("data: "));
          if (data && current === generation) {
            const event = JSON.parse(data.slice(6));
            if (event.nct_id === nct) render(event);
          }
        }
      }
    } catch (error) {
      if (current === generation && error.name !== "AbortError") {
        output.textContent = "Unable to load saved trial evidence.";
      }
    }
  }
  const onChange = () => load(input.value.trim().toUpperCase());
  input.addEventListener("change", onChange);
  return {
    load,
    destroy() {
      generation += 1;
      controller?.abort();
      input.removeEventListener("change", onChange);
    },
  };
}
