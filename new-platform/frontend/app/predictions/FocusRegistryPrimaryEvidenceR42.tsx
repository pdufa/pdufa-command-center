import Link from "next/link";
import {FOCUS_R42_PRIMARY_RESULTS} from "../../lib/focus-r42-primary-research";

export default function FocusRegistryPrimaryEvidenceR42(){
  const info=FOCUS_R42_PRIMARY_RESULTS;
  const outer={border:"1px solid #b5cfc5",background:"#f8fafb",
    borderRadius:12,padding:16,margin:"14px 0 18px"} as const;
  if(!info)return <section aria-label="Registry primary outcome source status" style={outer}>
    Original outcome receipt changed or crosswalk integrity failed. Source-derived result coverage withheld.
  </section>;
  const posted=info.trialRows.filter(t=>t.primary);
  const missing=info.trialRows.filter(t=>!t.primary);
  return <section aria-label="R42 exact FOCUS registry primary result evidence" style={outer}>
    <h2 style={{margin:"1px 0 7px",fontSize:20}}>New original registry results · 29 FOCUS trials</h2>
    <p style={{fontSize:13,lineHeight:1.6,margin:"4px 0 12px"}}>
      <strong>{posted.length}/29</strong> trials have primary result tables deposited in the current
      ClinicalTrials.gov record. <strong>16 primary outcome tables</strong> are captured with
      publicly reported treatment-arm and statistical fields.
      The other <strong>{missing.length}/29</strong> do not currently show a registry results section;
      that does <strong>not</strong> mean no Phase 3 results were published elsewhere.
    </p>
    <p style={{fontSize:12,lineHeight:1.6,margin:"6px 0"}}>
      These are <strong>reported source fields, not independently graded clinical endpoints</strong>.
      Source-only p-values cannot by themselves establish FDA efficacy, multiplicity control,
      final SAP adherence or a calibrated approval prediction.
    </p>
    <p style={{fontSize:12,margin:"6px 0 13px"}}>
      <a target="_blank" rel="noopener noreferrer" href={info.sourceArchiveUrl}
         style={{fontWeight:700,color:"#0b6657"}}>Open original source bytes and full scientific review fields</a>
      <span style={{marginLeft:8}}>Research receipt as of {info.asOf}</span>
    </p>
    <details style={{padding:12,background:"#fff",border:"1px solid #c5d8d2",borderRadius:9}}>
      <summary style={{cursor:"pointer",fontWeight:800}}>
        Inspect all 12 trials with posted primary results and 16 source-reported endpoints
      </summary>
      <div style={{display:"grid",gap:9,paddingTop:12}}>
        {posted.map(t=><article key={t.nct} style={{border:"1px solid #d6e4dd",padding:11,borderRadius:8}}>
          <strong>{t.ticker} · {t.nct}</strong>
          <span style={{fontSize:12,marginLeft:8}}>
            {t.primary!.endpoints.length} primary table(s) · results posted {t.primary!.reportedPostedOn}
          </span>
          <div style={{fontSize:12,margin:"7px 0"}}>
            Applications: {t.applicationCycleIds.join(", ")}
          </div>
          <ul style={{fontSize:12,lineHeight:1.6,paddingLeft:18,margin:"5px 0"}}>
            {t.primary!.endpoints.map((e,i)=><li key={i} style={{marginBottom:7}}>
              <strong>{e.title}</strong>
              <span style={{display:"block",color:"#536d65"}}>
                {e.pValuesAsReported.length?
                  "As-reported statistical p-value fields: "+e.pValuesAsReported.join("; "):
                  "No p-value field in this deposited primary outcome table"}
              </span>
            </li>)}
          </ul>
          <div style={{display:"flex",flexWrap:"wrap",gap:13,fontSize:12}}>
            <a href={t.sourceUrl} target="_blank" rel="noopener noreferrer" style={{color:"#086b58"}}>
              Exact ClinicalTrials.gov record
            </a>
            <Link href={"/predictions/assessment?nct="+t.nct} style={{color:"#086b58"}}>
              Open scientific evidence review
            </Link>
          </div>
        </article>)}
      </div>
    </details>
    <details style={{marginTop:9,padding:12,background:"#fff",border:"1px solid #c5d8d2",borderRadius:9}}>
      <summary style={{cursor:"pointer",fontWeight:700}}>
        Show 17 other trials without a current registry results section (not a negative finding)
      </summary>
      <div style={{display:"flex",flexWrap:"wrap",gap:"7px 15px",paddingTop:10,fontSize:12}}>
        {missing.map(t=><a key={t.nct} href={t.sourceUrl} target="_blank"
          rel="noopener noreferrer" style={{color:"#086b58"}}>{t.ticker} · {t.nct}</a>)}
      </div>
    </details>
    <p style={{fontSize:12,margin:"13px 0 0",lineHeight:1.55}}>
      <strong>Independent scientific grades: 0 · Validated FDA forecasts: 0 ·
      Historical FDA backtests: 0.</strong> Pending approval/CRL and review-delay
      decisions remain ABSTAIN; accuracy NOT CALIBRATED.
    </p>
  </section>;
}
