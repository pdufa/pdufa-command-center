"use client";

import styles from "./FunnelWorkspace.module.css";

type Props={
  poolNcts:number|null;
  pipelineResearch:{screenedTrials:number;screenDate:string;qualification:"NOT_VERIFIED"}|null;
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
  poolNcts,pipelineResearch,selectedTrials,selectedStages,totalStages,selectedStageLabels,selectedDesignationLabels,selectedDesignations,
  designationUniqueTrials,designationCoverage,loading,error,searchActive,sourceDate,sourceState
}:Props){
  const filterActive=selectedStages>0||selectedDesignations>0;
  const noNctLink=selectedDesignations>0&&designationCoverage?.noVerifiedNctLinks===true;
  const trialStatus=!filterActive?"0":loading?"…":error?"Unavailable":
    noNctLink?"Not established":!pipelineResearch?"Not verified":selectedTrials===null?"Unavailable":num(selectedTrials);
  const allStages=selectedStages===totalStages;
  const shouldCompare=selectedDesignations>0&&!searchActive&&allStages&&!loading&&!error&&!noNctLink&&!!pipelineResearch;
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
        <div className={pipelineResearch?styles.toolsFunnelValue:styles.toolsFunnelValueUnverified}>
          {pipelineResearch?num(pipelineResearch.screenedTrials):"Not verified"}
        </div>
        <p>{pipelineResearch?"Completed Phase 3 NCTs · dated research screen":"Restricted Pipeline count unavailable"}</p>
        <small>{pipelineResearch
          ?"$300M–$10B census dated "+pipelineResearch.screenDate+
            ". Exact NCT/ticker matches only. Full original restrictions: NOT VERIFIED."
          :"Original listing, cap, final-readout and rights checks are not fully reconciled."}</small>
      </div>
      <span className={styles.toolsFunnelArrow} aria-hidden="true">→</span>
      <div className={styles.toolsFunnelCard+" "+styles.toolsFunnelTrials}>
        <div className={styles.toolsFunnelCardHead}><span aria-hidden="true">◎</span><h3>TRIALS</h3></div>
        {selectedDesignations>0&&designationCoverage&&!loading&&!error
          ?<div className={styles.toolsFunnelUnlinkedResult} role="status" aria-live="polite" aria-atomic="true">
            <div className={styles.toolsFunnelNctUnknown} role="group" aria-label="Unique NCT clinical trial count">
              <span>UNIQUE NCT TRIAL COUNT AFTER SCREEN</span>
              <strong>{trialStatus}</strong>
              <small>{noNctLink
                ?"Exact trial IDs and clinical stages are not established for these FDA programs."
                :"Documented matches after the dated PIPELINE screen and selected clinical stages; incomplete FDA-to-NCT evidence, not an exhaustive trial census."}</small>
            </div>
            <div className={styles.toolsFunnelProgramBand} role="group" aria-label="FDA program record count, not clinical trials">
              <span>FDA APPLICATION / PROGRAM RECORDS</span>
              <strong>{num(designationCoverage!.sourcePrograms)}</strong>
              <small>Documented programs — NOT {num(designationCoverage!.sourcePrograms)} distinct trials.
                {" "}{num(designationCoverage!.linkedNcts)} crosswalk-linked NCTs in the unrestricted POOL before applying the dated PIPELINE screen.</small>
            </div>
          </div>
          :<>
            <div className={styles.toolsFunnelValue} role="status" aria-live="polite" aria-atomic="true">{trialStatus}</div>
            <p>{selectedDesignations>0?"Documented linked NCT matches":"Selected clinical trial matches"}</p>
            <small>{!pipelineResearch
              ?"Dated Pipeline screen unavailable; POOL-only detail below is NOT a qualified count"
              :filterActive
                ?selectedDesignations>0
                  ?"After the same dated Phase 3 screen; FDA-to-NCT evidence is partial"
                  :"After the same dated Phase 3 screen and selected stages"
                :"0 filters checked"}</small>
          </>}
      </div>
    </div>
    <p className={styles.toolsFunnelIntegrity}>
      {pipelineResearch
        ?"TRIALS intersects the dated screened NCT subset with your selected stages and FDA categories. "
        :"TRIALS cannot show an after-restrictions count until the dated census reconciles. "}
      <strong>Current full PIPELINE eligibility is not yet verified.</strong>
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
