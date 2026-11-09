import history from "../../../data/acacia-original-history-revision36.json";

const archiveBase="https://github.com/pdufa/pdufa-command-center/blob/feature/medical-stage4-verified-method-matrix-20261108/";
const sourceDirectory=archiveBase+history.sourceDirectory+"/";
const linkStyle={color:"#8ee7da",overflowWrap:"anywhere"} as const;
const cardStyle={border:"1px solid #365b6b",borderRadius:8,padding:10,minWidth:0,background:"#142b3b"} as const;

export default function PilotOriginalHistoryEvidence(){
  return <details style={{border:"1px solid #397b82",borderRadius:9,padding:12,
    background:"#102434",color:"#e1f2f1",marginBottom:12,minWidth:0}}
    aria-label="Revision 36 original ACACIA-HCM registry evidence">
    <summary style={{cursor:"pointer",fontWeight:800,color:"#91e4d6"}}>
      Original registry evidence recovered · v26, v27, v29 and v30
    </summary>
    <p style={{fontSize:12,lineHeight:1.6}}>
      <strong>ACACIA-HCM · {history.nct} · {history.protocol}.</strong>{" "}
      Four original public registry versions were captured on November 9, 2026, with exact trial,
      version, date and byte-hash checks. {history.interpretation.registryChange}
    </p>
    <p style={{fontSize:12,lineHeight:1.6}}>{history.interpretation.accessLimit}</p>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(100%,220px),1fr))",gap:8}}>
      {history.versions.map(version=><article key={version.version} style={cardStyle}
        aria-label={"Original registry version "+version.version}>
        <strong>v{version.version} · {version.primary.length} primary endpoint{version.primary.length===1?"":"s"}</strong>
        <dl style={{fontSize:12,lineHeight:1.6,margin:"8px 0"}}>
          <dt>Submitted</dt><dd style={{marginLeft:0}}>{version.submitted}</dd>
          <dt>Publicly posted</dt><dd style={{marginLeft:0}}>{version.posted} · {version.postingType}</dd>
          <dt>Enrollment</dt><dd style={{marginLeft:0}}>{version.enrollment.count} · <strong>{version.enrollment.type}</strong></dd>
          <dt>Reported phase</dt><dd style={{marginLeft:0}}>Phase III · independent signoff pending</dd>
        </dl>
        <details>
          <summary style={{cursor:"pointer",fontSize:12,fontWeight:750}}>Endpoint definitions and original source receipt</summary>
          <ol style={{fontSize:12,lineHeight:1.6,paddingLeft:20}}>
            {version.primary.map(endpoint=><li key={endpoint.measure}>
              <strong>{endpoint.measure}</strong><br/>{endpoint.timeFrame}<br/>{endpoint.description}
            </li>)}
          </ol>
          <p style={{fontSize:12}}>{version.secondaryCount} secondary endpoint definitions are preserved in the original record.</p>
          <p style={{fontSize:12,lineHeight:1.7}}>
            <a href={version.pageUrl} target="_blank" rel="noopener noreferrer" style={linkStyle}>Official public history page</a><br/>
            <a href={version.sourceUrl} target="_blank" rel="noopener noreferrer" style={linkStyle}>Original registry response · API index {version.apiIndex}</a><br/>
            <a href={sourceDirectory+version.artifact} target="_blank" rel="noopener noreferrer" style={linkStyle}>Preserved original bytes · {version.sourceBytes.toLocaleString("en-US")} bytes</a>
          </p>
          <p style={{fontSize:11,lineHeight:1.6,overflowWrap:"anywhere"}}>
            Retrieved: {version.retrievedAt}<br/>SHA-256: <code>{version.sourceSha256}</code>
          </p>
        </details>
      </article>)}
    </div>
    <details style={{marginTop:10}}>
      <summary style={{cursor:"pointer",fontWeight:750,fontSize:12}}>Interpretation, unresolved evidence and review requirements</summary>
      <ul style={{fontSize:12,lineHeight:1.65,paddingLeft:20}}>
        <li>{history.interpretation.temporalLimit}</li>
        <li>{history.interpretation.populationLimit}</li>
        <li>{history.interpretation.clinicalLimit}</li>
        <li>Final locked SAP, original population accounting, heart-failure definitions and reporting windows,
          and the treatment-interruption denominator remain unresolved.</li>
      </ul>
      <p style={{fontSize:12,lineHeight:1.65}}>
        Existing review positions enriched: <strong>{history.mappedExistingPositions.join(", ")}</strong>.
        No new method positions are marked complete. The queue remains <strong>18 mapped source leads</strong>{" "}
        and <strong>782 positions not source mapped</strong>. Official clinical grades: <strong>0/800</strong>.
        Authorized independent review remains required.
      </p>
      <p style={{fontSize:12,lineHeight:1.65}}>
        <a href={sourceDirectory+"validated_comparison.json"} target="_blank" rel="noopener noreferrer" style={linkStyle}>Validated original comparison</a>{" "}·{" "}
        <a href={sourceDirectory+"public_browser_receipt.json"} target="_blank" rel="noopener noreferrer" style={linkStyle}>Public browser receipt and prior access failure</a><br/>
        Original history index SHA-256: <code style={{overflowWrap:"anywhere"}}>{history.originalHistoryIndex.sha256}</code>
      </p>
    </details>
    <p style={{fontSize:12,lineHeight:1.6,marginBottom:0}}>
      APPROVAL: <strong>ABSTAIN</strong> · CRL: <strong>ABSTAIN</strong> · REVIEW DELAY: <strong>ABSTAIN</strong>.<br/>
      Certainty: <strong>NOT VALIDATED</strong> · Accuracy: <strong>NOT CALIBRATED</strong>.
    </p>
  </details>;
}
