import Link from "next/link";
export const metadata={title:"FDA application investigations | PDUFA"};
/** No retired rating or score contributes to an FDA decision. */
export default function PredictionsPage(){
 return <main style={{maxWidth:1000,margin:"32px auto",padding:20}}>
  <h1>FDA application investigations</h1>
  <p>Application outcomes and review timing require independent clinical and regulatory evidence. Numerical approval probabilities are not published without a separately validated calibration model.</p>
  <p><Link href="/preview/deep-medical-intelligence">Open the independent Deep Medical Intelligence preview</Link>{" · "}<Link href="/focus">FOCUS candidates</Link></p>
 </main>;
}
