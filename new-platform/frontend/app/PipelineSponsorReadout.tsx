import styles from "./FunnelWorkspace.module.css";
import { getSponsorPhase3Readout } from "../lib/pipeline-source-reported-readouts";

/** Source-backed facts, initially collapsed; not an FDA decision or modeled score. */
export default function PipelineSponsorReadout({nctId,ticker}:{nctId:string;ticker:string}){
 const fact=getSponsorPhase3Readout(nctId,ticker);
 if(!fact)return null;
 return <details className={styles.dossierSection} aria-label={"Sponsor-reported Phase 3 results for "+nctId}>
  <summary><strong>Phase 3 sponsor-reported primary outcome · {fact.study}</strong><span>Source linked · review required</span></summary>
  <div className={styles.dossierEvidence}>
   <p><strong>Therapy:</strong> {fact.therapy} · <strong>Indication:</strong> {fact.indication}</p>
   <p><strong>Public readout:</strong> {fact.sourcePublished} · <a href={fact.sourceUrl} target="_blank" rel="noopener noreferrer">Original sponsor announcement</a></p>
   <p><strong>Primary clinical remission at Week {fact.weeks}:</strong> {fact.remissionExperimentalPct}% ({fact.treatmentEvents}/{fact.treatmentN}) with 50 mg oral obefazimod versus {fact.remissionPlaceboPct}% ({fact.placeboEvents}/{fact.placeboN}) with placebo.</p>
   <p><strong>Reported placebo-adjusted difference:</strong> +{fact.placeboAdjustedDifferencePp} percentage points ({fact.pValue}). Not a comparison to an approved competitor.</p>
   <p><strong>Study population:</strong> {fact.population}</p>
   <p><strong>Important limitation:</strong> {fact.caveat}</p>
   <p><strong>Program:</strong> one obefazimod–ulcerative colitis program across ABTECT-1, ABTECT-2 and maintenance. These three NCT studies must not be counted as three separate commercial products.</p>
   <p className={styles.muted}>Primary sponsor release, awaiting independent review. Current U.S. listing, market cap, commercial rights, verified FDA PDUFA action date and regulatory outcome remain unestablished. No 20-assessment score or trading conclusion is inferred.</p>
  </div>
 </details>;
}
