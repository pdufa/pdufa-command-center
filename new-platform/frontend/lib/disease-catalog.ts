import data from "../data/diseaseCatalog.json";

export const DISEASE_STORAGE_KEY = "pdufa-disease-hierarchy-v2";
export const LEGACY_DISEASE_STORAGE_KEY = "pdufa-disease-hierarchy-v1";
export const DISEASE_LEVELS = ["Therapeutic area", "Disease group", "Disease family", "Specific disease", "Disease subtype"];
export const diseaseCatalogInfo = {
  source: data.source, sourceUrl: data.sourceUrl, coverage: data.coverage,
  version: data.version, uniqueCount: data.uniqueCount,
  placementCount: data.placementCount, levelCounts: data.levelCounts,
};

export type DiseaseNode = {
  id: string;
  name: string;
  parentId: string | null;
  sourceId?: string;
  sourceName?: string;
  sourceUrl?: string;
  treeNumber?: string;
  aliases?: string[];
  needsReview?: boolean;
};
export type DiseaseEdits = { version: 2; custom: DiseaseNode[]; renames: Record<string, string> };
export const emptyDiseaseEdits = (): DiseaseEdits => ({ version: 2, custom: [], renames: {} });

const records = data.terms as [string, string, string[], string[]][];
const builtinNodes: DiseaseNode[] = records.flatMap(([sourceId, name, paths, aliases]) => paths.map(treeNumber => ({
  id: "mesh:" + treeNumber, name, sourceName: name, sourceId, aliases, treeNumber,
  sourceUrl: "https://meshb.nlm.nih.gov/record/ui?ui=" + sourceId,
  parentId: treeNumber.includes(".") ? "mesh:" + treeNumber.slice(0, treeNumber.lastIndexOf(".")) : null,
})));
const builtinById = new Map(builtinNodes.map(node => [node.id, node]));
const builtinSourceIds = new Set(records.map(([id]) => id));

export function safeDiseaseSource(value: unknown): string | undefined {
  if (typeof value !== "string" || !value.trim()) return undefined;
  try {
    const url = new URL(value.trim());
    return url.protocol === "https:" && !url.username && !url.password ? url.href : undefined;
  } catch { return undefined; }
}

/** Preserve old manual entries while always retaining the bundled population. */
export function restoreDiseaseEdits(value: unknown): DiseaseEdits {
  const result = emptyDiseaseEdits();
  const state = value && typeof value === "object" ? value as Record<string, unknown> : null;
  const custom = Array.isArray(value) ? value : state?.version === 2 && Array.isArray(state.custom) ? state.custom : [];
  const ids = new Set<string>();
  for (const item of custom) {
    if (!item || typeof item !== "object") continue;
    const node = item as Record<string, unknown>;
    if (typeof node.id !== "string" || !node.id.trim() || builtinById.has(node.id) || ids.has(node.id) ||
        typeof node.name !== "string" || !node.name.trim()) continue;
    const parentId = typeof node.parentId === "string" ? node.parentId : null;
    ids.add(node.id);
    result.custom.push({ id: node.id, name: node.name.trim(), parentId,
      sourceUrl: safeDiseaseSource(node.sourceUrl), needsReview: node.needsReview === true || undefined });
  }
  const byId = new Map([...builtinById, ...result.custom.map(node => [node.id, node] as const)]);
  for (const node of result.custom) {
    const visited = new Set([node.id]);
    let parent = node.parentId;
    while (parent) {
      if (visited.has(parent) || !byId.has(parent)) {
        node.parentId = null;
        node.needsReview = true;
        break;
      }
      visited.add(parent);
      parent = byId.get(parent)!.parentId;
    }
  }
  if (state?.version === 2 && state.renames && typeof state.renames === "object") {
    for (const [id, name] of Object.entries(state.renames)) {
      if (builtinSourceIds.has(id) && typeof name === "string" && name.trim()) result.renames[id] = name.trim();
    }
  }
  return result;
}

export function buildDiseaseIndex(edits: DiseaseEdits) {
  const nodes = [...builtinNodes.map(node => node.sourceId && edits.renames[node.sourceId]
    ? { ...node, name: edits.renames[node.sourceId] } : node), ...edits.custom];
  const byId = new Map(nodes.map(node => [node.id, node]));
  const children = new Map<string | null, DiseaseNode[]>();
  for (const node of nodes) {
    const list = children.get(node.parentId) || [];
    list.push(node);
    children.set(node.parentId, list);
  }
  for (const list of children.values()) list.sort((a, b) => a.name.localeCompare(b.name));
  const unique = new Map<string, DiseaseNode>();
  for (const node of nodes) {
    const id = node.sourceId || node.id;
    const previous = unique.get(id);
    // Search results select a short, complete source path; every other path stays browsable.
    if (!previous || (node.treeNumber?.length || 0) < (previous.treeNumber?.length || 0)) unique.set(id, node);
  }
  return { nodes, byId, children, unique: [...unique.values()].sort((a, b) => a.name.localeCompare(b.name)) };
}
export type DiseaseIndex = ReturnType<typeof buildDiseaseIndex>;

export function diseasePath(id: string, index: DiseaseIndex): DiseaseNode[] {
  const path: DiseaseNode[] = [];
  const visited = new Set<string>();
  let node = index.byId.get(id);
  while (node && !visited.has(node.id)) {
    visited.add(node.id);
    path.unshift(node);
    node = node.parentId ? index.byId.get(node.parentId) : undefined;
  }
  return path;
}

export function searchDiseases(query: string, index: DiseaseIndex): DiseaseNode[] {
  const words = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) return [];
  return index.unique.filter(node => {
    const text = [node.name, node.sourceName, node.sourceId, ...(node.aliases || [])].join(" ").toLocaleLowerCase();
    return words.every(word => text.includes(word));
  });
}

export function renameDisease(edits: DiseaseEdits, node: DiseaseNode, name: string): DiseaseEdits {
  if (!name.trim()) return edits;
  return node.sourceId
    ? { ...edits, renames: { ...edits.renames, [node.sourceId]: name.trim() } }
    : { ...edits, custom: edits.custom.map(item => item.id === node.id ? { ...item, name: name.trim() } : item) };
}

export function addDiseaseNode(edits: DiseaseEdits, node: DiseaseNode, index: DiseaseIndex): DiseaseEdits {
  if (!node.name.trim() || index.byId.has(node.id) || node.parentId && !index.byId.has(node.parentId)) return edits;
  if ((index.children.get(node.parentId) || []).some(item => item.name.toLocaleLowerCase() === node.name.trim().toLocaleLowerCase())) return edits;
  return { ...edits, custom: [...edits.custom, { ...node, name: node.name.trim(), sourceUrl: safeDiseaseSource(node.sourceUrl) }] };
}
