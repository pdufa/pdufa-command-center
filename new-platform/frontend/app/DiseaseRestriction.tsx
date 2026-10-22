"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";
import {
  addDiseaseNode, buildDiseaseIndex, diseaseCatalogInfo, diseasePath, DISEASE_LEVELS,
  DISEASE_STORAGE_KEY, emptyDiseaseEdits, LEGACY_DISEASE_STORAGE_KEY, renameDisease,
  restoreDiseaseEdits, safeDiseaseSource, searchDiseases, type DiseaseEdits, type DiseaseNode,
} from "../lib/disease-catalog";

type Editor = { mode: "add"; parentId: string | null } | { mode: "rename"; node: DiseaseNode };
const number = (value: number) => value.toLocaleString("en-US");

export default function DiseaseRestriction() {
  const [edits, setEdits] = useState<DiseaseEdits>(emptyDiseaseEdits);
  const [ready, setReady] = useState(false);
  const [storageError, setStorageError] = useState("");
  const [selected, setSelected] = useState("mesh:C04.588.894.797.520");
  const [visibleDepth, setVisibleDepth] = useState(5);
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);
  const [resultLimit, setResultLimit] = useState(30);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [name, setName] = useState("");
  const [source, setSource] = useState("");
  const [formError, setFormError] = useState("");

  useEffect(() => {
    try {
      const current = localStorage.getItem(DISEASE_STORAGE_KEY);
      const legacy = localStorage.getItem(LEGACY_DISEASE_STORAGE_KEY);
      if (current) {
        try { setEdits(restoreDiseaseEdits(JSON.parse(current))); }
        catch {
          if (legacy) setEdits(restoreDiseaseEdits(JSON.parse(legacy)));
          setStorageError("The saved disease edits could not be read. The source catalog is still available.");
          return;
        }
      } else if (legacy) setEdits(restoreDiseaseEdits(JSON.parse(legacy)));
      setReady(true);
    } catch { setStorageError("Saved disease edits are unavailable on this device. The source catalog is still available."); }
  }, []);
  useEffect(() => {
    if (!ready) return;
    try { localStorage.setItem(DISEASE_STORAGE_KEY, JSON.stringify(edits)); }
    catch { setStorageError("This device could not save your latest disease edits. Keep this page open to retain them."); }
  }, [edits, ready]);

  const index = useMemo(() => buildDiseaseIndex(edits), [edits]);
  const selectedPath = useMemo(() => diseasePath(selected, index), [selected, index]);
  const results = useMemo(() => searchDiseases(deferredQuery, index), [deferredQuery, index]);
  const roots = index.children.get(null) || [];
  const current = index.byId.get(selected);
  const customDepth = edits.custom.reduce((max, node) => Math.max(max, diseasePath(node.id, index).length), 0);
  const maxDepth = Math.max(diseaseCatalogInfo.levelCounts.length, customDepth);

  function selectNode(node: DiseaseNode) {
    setSelected(node.id);
    setVisibleDepth(depth => Math.max(depth, diseasePath(node.id, index).length));
    setEditor(null);
  }
  function startEditor(next: Editor) {
    setEditor(next);
    setName(next.mode === "rename" ? next.node.name : "");
    setSource("");
    setFormError("");
  }
  function saveEditor(event: React.FormEvent) {
    event.preventDefault();
    if (!editor || !name.trim()) return;
    if (editor.mode === "rename") {
      setEdits(old => renameDisease(old, editor.node, name));
    } else {
      if (source.trim() && !safeDiseaseSource(source)) { setFormError("Use a complete https:// source link."); return; }
      if ((index.children.get(editor.parentId) || []).some(node => node.name.toLocaleLowerCase() === name.trim().toLocaleLowerCase())) {
        setFormError("That name already exists under this parent."); return;
      }
      const node: DiseaseNode = { id: "custom:" + crypto.randomUUID(), name: name.trim(), parentId: editor.parentId, sourceUrl: safeDiseaseSource(source) };
      setEdits(old => addDiseaseNode(old, node, index));
      setSelected(node.id);
      setVisibleDepth(depth => Math.max(depth, editor.parentId ? diseasePath(editor.parentId, index).length + 1 : 5));
    }
    setEditor(null);
  }

  return <details className="panel disease-restriction" id="disease" open>
    <summary><strong>DISEASE — restriction subtype</strong> · {number(index.unique.length)} unique classifications</summary>
    <div className="disease-body">
      <p className="subtle">Populated from NLM MeSH 2026: {number(roots.length)} areas, five browsing levels and all published deeper levels.</p>
      <p className="subtle">Levels follow the source tree. A branch may end before Level 5 or continue beyond it. A classification in several branches is counted once.</p>
      <div className="disease-toolbar">
        <a href={diseaseCatalogInfo.sourceUrl} target="_blank" rel="noopener noreferrer">SOURCE CATALOG ↗</a>
        <a href="https://mondo.monarchinitiative.org/" target="_blank" rel="noopener noreferrer">MORE DISEASE / SUBTYPE REFERENCES ↗</a>
        <button type="button" onClick={() => startEditor({ mode: "add", parentId: null })}>+ ADD AREA / LEVEL 1</button>
      </div>
      <label className="disease-search">Search every level
        <input type="search" placeholder="Disease, alternate name or MeSH ID" value={query}
          onChange={event => { setQuery(event.target.value); setResultLimit(30); }} />
      </label>
      {query.trim() ? <div className="disease-results" aria-busy={query !== deferredQuery}>
        <p role="status">{number(results.length)} unique matching classifications</p>
        <ul>{results.slice(0, resultLimit).map(node => <li key={node.sourceId || node.id}>
          <button type="button" className="secondary" onClick={() => selectNode(node)}>{node.name}</button>
          <small>{diseasePath(node.id, index).map(item => item.name).join(" › ")}</small>
        </li>)}</ul>
        {results.length > resultLimit && <button type="button" onClick={() => setResultLimit(limit => limit + 30)}>SHOW 30 MORE</button>}
      </div> : null}
      <nav aria-label="Selected disease path" className="disease-breadcrumb">
        {selectedPath.map((node, depth) => <button type="button" key={node.id} className="secondary"
          onClick={() => selectNode(node)}>{depth + 1}. {node.name}</button>)}
      </nav>
      <div className="disease-levels">
        {Array.from({ length: visibleDepth }, (_, depth) => {
          const parent = depth === 0 ? null : selectedPath[depth - 1];
          const options = depth === 0 ? roots : parent ? index.children.get(parent.id) || [] : [];
          const node = selectedPath[depth];
          return <section className="disease-level" key={depth}>
            <h4>LEVEL {depth + 1} · {DISEASE_LEVELS[depth] || "Deeper classification"}</h4>
            <p className="subtle">{number(options.length)} {depth === 0 ? "areas" : "entries under selected parent"}</p>
            <label>Choose Level {depth + 1}
              <select value={node?.id || ""} disabled={!options.length} onChange={event => { const next = index.byId.get(event.target.value); if (next) selectNode(next); }}>
                <option value="">{options.length ? "Select classification" : parent ? "No finer source classification" : "Select a parent above"}</option>
                {options.map(option => <option key={option.id} value={option.id}>{option.name}</option>)}
              </select>
            </label>
            {node ? <div className="disease-node">
              <strong>{node.name}</strong>
              {node.sourceId && <small>{node.sourceId} · {node.treeNumber}</small>}
              {node.sourceName && node.name !== node.sourceName && <small>Source name: {node.sourceName}</small>}
              {node.needsReview && <small>Review parent placement for this saved entry.</small>}
              {node.sourceUrl && <a href={node.sourceUrl} target="_blank" rel="noopener noreferrer">SOURCE ↗</a>}
              <div className="disease-actions">
                <button type="button" onClick={() => startEditor({ mode: "rename", node })}>RENAME</button>
                <button type="button" onClick={() => startEditor({ mode: "add", parentId: node.id })}>+ ADD SUBLEVEL</button>
              </div>
            </div> : null}
          </section>;
        })}
      </div>
      <div className="disease-toolbar">
        <button type="button" disabled={visibleDepth >= maxDepth + 1} onClick={() => setVisibleDepth(depth => depth + 1)}>+ SHOW NEXT LEVEL</button>
        {visibleDepth > 5 && <button type="button" className="secondary" onClick={() => { setVisibleDepth(5); if (selectedPath[4]) setSelected(selectedPath[4].id); }}>SHOW FIRST 5 LEVELS</button>}
        {current && <button type="button" onClick={() => startEditor({ mode: "add", parentId: current.id })}>+ ADD LEVEL BELOW {current.name}</button>}
      </div>
      {editor && <form className="disease-editor" onSubmit={saveEditor}>
        <h4>{editor.mode === "rename" ? "Rename " + editor.node.name : "Add classification"}</h4>
        {editor.mode === "add" && <p>Parent: {editor.parentId ? index.byId.get(editor.parentId)?.name : "Top level"}</p>}
        <label>Name<input required autoFocus maxLength={200} value={name} onChange={event => setName(event.target.value)} /></label>
        {editor.mode === "add" && <label>Source link (optional)<input type="url" placeholder="https://" value={source} onChange={event => setSource(event.target.value)} /></label>}
        {formError && <p role="alert">{formError}</p>}
        <div className="disease-toolbar"><button type="submit">SAVE</button><button type="button" className="secondary" onClick={() => setEditor(null)}>CANCEL</button></div>
      </form>}
      {storageError && <p role="alert">{storageError}</p>}
      <details className="disease-coverage"><summary>Catalog coverage and saved edits</summary>
        <p>{diseaseCatalogInfo.coverage}</p>
        <p>{number(diseaseCatalogInfo.uniqueCount)} source classifications · {number(diseaseCatalogInfo.placementCount)} tree placements · {diseaseCatalogInfo.levelCounts.length} source levels.</p>
        <p>{number(edits.custom.length)} added entries and {number(Object.keys(edits.renames).length)} renamed classifications saved on this device.</p>
        <p>Reference names and identifiers remain available after renaming.</p>
      </details>
    </div>
  </details>;
}
