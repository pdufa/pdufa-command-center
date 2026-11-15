const object=(x:unknown):x is Record<string,unknown>=>!!x&&typeof x==='object'&&!Array.isArray(x);
const text=(x:unknown)=>x===undefined||x===null?'Not reported':typeof x==='object'?JSON.stringify(x):String(x);
function Citation({value}:{value:unknown}){
 if(!object(value)||typeof value.source_url!=='string'||!value.source_url.startsWith('https://'))return null;
 return <div><a href={value.source_url} target="_blank" rel="noopener noreferrer">{text(value.locator)}</a> · Published {text(value.published_at)} · Retrieved {text(value.captured_at)}
  {typeof value.excerpt==='string'&&<blockquote style={{whiteSpace:'pre-wrap'}}>{value.excerpt}</blockquote>}
  <small style={{overflowWrap:'anywhere'}}>Original SHA-256 {text(value.raw_sha256)}</small>
 </div>;
}
function Checks({items}:{items:unknown}){
 if(!Array.isArray(items))return null;
 return <div>{items.filter(object).map((item,index)=><details key={index} open={item.state==='CONCERNS'}>
  <summary>{text(item.id)} · {text(item.state)}</summary><p>{text(item.explanation)}</p>
  {item.value!==undefined&&item.value!==null&&<pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere',maxHeight:300,overflow:'auto'}}>{JSON.stringify(item.value,null,2)}</pre>}
  {Array.isArray(item.citations)&&item.citations.map((citation,i)=><Citation key={i} value={citation}/>)}
 </details>)}</div>;
}
export default function ScientificTrialFindings({value}:{value:unknown}){
 if(!object(value)||value.kind!=='EXECUTED_SCIENTIFIC_TRIAL_ASSESSMENT')return null;
 const identity=object(value.trialIdentity)?value.trialIdentity:{};
 const observations=Array.isArray(value.observations)?value.observations.filter(object):[];
 const endpoints=observations.flatMap(x=>Array.isArray(x.endpointEvaluations)?x.endpointEvaluations.filter(object):[]);
 return <section aria-label="Executed scientific findings">
  <h4>Trial identity and scientific findings</h4>
  <p>Company/sponsor: {text(identity.company)} · Ticker: {identity.ticker?text(identity.ticker):'NOT VERIFIED'} · Candidate: {text(identity.candidate)} · Study code: {text(identity.studyCode)} · NCT: {text(identity.nct)}</p>
  <p>Indication: {text(identity.indication)}. Execution: {text(value.executionStatus)}. Registry sponsor identity does not independently verify a listed issuer/ticker.</p>
  <Checks items={value.checks}/>
  {endpoints.map((endpoint,index)=><section key={index} aria-label={'Endpoint '+text(endpoint.title)} style={{borderTop:'1px solid #abc9bd',marginTop:12}}>
   <h4>{text(endpoint.endpointType)} · {text(endpoint.title)}</h4>
   <p>{text(endpoint.description)}</p><p>Window: {text(endpoint.timeFrame)} · Analysis population: {text(endpoint.population)} · Unit: {text(endpoint.unit)}</p>
   <details><summary>Observed groups, denominators and measurements</summary><pre style={{whiteSpace:'pre-wrap'}}>{JSON.stringify({groups:endpoint.groups,denominators:endpoint.denominators,measurements:endpoint.reportedMeasurements},null,2)}</pre></details>
   {Array.isArray(endpoint.calculatedContrasts)&&endpoint.calculatedContrasts.filter(object).map((contrast,i)=><p key={i}><strong>{text(contrast.treatmentGroup)} versus {text(contrast.controlGroup)}:</strong> absolute difference {typeof contrast.absoluteDifferencePercentagePoints==='number'?contrast.absoluteDifferencePercentagePoints.toFixed(2):'unresolved'} percentage points. {text(contrast.limitation)}</p>)}
   {Array.isArray(endpoint.statisticalAnalyses)&&endpoint.statisticalAnalyses.filter(object).map((analysis,i)=>{
    const a=object(analysis.reported)?analysis.reported:{};
    return <p key={i}>Reported {text(a.paramType)}: {text(a.paramValue)}; {text(a.ciPctValue)}% CI {text(a.ciLowerLimit)}–{text(a.ciUpperLimit)}; p {text(a.pValue)}. Method: {text(a.statisticalMethod)}. {text(analysis.nominalSignificance)}. Interval check: {text(analysis.intervalConsistency)}. {text(analysis.limitation)}</p>;
   })}
   <Citation value={endpoint.citation}/>
  </section>)}
  {object(value.prerequisiteAssessments)&&Object.entries(value.prerequisiteAssessments).map(([level,prior])=>object(prior)?<details key={level}><summary>Executed prerequisite Level {level} · {text(prior.name)} · {text(prior.engineVersion)}</summary><Checks items={prior.checks}/></details>:null)}
  {Array.isArray(value.rejectedEvidence)&&value.rejectedEvidence.length>0&&<details><summary>Rejected evidence</summary><pre style={{whiteSpace:'pre-wrap'}}>{JSON.stringify(value.rejectedEvidence,null,2)}</pre></details>}
 </section>;
}
