import type {Metadata} from "next";
import Link from "next/link";
import InstallationProgressDashboard from "../main/InstallationProgressDashboard";
import PrecisionMonitoringConsole from "./PrecisionMonitoringConsole";

export const metadata:Metadata={
  title:"PDUFA Precision Monitoring Dashboard | MAIN",
  description:"Live source-linked installation status, 20 FOCUS ticker groups, 29 trial identities, and evidence-governed prediction readiness."
};
export const dynamic="force-dynamic";

export default function PrecisionMonitoringPage(){
  return <main className="shell" style={{maxWidth:1480,margin:"0 auto",padding:"12px 12px 44px"}}>
    <PrecisionMonitoringConsole/>
    <details style={{border:"1px solid #b5d1c2",borderRadius:12,padding:14,marginTop:16,background:"#f2f8f4"}} id="full-monitor-evidence">
      <summary style={{cursor:"pointer",fontWeight:800,color:"#164132",fontSize:17}}>
        Full installation evidence ledger · all checks, source revisions and FOCUS trial records
      </summary>
      <p style={{fontSize:13,color:"#36574a",margin:"12px 0"}}>
        The visual console above displays actual reported checks when available. Expand for individual evidence, source gaps,
        blocker details and saved medical history. An unavailable protected API never implies healthy operation.
      </p>
      <InstallationProgressDashboard/>
    </details>
    <p style={{fontSize:13,marginTop:18}}>
      <Link href="/main">MAIN technical acceptance</Link>{" · "}
      <Link href="/pool">POOL</Link>{" · "}
      <Link href="/focus">FOCUS</Link>{" · "}
      <Link href="/predictions">FDA prediction blockers</Link>
    </p>
  </main>;
}
