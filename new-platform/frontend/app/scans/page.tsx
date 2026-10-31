import type {Metadata} from "next";import PublishedScansPanel from "../PublishedScansPanel";
export const metadata:Metadata={title:"SCANS — POOL / PIPELINE Source Verification",description:"Clinical and regulatory scan controls, published reporting and independent Phase 3 posted-results collector."};
export default function ScansPage(){return <main className="shell"><h1>SCANS — Source Collections</h1><PublishedScansPanel/></main>;}
