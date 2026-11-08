import type {Metadata} from "next";
import Link from "next/link";
import InstallationProgressDashboard from "../main/InstallationProgressDashboard";
export const metadata:Metadata={
 title:"PDUFA Precision Monitoring Dashboard — MAIN",
 description:"Evidence-based installation, POOL, FOCUS and 12 medical research-level checkpoints."
};
export const dynamic="force-dynamic";
export default function PrecisionMonitor(){
 return <main className="shell" style={{maxWidth:1250,margin:"0 auto",padding:"20px 12px 45px"}}>
  <div className="topline">PDUFA · MAIN · PRECISION MONITOR</div>
  <h1>Precision Monitoring Dashboard</h1>
  <p>Independent, read-only installation and health monitoring. POOL and FOCUS remain the only active trial populations; retired analysis remains excluded.</p>
  <p>FDA approval, CRL and review-delay predictions are <strong>ABSTAIN</strong> pending independent validation. Certainty is not yet rated.</p>
  <p><Link href="/main">MAIN acceptance gates</Link> · <Link href="/focus">FOCUS trial evidence</Link></p>
  <InstallationProgressDashboard/>
 </main>;
}