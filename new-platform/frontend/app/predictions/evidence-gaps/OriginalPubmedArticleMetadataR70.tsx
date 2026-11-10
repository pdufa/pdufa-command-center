import {FOCUS_R70_ARTICLE_SOURCE} from "../../../lib/focus-r70-pubmed-article-source";
import styles from "./OriginalPubmedArticleMetadataR70.module.css";

/** PubMed original XML metadata/abstract only.
 * Explicit study-ID link is NOT qualified adjudication of pivotal efficacy.
 */
export default function OriginalPubmedArticleMetadataR70({nct}:{nct:string}){
  const source=FOCUS_R70_ARTICLE_SOURCE;
  if(!source)return <section className={styles.shell}
      aria-label={"R70 article metadata for "+nct}>
    <p role="alert">The original PubMed article source did not pass identity checks.
      Source classifications are withheld.</p>
  </section>;
  const trial=source.studies.find(x=>x.nct===nct);
  if(!trial)return null;
  return <section className={styles.shell}
      aria-label={"R70 article metadata for "+nct}>
    <p className={styles.eyebrow}>REVISION 70 · ORIGINAL NLM ARTICLE METADATA / ABSTRACT</p>
    <h3>Article source inspection · {nct}</h3>
    <p className={styles.intro}>Original PubMed XML metadata and available
      abstracts retrieved for <strong>{source.originalPubmedRecordsRetrieved} references</strong>
      across the seven NCTs with registry-listed leads. For all 11 references,
      PubMed links the ClinicalTrials.gov NCT in its databank; only eight mention the exact NCT
      within the article title or abstract. Neither proves a paper reports
      a prospectively defined pivotal Phase 3 outcome.</p>
    <div className={styles.list}>
      {trial.articles.map(article=><details key={article.pmid} className={styles.paper}>
        <summary>
          <strong>{article.title}</strong>
          <span>PMID {article.pmid} · {article.journal}</span>
          <small>{article.articleTextExplicitExactNct?
            "Exact NCT string in article title/abstract":
            "Exact NCT in PubMed databank only"}
            {" · "}NOT SCIENTIFICALLY ADJUDICATED</small>
        </summary>
        <div className={styles.content}>
          <p><strong>Source paper citation:</strong> {article.journal}.
            {article.doi?" DOI: "+article.doi:" DOI not supplied."}</p>
          <p><strong>PubMed indexed publication types:</strong>{" "}
            {article.pubmedPublicationTypes.join(", ")||"Not specified"}</p>
          {article.metadataCautions.length>0?
            <ul>{article.metadataCautions.map(s=><li key={s}>{s}</li>)}</ul>:
            <p>Source metadata alone cannot determine whether this paper
              reports the exact trial's pivotal efficacy endpoint.</p>}
          <p>Article metadata is not the full manuscript.
            <strong> Independent trial-phase, efficacy, safety, multiplicity,
              original SAP chronology and statistical review remain pending.</strong></p>
          <a href={article.pubmedUrl} target="_blank" rel="noopener noreferrer">
            Open original PubMed article PMID {article.pmid}</a>
        </div>
      </details>)}
    </div>
    <p className={styles.footer}>
      Research receipt: <a href={source.sourceArchiveUrl} target="_blank"
      rel="noopener noreferrer">Open original 11-article PubMed XML archive</a>.
      These are source-only metadata observations; <strong>0</strong> fully
      adjudicated pivotal trial outcomes, <strong>0</strong> qualified reviewer
      signatures, <strong>0/23</strong> independently validated FDA forecasts.
      Official outcome: <strong>ABSTAIN</strong>.
    </p>
  </section>;
}
