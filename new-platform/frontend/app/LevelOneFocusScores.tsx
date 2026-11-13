"use client";

import { useMemo, useState } from "react";
import snapshot from "../data/focusLevelOneDocumentCoverage20261113.json";

type Trial = (typeof snapshot.records)[number];
type Sort = "score" | "ticker" | "nct";
const headers = [
  ["Identity & phase", "identityPhase", 15],
  ["Design & endpoints", "designEndpoints", 20],
  ["Linked protocol and SAP", "protocolSap", 25],
  ["Posted registry results", "registryResults", 25],
  ["Source traceability", "sourceTraceability", 15],
] as const;

const section = {
  border: "1px solid #aacbc2", borderRadius: 14, padding: "clamp(14px,2vw,22px)",
  background: "#f9fcfb", margin: "0 0 22px", color: "#173b37",
} as const;

function detailsFor(row: Trial) {
  return row.score === 100
    ? "All five defined registry-document checklist categories were present at this source snapshot. This does not establish statistically significant benefit, acceptable safety, manufacturing readiness, or FDA approval."
    : "Registry identity, trial design/endpoints and original-source traceability were captured. A linked protocol/SAP and posted results were not present in this registry snapshot. Those may exist in other sources or may not yet be expected at this trial stage; absence is not an adverse finding.";
}

