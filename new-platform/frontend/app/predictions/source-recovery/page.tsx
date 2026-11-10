import {R89_HISTORICAL_SOURCE_RECOVERY} from
 "../../../lib/focus-r89-historical-source-recovery";
import OriginalHistoryRecoveryR89Client from "./OriginalHistoryRecoveryR89Client";
import {R89_NEW_PUBLIC_SOURCE_LEADS} from "../../../lib/focus-r89-new-public-source-leads";
import {R90_CANONICAL_RESULTS_RECOVERY} from "../../../lib/focus-r90-canonical-results-source-coverage";
import styles from "../evidence-gaps/EvidenceRecoveryBoardR68.module.css";

export const metadata={
 title:"Stage 4 Step 2 | 17 original-source recovery cases",
 description:"Reuse five original pivotal journal leads; inspect historical registry for 17 trials absent current uploaded protocol/SAP files, no scientific certification"
};
export default function OriginalSourceRecoveryR89Page(){
 const d=R89_HISTORICAL_SOURCE_RECOVERY;
 if(!d||!R89_NEW_PUBLIC_SOURCE_LEADS||!R90_CANONICAL_RESULTS_RECOVERY)return <main className={styles.coverage}>
  <h1>Original source recovery queue</h1>
  <p role="alert">The exact original 29/23 FOCUS study, publication or
   trial-source crosswalk failed; no reviews or source history are released.</p>
 </main>;
 return <main className={styles.coverage}>
   <div className={styles.eyebrow}>MAIN · REVISIONS 89–90 · STAGE 4 STEP 2</div>
   <h1>Original scientific evidence: historical source-recovery queue</h1>
   <p className={styles.intro}>{d.notice} Baseline registry evidence dated
    {" "}<strong>{d.sourceSnapshotDate} UTC</strong>.</p>
   <div className={styles.stats}>
     <div><small>Exact FOCUS trials</small><strong>{d.exactFocusTrialCount}</strong></div>
     <div><small>Current registry file gaps</small><strong>{d.missingPublicProtocolSapListingNcts}</strong></div>
     <div><small>Existing pivotal journal leads</small><strong>{d.originalPivotalPublisherLeadsInFiveStudyIndex}</strong></div>
     <div><small>Not indexed in five-study archive</small><strong>{d.unindexedPivotalPublicationInFiveStudyIndex}</strong></div>
     <div><small>Additional public conference/sponsor leads found</small>
      <strong>{R89_NEW_PUBLIC_SOURCE_LEADS.exactNctMatchedNewSourceLeads}</strong></div>
     <div><small>Pre-existing FOCUS issuer/SEC source links checked</small>
      <strong>{R90_CANONICAL_RESULTS_RECOVERY.alreadyHeldNineIssuerSecResultsLinksVerified}</strong></div>
     <div><small>Seventeen trial results-source research leads</small>
      <strong>{R90_CANONICAL_RESULTS_RECOVERY.sourceResultLeadCoverageForSeventeen}/17</strong></div>
     <div><small>Direct NCT text in nine issuer/SEC pages</small>
      <strong>{R90_CANONICAL_RESULTS_RECOVERY.directExactNctInNineReports}/9</strong></div>
     <div><small>Authenticated prospectively signed SAPs</small><strong>{d.independentlyAuthenticatedSignedProspectiveSAPs}</strong></div>
     <div><small>Qualified scientific signoffs</small><strong>{d.independentQualifiedScienceReviews}</strong></div>
   </div>
   <p className={styles.notice}>{R90_CANONICAL_RESULTS_RECOVERY.notice}
    The earlier nine without a new lead in the R89 pass already had
    issuer/SEC result links in the canonical 29-trial FOCUS snapshot.
    Those nine links were checked; five pages explicitly name the NCT and
    four rely on sponsor trial-name matching against the original registry.
    Source coverage is not evidence of signed SAP availability or a validated
    FDA forecast.
   </p>
   <p className={styles.notice}>
    Existing original journal links are shown directly for the five mapped
    publications. For each of the 17 trial records, request an exact official
    ClinicalTrials.gov historical version index, then inspect a version to
    identify original protocol/SAP listings and endpoint chronology.
    The historical registry endpoint may be inaccessible from this preview;
    access failure must never count as missing original evidence.
    These on-demand lookups are source research, not independent pre-unblinding
    plan authentication, trial success, or FDA outcome calibration.
   </p>
   <p className={styles.footer}>Additional research leads discovered on
    <strong> {R89_NEW_PUBLIC_SOURCE_LEADS.researchDate}</strong>:
    {R89_NEW_PUBLIC_SOURCE_LEADS.conferenceSupplementAbstractLeads} publisher
    conference abstract and {R89_NEW_PUBLIC_SOURCE_LEADS.sponsorPublicReportLeads}
    sponsor-reported disclosure records. These sources are not complete
    original prospective SAPs or clinical study reports. The historical
    original-version endpoint is still inaccessible from the preview server;
    use the public record-history links.</p>
   <OriginalHistoryRecoveryR89Client rows={d.rows}
     newLeads={R89_NEW_PUBLIC_SOURCE_LEADS.rows}
     canonicalSourceLeads={R90_CANONICAL_RESULTS_RECOVERY.rows}/>
   <p className={styles.footer}>
    <a href="/predictions/original-documents/chronology">
     Return to dated 23-file original SAP chronology
    </a>
    {" · "}
    <a href="/predictions/original-documents">
     Original 29-trial document inventory and PDF checksums
    </a>.
    R89 does not update clinical grades, the 29-trial population, the 23
    provisional review cycles, or production.
   </p>
 </main>;
}
