"use client";
import Link from "next/link";
import {usePathname} from "next/navigation";
const links=[
 {label:"PIPELINE",href:"/pipeline"},
 {label:"SCAN",href:"/scans"},
 {label:"PREDICTIONS",href:"/predictions"},
 {label:"#1",href:"/patient-population"},
 {label:"SYSTEM STATUS",href:"/installation-audit"}
];
export default function GlobalNavigation(){
 const pathname=usePathname();
 return <nav aria-label="Site navigation" style={{position:"sticky",top:0,zIndex:1000,background:"#10233a",color:"#fff",borderBottom:"2px solid #16a085",padding:"9px 12px",display:"flex",gap:8,alignItems:"center",overflowX:"auto",whiteSpace:"nowrap",WebkitOverflowScrolling:"touch"}}>
  <strong style={{marginRight:12,fontSize:13,flexShrink:0}}>PDUFA</strong>
  {links.map(link=><Link key={link.label} href={link.href} aria-current={pathname===link.href?"page":undefined} style={{color:"#fff",textDecoration:"none",fontSize:12,fontWeight:700,padding:"8px 10px",border:"1px solid #45627b",borderRadius:6,flexShrink:0}}>{link.label}</Link>)}
 </nav>;
}