export default function LevelOneFocusScores() {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<Sort>("score");
  const visible = useMemo(() => {
    const term = query.trim().toLowerCase();
    return snapshot.records
      .filter(row => !term || row.ticker.toLowerCase().includes(term) || row.nct.toLowerCase().includes(term))
      .slice()
      .sort((a, b) => sort === "score" ? b.score - a.score || a.ticker.localeCompare(b.ticker) || a.nct.localeCompare(b.nct)
        : sort === "ticker" ? a.ticker.localeCompare(b.ticker) || a.nct.localeCompare(b.nct)
        : a.nct.localeCompare(b.nct));
  }, [query, sort]);

  const full = snapshot.records.filter(row => row.score === 100).length;
  return <section id="focus-level1-scores" aria-label="Level 1 registry document coverage assessments" data-testid="focus-level1-scores" style={section}>
    <div style={{fontWeight:850, fontSize:11, letterSpacing:".075em", color:"#176658"}}>
      FOCUS · LEVEL 1 · DOCUMENTATION SCORE ONLY
    </div>
    <h2 style={{fontSize:23, margin:"6px 0"}}>All 32 FOCUS trials — Level 1 Documentation Scores</h2>
    <p style={{fontSize:14,lineHeight:1.6,maxWidth:1050,margin:"8px 0"}}>
      Dated ClinicalTrials.gov documentation-coverage assessment,  <strong>{snapshot.asOfUtc} UTC</strong>.
      All <strong>{snapshot.records.length} / 32</strong> exact trial IDs were scored against this five-part
      documentation checklist: <strong>{full}</strong> have 100/100 documentation points and{" "}
      <strong>{snapshot.records.length - full}</strong> have 50/100 documentation points.
    </p>
    <p style={{fontSize:13,lineHeight:1.65,padding:12,background:"#fff4df",border:"1px solid #d9b981",borderRadius:8,margin:"9px 0"}}>
      <strong>DOCUMENTATION SCORE ONLY — NOT A PDUFA APPROVAL PREDICTION.</strong>{" "}
      A 100/100 means all checklist categories were documented in the registry snapshot; a 50/100
      means fewer categories were documented there, <strong>not</strong> that approval is 50% likely.
      Information absent from ClinicalTrials.gov may be available from FDA filings, sponsors,
      scientific publications, or a later registry release. Independent scientific review is pending.
    </p>
    <p style={{fontSize:12,lineHeight:1.55,color:"#57726c",margin:"8px 0 15px"}}>
      Dated 32-record FOCUS research cohort, not a current eligibility or application-cycle verification.
      Registry phase/status and documents must be checked again before a clinical assessment.
      <a href={snapshot.sourceRun} target="_blank" rel="noopener noreferrer" style={{color:"#087a6a",marginLeft:8}}>
        Source-run record
      </a>
      {" · "}
      <a href={snapshot.sourceArtifact} target="_blank" rel="noopener noreferrer" style={{color:"#087a6a"}}>
        Original-source archive
      </a>
    </p>
    <div style={{display:"flex",alignItems:"end",gap:12,flexWrap:"wrap",marginBottom:13}}>
      <label htmlFor="level1-filter" style={{display:"grid",gap:5,fontSize:12,fontWeight:750}}>
        Find company ticker or NCT
        <input id="level1-filter" type="search" value={query} onChange={e=>setQuery(e.target.value)}
          placeholder="e.g., ABVX or NCT05507203" style={{minWidth:235,padding:"9px 11px",fontSize:14,border:"1px solid #b5c8c2",borderRadius:7}}/>
      </label>
      <label htmlFor="level1-sort" style={{display:"grid",gap:5,fontSize:12,fontWeight:750}}>
        Sort trials
        <select id="level1-sort" value={sort} onChange={e=>setSort(e.target.value as Sort)}
          style={{padding:"9px 11px",fontSize:14,border:"1px solid #b5c8c2",borderRadius:7}}>
          <option value="score">Highest document score first</option>
          <option value="ticker">Ticker A to Z</option>
          <option value="nct">NCT ID</option>
        </select>
      </label>
      <span role="status" aria-live="polite" style={{fontSize:12,color:"#56716b",paddingBottom:8}}>
        Showing {visible.length} of {snapshot.records.length} trials
      </span>
    </div>
    <div style={{overflowX:"auto",background:"#fff",border:"1px solid #c9dbd4",borderRadius:9}}>
      <table style={{borderCollapse:"collapse",width:"100%",minWidth:760,fontSize:13}}>
        <thead><tr style={{background:"#e5f1eb",textAlign:"left"}}>
          {["Ticker","Exact NCT","Documentation /100","Identity /15","Design /20","Protocol+SAP /25","Results /25","Trace /15","Explanation & sources"].map(x=>
            <th key={x} scope="col" style={{padding:"10px 8px",borderBottom:"2px solid #acc8ba",whiteSpace:"nowrap"}}>{x}</th>)}
        </tr></thead>
        <tbody>{visible.map(row=><tr key={row.nct} data-testid="level1-score-row">
          <td style={{padding:"9px 8px",borderBottom:"1px solid #dce7e3",fontWeight:800}}>{row.ticker}</td>
          <td style={{padding:"9px 8px",borderBottom:"1px solid #dce7e3"}}>
            <a href={"https://clinicaltrials.gov/study/"+row.nct} target="_blank" rel="noopener noreferrer" style={{color:"#08665a"}}>{row.nct}</a>
          </td>
          <td style={{padding:"9px 8px",borderBottom:"1px solid #dce7e3",fontWeight:850,whiteSpace:"nowrap"}}>
            {row.score} / 100 <span style={{display:"block",fontSize:10,fontWeight:650,color:"#58746c"}}>Documentation only</span>
          </td>
          {[row.identityPhase,row.designEndpoints,row.protocolSap,row.registryResults,row.sourceTraceability].map((value,i)=>
            <td key={i} style={{padding:"9px 8px",borderBottom:"1px solid #dce7e3",textAlign:"center"}}>
              {value} / {headers[i][2]}
            </td>)}
          <td style={{padding:"9px 8px",borderBottom:"1px solid #dce7e3",minWidth:220}}>
            <details>
              <summary style={{cursor:"pointer",color:"#087867",fontWeight:750}}>View assessment and evidence</summary>
              <p style={{lineHeight:1.5,fontSize:12}}>{detailsFor(row)}</p>
              <p style={{lineHeight:1.5,fontSize:12}}>
                Protocol linked: {row.protocolLinked ? "Yes" : "No (registry only)"}.
                SAP linked: {row.sapLinked ? "Yes" : "No (registry only)"}.
                Primary results posted: {row.primaryOutcomeResultsPosted ? "Yes" : "No (registry only)"}.
                Adverse events posted: {row.adverseEventResultsPosted ? "Yes" : "No (registry only)"}.
              </p>
              <p style={{lineHeight:1.5,fontSize:12}}>
                Registry update posted: <strong>{row.registryLastUpdatePosted}</strong>.
                Source retrieved: <strong>{snapshot.sourceRetrievedUtcDate} UTC</strong>.
              </p>
              <p style={{fontSize:11,overflowWrap:"anywhere"}}>
                Registry-source SHA-256: <code>{row.rawRegistrySourceSha256}</code>
              </p>
              <strong style={{fontSize:11,color:"#80511d"}}>Automated provisional · scientific review pending</strong>
            </details>
          </td>
        </tr>)}</tbody>
      </table>
      {visible.length === 0 && <p style={{padding:"12px 16px"}}>No trial matches this search.</p>}
    </div>
    <p style={{fontSize:12,color:"#55716a",lineHeight:1.6,margin:"13px 0 0"}}>
      Level 1 documentation scoring formula: identity and phase (15), study design and endpoints (20),
      registry-linked protocol/SAP (25), posted registry results (25), source traceability (15).
      The Level 1 document coverage score must not be substituted for Levels 2–6 medical or
      regulatory scores, and cannot justify an investment or trading decision.
    </p>
  </section>;
}
