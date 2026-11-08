import Link from "next/link";
import InstallationProgressDashboard from "../main/InstallationProgressDashboard";
import type {Metadata} from "next";
export const metadata:Metadata={
 title:"PDUFA Precision Monitoring Dashboard | MAIN",
 description:"Read-only evidence-backed installation, POOL/FOCUS and independent medical monitoring."
};
export const dynamic="force-dynamic";
export default function PrecisionMonitoringPage(){
 return <main className="shell" style={{maxWidth:1240,margin:"0 auto",padding:"20px 16px 48px"}}>
  <div className="topline">PDUFA COMMAND CENTER · MAIN</div>
  <h1>PDUFA Precision Monitoring Dashboard</h1>
  <p>Read-only installation and system-health evidence for POOL, FOCUS and twelve independent medical levels.
    A percentage measures verified installation checkpoints, not FDA prediction accuracy or clinical confidence.
    All unvalidated FDA outcomes stay <strong>ABSTAIN</strong>; certainty stays <strong>NOT VALIDATED</strong>.</p>
  <p><Link href="/main">MAIN acceptance</Link> · <Link href="/pool">POOL</Link> · <Link href="/focus">FOCUS</Link></p>
  <InstallationProgressDashboard/>
 </main>;
}
