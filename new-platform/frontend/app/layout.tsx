import "./globals.css";
import GlobalNavigation from "./GlobalNavigation";
import type { Metadata } from "next";
export const metadata: Metadata = {
 title: "PDUFA Command Center — POOL → FOCUS",
 description: "Source-linked POOL and FOCUS trial research, independent medical intelligence, and evidence-based FDA assessment."
};
export default function RootLayout({children}:{children:React.ReactNode}){
 return <html lang="en"><body><GlobalNavigation/>{children}</body></html>;
}
