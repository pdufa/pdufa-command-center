import snapshot from "../../lib/fda-holdout-reconstruction-snapshot.json";
import { auditHoldoutReconstruction, type HoldoutCase } from "../../lib/fda-holdout-reconstruction";

const labels: Record<string, string> = {
  PREDECISION_RESEARCH_CANDIDATE: "Pre-cutoff research observation · not independently certified",
  EXCLUDED_OUTCOME_ONLY: "Excluded from prediction inputs · FDA outcome evidence",
  EXCLUDED_AFTER_RECONSTRUCTION_CUTOFF: "Excluded · available after reconstruction cutoff",
  EXCLUDED_AFTER_AUDIT_SNAPSHOT: "Excluded · after audit snapshot",
  QUARANTINED_UNKNOWN_AVAILABILITY: "Quarantined · public availability unknown",
  QUARANTINED_PRINTED_DATE_ONLY: "Quarantined · printed date does not prove availability",
};
function Facts({title, values}: {title: string; values: string[]}) {
  return <><h4>{title}</h4><ul>{values.map((value, i) => <li key={i}>{value}</li>)}</ul></>;
}
function CaseDetails({record}: {record: HoldoutCase}) {
  const ticker = record.event_key.split("|")[0];
  return <details style={{padding:"10px 0",borderTop:"1px solid #cbd5e1"}}>
    <summary style={{cursor:"pointer",fontWeight:650}}>{ticker} · {record.application_id} · INSUFFICIENT EVIDENCE</summary>
    <p>{record.indication}</p>
    <dl style={{display:"grid",gridTemplateColumns:"minmax(150px, 1fr) 2fr",gap:"6px 14px"}}>
      <dt>Legacy PDUFA target</dt><dd style={{margin:0}}>{record.legacy_goal_date}</dd>
      <dt>Recorded FDA action</dt><dd style={{margin:0}}>{record.action_date}</dd>
      <dt>Research cutoff</dt><dd style={{margin:0}}>{record.reconstruction_cutoff}</dd>
      <dt>Original prediction cutoff</dt><dd style={{margin:0}}>Not verified</dd>
      <dt>Historical validation</dt><dd style={{margin:0}}>Not eligible · probabilities, uncertainty range and accuracy withheld</dd>
    </dl>
    <p><strong>FDA action document:</strong> {record.action_document.status.replaceAll("_", " ")}. <a href={record.action_document.source_url} target="_blank" rel="noopener noreferrer">FDA source</a>.
      Original PDF bytes are not retained; original public availability is unverified.</p>
    <Facts title="Supporting research factors" values={record.supporting_factors}/>
    <Facts title="Opposing evidence and unresolved risks" values={record.opposing_factors}/>
    <details><summary>Evidence matrix · {record.source_classification.length} observations</summary>
      <p>Research dates are conservative bounds. An outcome letter or later statement cannot support a pre-decision prediction.</p>
      <ul>{record.source_classification.map(source => <li key={source.source_id} style={{marginBottom:12}}>
        <strong>{labels[source.classification]}</strong><br/>
        {source.finding}<br/>
        <a href={source.source_url} target="_blank" rel="noopener noreferrer">Original source</a>
        {source.availability_source_url && <> · <a href={source.availability_source_url} target="_blank" rel="noopener noreferrer">Availability index</a></>}
        <br/>Recorded source date: {source.available_on ?? "Unknown"} · {source.availability_basis.replaceAll("_", " ")}
      </li>)}</ul>
    </details>
    <details><summary>SCIENCE · eight layers, 40 questions and 20 investigation depths</summary>
      <p>Independently certified assessments: 0/40. Certified depths: 0/20. Source observations are leads for investigation; they do not satisfy an assessment. The twenty-level research protocol defines the required analysis and completion artifacts. It has not independently validated the investigation method or completed these case investigations.</p>
      {Array.from({length:8}, (_, i) => {
        const questions = record.science_worklist.filter(q => q.layer === i + 1);
        return <details key={i}><summary>{i + 1}. {questions[0].layer_name}</summary>
          <ul>{questions.map(q => {
            const investigation = record.scientific_dossier.layers[i].questions.find(item => item.question_id === q.question_id)!;
            return <li key={q.question_id}><strong>{q.question_id}: {q.question}</strong><br/>
              {q.source_ids.length ? `Research source leads: ${q.source_ids.join(", ")}. Independent review remains outstanding.` : "Required evidence not reconstructed for this question."}
              <br/>Required documents: {investigation.required_evidence}.
              <ul>{investigation.uncertainties.map((uncertainty, index) => <li key={index}>{uncertainty}</li>)}</ul>
            </li>;
          })}</ul>
        </details>;
      })}
      <details><summary>Twenty-level investigation protocol · 0/20 independently completed</summary>
        <p>Protocol version: {record.scientific_dossier.depth_framework.catalog_version}. Source leads identify work to review; they are not completion evidence.</p>
        {record.scientific_dossier.depth_framework.levels.map(depth => <details key={depth.level_id}>
          <summary>{depth.depth_level}. {depth.title} · independent review missing</summary>
          <p>{depth.objective}</p>
          <p>Scientific questions: {depth.question_ids.join(", ")}. {depth.source_lead_ids.length
            ? `Candidate source leads: ${depth.source_lead_ids.join(", ")}.`
            : "Pre-cutoff source leads are missing for these questions."}</p>
          <Facts title="Required analysis" values={depth.requirements}/>
          <Facts title="Completion artifacts required" values={depth.completion_artifacts}/>
          <p>All completion artifacts require independent adjudication.
            {depth.blocking_prerequisite_levels.length > 0 && <> Prerequisite levels still incomplete: {depth.blocking_prerequisite_levels.join(", ")}.</>}
            {depth.question_ids_without_source_leads.length > 0 && <> Questions without candidate sources: {depth.question_ids_without_source_leads.join(", ")}.</>}
          </p>
        </details>)}
      </details>
    </details>
    <details><summary>Historical comparator research</summary>
      <p>These are unadjudicated research contexts, not validated matched comparators or independent training cases.</p>
      <ul>{record.related_precedents.map((p, i) => <li key={i}><strong>{p.name}</strong>: {p.comparison}
        {p.source_url && <> <a href={p.source_url} target="_blank" rel="noopener noreferrer">Source context</a></>}
      </li>)}</ul>
    </details>
    <details><summary>Missing requirements and reasons for exclusion</summary>
      <Facts title="Outstanding evidence" values={record.missing_documents}/>
      <Facts title="Validation blockers" values={record.blockers.map(value => value.replaceAll("_", " "))}/>
    </details>
  </details>;
}

export default function HistoricalHoldoutReconstruction({value = snapshot}: {value?: unknown}) {
  let report;
  try { report = auditHoldoutReconstruction(value); }
  catch { return <section aria-label="Historical FDA reconstruction"><h2>Historical FDA reconstruction</h2>
    <p role="alert">Historical reconstruction could not be verified. Evidence counts and predictions withheld.</p></section>; }
  return <section aria-label="Historical FDA reconstruction" style={{margin:"22px 0",padding:"16px",border:"1px solid #cbd5e1",borderRadius:8}}>
    <h2>MAIN · SCIENCE / OUTCOME historical reconstruction</h2>
    <p><strong>Dated research snapshot: {report.asOf}.</strong> Six priority cases are joined to {report.historyRecords} legacy prediction records. Independently validated cases: <strong>0</strong>. OUTCOME and MAIN abstain for every case.</p>
    <p>The recovered model and prediction locks postdate these FDA actions. Original prediction freezes and training chronology are unverified. Accuracy, calibration, approval/CRL probabilities and prediction confidence remain unmeasured. This research view does not change Pipeline, GEM JR, GEM, WT or FS/FA memberships.</p>
    {report.caseReports.map(record => <CaseDetails key={record.event_key} record={record}/>)}
  </section>;
}
