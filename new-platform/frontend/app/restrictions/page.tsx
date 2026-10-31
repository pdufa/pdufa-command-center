import type {Metadata} from "next";import Link from "next/link";
export const metadata:Metadata={title:"RESTRICTIONS — Post–Phase 3 Pipeline",description:"Independent mandatory market capitalization, listing and Phase 3 evidence gates."};
const rules=[
 {title:"1 · Current public listing",detail:"U.S.-listed company; live listing source, exact company and drug rights required."},
 {title:"2 · Market capitalization",detail:"$300 million–$10 billion inclusive, verified with a dated current-market source; old census values are only historical pointers."},
 {title:"3 · Post–Phase 3 pivotal evidence",detail:"Completed pivotal Phase 3 or independently verified final pivotal readout for the exact drug and indication. Registry completion alone does not prove successful efficacy."}
];
export default function RestrictionsPage(){return <main className="shell">
 <div className="topline">POOL → PIPELINE</div><h1>PIPELINE · Mandatory Eligibility Restrictions</h1>
 <p>Apply all three rules to the preserved POOL. Keep failures and unknowns visible as separate review reasons; never remove the underlying trial record.</p>
 <div style={{display:"grid",gap:12}}>{rules.map(r=><section key={r.title} className="panel"><h2>{r.title}</h2><p>{r.detail}</p></section>)}</div>
 <p>Historical final-readout and publicly-traded status require re-verification. This is a rule specification, not confirmation that the live 11,000+ universe has been fully screened.</p>
 <p><Link href="/pool">Open full POOL</Link> · <Link href="/pipeline">Open screening PIPELINE</Link></p>
 </main>}
