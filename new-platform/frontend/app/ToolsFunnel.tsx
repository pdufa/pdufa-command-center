"use client";

import styles from "./FunnelWorkspace.module.css";

type Props={
  poolNcts:number|null;
  selectedTrials:number|null;
  selectedStages:number;
  totalStages:number;
  selectedStageLabels:string[];
  selectedDesignationLabels:string[];
  selectedDesignations:number;
  designationUniqueTrials:number|null;
  designationCoverage:{sourcePrograms:number;unlinkedPrograms:number;linkedNcts:number;noVerifiedNctLinks:boolean}|null;
  loading:boolean;
  error:string;
  searchActive:boolean;
  sourceDate:string;
  sourceState:string;
};
const num=(value:number)=>value.toLocaleString("en-US");

/**
 * POOL -> PIPELINE -> TRIALS is a visual research workflow. Do not conflate
 * stage-filtered POOL matches with verified post-Phase-3 PIPELINE eligibility.
 */
export default function ToolsFunnel({
  poolNcts,selectedTrials,selectedStages,totalStages,selectedStageLabels,selectedDesignationLabels,selectedDesignations,
  designationUniqueTrials,designationCoverage,loading,error,searchActive,sourceDate,sourceState
}:Props){
  const filterActive=selectedStages>0||selectedDesignations>0;
  const noNctLink=selectedDesignations>0&&designationCoverage?.noVerifiedNctLinks===true;
  const trialStatus=!filterActive?"0":loading?"…":error?"Unavailable":
    noNctLink?"Not established":selectedTrials===null?"Unavailable":num(selectedTrials);
  const allStages=selectedStages===totalStages;
  const shouldCompare=selectedDesignations>0&&!searchActive&&allStages&&!loading&&!error&&!noNctLink;
  const parity=shouldCompare&&designationUniqueTrials!==null&&selectedTrials!==null
    ?designationUniqueTrials===selectedTrials:null;
  const date=sourceDate&&sourceDate!=="Not recorded"?sourceDate:"Date not available";
  const stagesLabel=selectedStages===totalStages?"All "+totalStages+" stages":selectedStages<=3?selectedStageLabels.join(", "):selectedStages+" stages";
  const designationsLabel=selectedDesignationLabels.length<=2?selectedDesignationLabels.join(", "):selectedDesignationLabels.length+" FDA categories";

  return <section className={styles.toolsFunnel} aria-label="POOL to PIPELINE to TRIALS filter flow">
    <div className={styles.toolsFunnelHeading}>
      <div>
        <h2>POOL <span aria-hidden="true">→</span> PIPELINE <span aria-hidden="true">→</span> TRIALS</h2>
        <p>Three bordered stages. Numbers update from source-backed research, not example values.</p>
      </div>
      <span className={styles.toolsFunnelDate}>POOL source: {date}</span>
    </div>
    {filterActive&&<div className={styles.toolsFunnelActiveFilters} aria-label="Currently checked TOOLS filters">
      <strong>SELECTED FILTERS</strong>
      {selectedDesignations>0&&<span>FDA: {designationsLabel}</span>}
      {selectedStages>0&&<span>Stages: {stagesLabel}</span>}
      {searchActive&&<span>Text search active</span>}
    </div>}
    <div className={styles.toolsFunnelSteps}>
      <div className={styles.toolsFunnelCard+" "+styles.toolsFunnelPool}>
        <div className={styles.toolsFunnelCardHead}><span aria-hidden="true">▤</span><h3>POOL</h3></div>
        <div className={styles.toolsFunnelValue}>{poolNcts===null?"—":num(poolNcts)}</div>
        <p>Unique NCT studies</p>
        <small>Unrestricted clinical-trial inventory</small>
      </div>
      <span className={styles.toolsFunnelArrow} aria-hidden="true">→</span>
      <div className={styles.toolsFunnelCard+" "+styles.toolsFunnelPipeline}>
        <div className={styles.toolsFunnelCardHead}><span aria-hidden="true">▽</span><h3>PIPELINE</h3></div>
        <div className={styles.toolsFunnelValueUnverified}>Not verified</div>
        <p>Restricted qualified trials</p>
        <small>Listing, market cap and post–Phase 3 gates still need current verification</small>
      </div>
      <span className={styles.toolsFunnelArrow} aria-hidden="true">→</span>
      <div className={styles.toolsFunnelCard+" "+styles.toolsFunnelTrials}>
        <div className={styles.toolsFunnelCardHead}><span aria-hidden="true">◎</span><h3>TRIALS</h3></div>
        {noNctLink&&!loading&&!error
          ?<div className={styles.toolsFunnelUnlinkedResult} role="status" aria-live="polite" aria-atomic="true">
            <div className={styles.toolsFunnelNctUnknown} role="group" aria-label="Unique NCT clinical trial count">
              <span>UNIQUE NCT TRIAL COUNT</span>
              <strong>{trialStatus}</strong>
              <small>Trial IDs and phases have not been verified</small>
            </div>
            <div className={styles.toolsFunnelProgramBand} role="group" aria-label="FDA program record count, not clinical trials">
              <span>FDA APPLICATION / PROGRAM RECORDS</span>
              <strong>{num(designationCoverage!.sourcePrograms)}</strong>
              <small>Documented programs — NOT {num(designationCoverage!.sourcePrograms)} distinct trials</small>
            </div>
          </div>
          :<>
            <div className={styles.toolsFunnelValue} role="status" aria-live="polite" aria-atomic="true">{trialStatus}</div>
            <p>{selectedDesignations>0?"Documented linked NCT matches":"Selected POOL trial matches"}</p>
            <small>{filterActive?selectedDesignations>0?"Partial FDA-to-NCT evidence; not comprehensive":"Calculated from selected clinical stages":"0 filters checked"}</small>
          </>}
      </div>
    </div>
    <p className={styles.toolsFunnelIntegrity}>
      TRIALS uses the full POOL. <strong>PIPELINE eligibility is not yet verified.</strong>
      {sourceState==="PARTIAL"?" POOL source coverage: PARTIAL.":""}
    </p>
    <details className={styles.toolsFunnelRestrictions}>
      <summary>Required PIPELINE restrictions — awaiting full verification</summary>
      <ul>
        <li>Publicly traded U.S.-listed issuer</li>
        <li>Current source-verified market cap $300 million–$10 billion</li>
        <li>Completed pivotal Phase 3 or independently verified final pivotal readout</li>
        <li>U.S. FDA program and exact drug–indication linkage</li>
        <li>Active program, verified sponsor and commercial rights</li>
      </ul>
      <p>These are required eligibility checks, not five automatically passed or applied restrictions.</p>
    </details>
    {noNctLink&&!loading&&!error&&<details className={styles.toolsFunnelRestrictions}>
      <summary>Why are the FDA program count and trial count different?</summary>
      <p>{num(designationCoverage!.sourcePrograms)} FDA application/program records are documented, but their NCT trial links are not verified.
        {allStages?" Selecting all stages cannot establish the number of clinical trials for these programs.":""}
        Program-record counts must not be presented as verified trial counts.</p>
      <p>See the FDA source-program spreadsheet below for each regulatory record and its evidence link.</p>
    </details>}
    {shouldCompare&&<p className={parity===true?styles.toolsFunnelParityPass:styles.toolsFunnelParityWarning} role="status">
      {parity===true
        ?"All-stage check passed: "+num(selectedTrials!)+" matched trials = "+num(designationUniqueTrials!)+" linked designation trials."
        :parity===false
          ?"Count mismatch: selecting every clinical stage should equal the designation-only linked-trial count. These numbers need reconciliation."
          :"All-stage parity could not be verified from the available source counts."}
    </p>}
    {selectedDesignations>0&&searchActive&&<p className={styles.toolsFunnelIntegrity}>
      An active text search may reduce the trial count below the unsearched designation total.
    </p>}
  </section>;
}
