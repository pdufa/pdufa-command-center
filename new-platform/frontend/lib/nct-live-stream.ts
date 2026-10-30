export const NCT_PATTERN = /^NCT[0-9]{8}$/;
export const RUN_PATTERN = /^[A-Za-z0-9_-]{8,100}$/;
export const NODE_STATES = ["PENDING", "LOADING", "VERIFIED", "FAILED", "INSUFFICIENT_EVIDENCE"] as const;
export type NodeStatus = typeof NODE_STATES[number];
export type SourceProof = { url: string; sha256: string; verified_at: string };
export type NctEvent = {
  run_id: string; nct_id: string; sequence: number; node_id: string; level: 4 | 3 | 2 | 1;
  status: NodeStatus; value?: unknown; source?: SourceProof | null; parent_id?: string | null;
  terminal?: boolean; kind: "node" | "complete";
};
export type NctRunState = {
  run_id: string; nct_id: string; dossier_id: string; sequence: number;
  nodes: Record<string, NctEvent>; terminal: boolean;
};
export type RunPointer = { run_id: string; nct_id: string };

function object(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}
function sourceProof(value: unknown): value is SourceProof {
  if (!object(value) || typeof value.url !== "string" || typeof value.sha256 !== "string" || typeof value.verified_at !== "string") return false;
  try {
    const url = new URL(value.url);
    return url.protocol === "https:" && !url.username && !url.password && /^[a-f0-9]{64}$/i.test(value.sha256) &&
      /T.*(?:Z|[+-][0-9]{2}:[0-9]{2})$/.test(value.verified_at) && Number.isFinite(Date.parse(value.verified_at));
  } catch { return false; }
}
export function isNctEvent(value: unknown): value is NctEvent {
  return object(value) && typeof value.run_id === "string" && RUN_PATTERN.test(value.run_id) &&
    typeof value.nct_id === "string" && NCT_PATTERN.test(value.nct_id) &&
    typeof value.sequence === "number" && Number.isSafeInteger(value.sequence) && value.sequence > 0 &&
    typeof value.node_id === "string" && value.node_id.length > 0 && value.node_id.length <= 150 &&
    [1, 2, 3, 4].includes(Number(value.level)) && typeof value.level === "number" &&
    NODE_STATES.includes(value.status as NodeStatus) && (value.kind === "node" || value.kind === "complete") &&
    (value.parent_id === undefined || value.parent_id === null || typeof value.parent_id === "string") &&
    (value.terminal === undefined || typeof value.terminal === "boolean") &&
    (value.kind !== "complete" || value.terminal === true) &&
    (value.level !== 4 || value.status !== "VERIFIED" || sourceProof(value.source));
}

export function initialRun(run_id: string, nct_id: string, dossier_id = ""): NctRunState {
  if (!RUN_PATTERN.test(run_id) || !NCT_PATTERN.test(nct_id)) throw new Error("Invalid saved run identity");
  return { run_id, nct_id, dossier_id, sequence: 0, nodes: {}, terminal: false };
}

export function reduceNctEvent(state: NctRunState, value: unknown): NctRunState {
  if (!isNctEvent(value)) throw new Error("Malformed processing event");
  if (value.run_id !== state.run_id || value.nct_id !== state.nct_id) throw new Error("Processing event identity mismatch");
  if (value.sequence <= state.sequence) return state;
  if (state.terminal) throw new Error("Received an event after completion");
  if (value.sequence !== state.sequence + 1) throw new Error("Processing event sequence gap");
  return { ...state, sequence: value.sequence, terminal: value.kind === "complete" && value.terminal === true,
    nodes: value.kind === "node" ? { ...state.nodes, [value.node_id]: value } : state.nodes };
}

export function savedPointer(value: unknown): RunPointer | null {
  if (!object(value) || typeof value.run_id !== "string" || typeof value.nct_id !== "string" ||
      !RUN_PATTERN.test(value.run_id) || !NCT_PATTERN.test(value.nct_id)) return null;
  return { run_id: value.run_id, nct_id: value.nct_id };
}

export function parseSnapshot(value: unknown, pointer: RunPointer): NctRunState {
  if (!object(value) || value.run_id !== pointer.run_id || value.nct_id !== pointer.nct_id ||
      typeof value.dossier_id !== "string" || !Array.isArray(value.events) || typeof value.terminal !== "boolean") {
    throw new Error("Saved processing snapshot identity or schema mismatch");
  }
  let state = initialRun(pointer.run_id, pointer.nct_id, value.dossier_id);
  for (const event of value.events) state = reduceNctEvent(state, event);
  if (value.terminal !== state.terminal) throw new Error("Saved processing snapshot completion mismatch");
  return state;
}

export class NctSseParser {
  private decoder = new TextDecoder();
  private buffer = "";
  constructor(private readonly identity: RunPointer) {}
  feed(chunk: Uint8Array, final = false): NctEvent[] {
    this.buffer += this.decoder.decode(chunk, { stream: !final });
    if (this.buffer.length > 4_000_000) throw new Error("Processing event exceeds the stream buffer limit");
    const events: NctEvent[] = [];
    let boundary: RegExpMatchArray | null;
    while ((boundary = this.buffer.match(/\r?\n\r?\n/)) !== null) {
      const cut = boundary.index!;
      const frame = this.buffer.slice(0, cut).replace(/\r\n/g, "\n");
      this.buffer = this.buffer.slice(cut + boundary[0].length);
      const lines = frame.split("\n");
      const data = lines.filter(line => line.startsWith("data:")).map(line => line.slice(5).replace(/^ /, "")).join("\n");
      if (!data) continue; // Heartbeat comments carry no processing state.
      const value: unknown = JSON.parse(data);
      if (!isNctEvent(value)) throw new Error("Malformed processing stream event");
      if (value.run_id !== this.identity.run_id || value.nct_id !== this.identity.nct_id) throw new Error("Processing stream identity mismatch");
      const id = lines.find(line => line.startsWith("id:"))?.slice(3).trim();
      if (id !== value.run_id + ":" + value.sequence) throw new Error("Processing stream cursor mismatch");
      const type = lines.find(line => line.startsWith("event:"))?.slice(6).trim();
      if (type && type !== value.kind && type !== value.status.toLowerCase()) throw new Error("Processing stream event type mismatch");
      events.push(value);
    }
    if (final && this.buffer.trim() && !this.buffer.trim().startsWith(":")) throw new Error("Processing stream ended mid-event");
    return events;
  }
}

export function eventCursor(state: NctRunState): string {
  return state.run_id + ":" + state.sequence;
}

export function nodeLabel(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, letter => letter.toUpperCase());
}
