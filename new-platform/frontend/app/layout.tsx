import "./globals.css";
import GlobalNavigation from "./GlobalNavigation";
import type { Metadata } from "next";
export const metadata: Metadata = {
 title: "PDUFA Command Center — POOL → PIPELINE",
 description: "Next.js research platform for a preserved master POOL, verified post–Phase 3 issuer eligibility, FDA evidence and commercial assessments."
};
export default function RootLayout({children}:{children:React.ReactNode}){
 return <html lang="en"><body><GlobalNavigation/>{children}</body></html>;
}
