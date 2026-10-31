"use client";
import Link from "next/link";
import {usePathname} from "next/navigation";
const links=[
 {label:"DASHBOARD",href:"/"},
 {label:"GOAL",href:"/?section=GOAL"},
 {label:"SCANS",href:"/?section=SCANS"},
 {label:"RESULTS",href:"/?section=RESULTS"},
 {label:"PIPELINE",href:"/?section=PIPELINE"},
 {label:"#1",href:"/patient-population"},
 {label:"GEM JR",href:"/?section=GEM_JR"},
 {label:"GEM",href:"/?section=GEM"},
 {label:"WT",href:"/?section=WT"},
 {label:"RESTRICTIONS",href:"/?section=RESTRICTIONS"},
 {label:"PREDICTIONS",href:"/?section=PREDICTION"},
 {label:"SYSTEM STATUS",href:"/installation-audit"},
 {label:"PREDICTION PILOT",href:"/prediction-pilot"}
];
export default function GlobalNavigation(){
 const pathname=usePathname();
 return <nav aria-label="Site navigation" style={{position:"sticky",top:0,zIndex:1000,background:"#10233a",color:"#fff",borderBottom:"2px solid #16a085",padding:"9px 12px",display:"flex",gap:8,alignItems:"center",overflowX:"auto",whiteSpace:"nowrap",WebkitOverflowScrolling:"touch"}}>
  <strong style={{marginRight:12,fontSize:13,flexShrink:0}}>PDUFA</strong>
  {links.map(link=><Link key={link.label} href={link.href} aria-current={pathname===link.href?"page":undefined} style={{color:"#fff",textDecoration:"none",fontSize:12,fontWeight:700,padding:"8px 10px",border:"1px solid #45627b",borderRadius:6,flexShrink:0}}>{link.label}</Link>)}
 </nav>;
}
