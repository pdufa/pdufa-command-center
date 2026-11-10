import {FOCUS_R69_REGISTRY_PUBLICATION_LEADS} from
  "../../../lib/focus-r69-original-publication-leads";
import PublicationEvidenceRoleR70 from "./PublicationEvidenceRoleR70";
import OriginalPubmedArticleMetadataR70 from "./OriginalPubmedArticleMetadataR70";
import ScientificOriginalsIntakeR71 from "./ScientificOriginalsIntakeR71";
import styles from "./OriginalPublicationLeadsR69.module.css";

/** Read-only external PubMed search leads derived from archived registry
 * referencesModule. Does NOT independently open, assess or adjudicate papers.
 */
export default function OriginalPublicationLeadsR69({nct}:{nct:string}){
 const sources=FOCUS_R69_REGISTRY_PUBLICATION_LEADS;
 if(!sources)return <section className={styles.box}
  aria-label={"R69 registry publication leads for "+nct}>
   <strong>Original registry publication leads</strong>
   <p role="alert">The pinned original source reference list could not be verified.
     Candidate publication links are withheld.</p>
  </section>;
 const trial=sources.cases.find(x=>x.nct===nct);
 if(!trial)return null;
 return <section className={styles.box}
   aria-label={"R69 registry publication leads for "+nct}>
  <div className={styles.kicker}>REVISION 69 · REGISTRY-LISTED PUBMED REFERENCES</div>
  <h3>Publication leads for {nct} · {trial.sourceReferenceLeads.length}</h3>
  <p>These are PubMed references listed as <strong>DERIVED</strong> in the
   original registry copy. A reference could describe background science,
   prior studies or another patient population. <strong>Its exact NCT match
   and pivotal endpoint relevance have NOT been verified.</strong></p>
  {trial.sourceReferenceLeads.length>0?
   <ul className={styles.refs}>{trial.sourceReferenceLeads.map(x=><li key={x.pmid}>
    <a href={x.pubmedUrl} target="_blank" rel="noopener noreferrer">
      Open PubMed PMID {x.pmid}</a>
    <span>Unreviewed source lead · Not an accepted efficacy/safety result</span>
   </li>)}</ul>:
   <p>No PubMed reference is listed in this retained registry copy. This
    <strong> does not mean no relevant study publication exists.</strong></p>}
  <PublicationEvidenceRoleR70 nct={nct}/>
  <OriginalPubmedArticleMetadataR70 nct={nct}/>
  <ScientificOriginalsIntakeR71 nct={nct}/>
  <div className={styles.links}>
   <a href={"https://pubmed.ncbi.nlm.nih.gov/?term="+encodeURIComponent(nct)}
      target="_blank" rel="noopener noreferrer">
      Search PubMed for this exact NCT</a>
   <a href={sources.sourceArchiveUrl} target="_blank" rel="noopener noreferrer">
      Verify original R69 reference receipt</a>
  </div>
  <p className={styles.warning}>Next scientific gate: read the full publication,
   independently verify the exact study identifier, primary endpoint data,
   comparator and original pre-unblinding protocol/SAP version; obtain authorized
   reviewer signoff. <strong>Confirmed exact-trial primary outcomes: 0</strong>.
   FDA outcome: <strong>ABSTAIN</strong>.</p>
 </section>;
}
