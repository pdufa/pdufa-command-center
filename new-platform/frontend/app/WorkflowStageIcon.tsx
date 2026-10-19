export type WorkflowStageId = "PIPELINE" | "GEM_JR" | "GEM" | "WT";

export default function WorkflowStageIcon({stage}: {stage:"PIPELINE"|"GEM_JR"|"GEM"|"WT"}) {
  if (stage==="PIPELINE") return <svg viewBox="0 0 48 48" fill="none" aria-hidden="true" focusable="false">
    <ellipse cx="24" cy="10" rx="16" ry="6" fill="currentColor" opacity=".88"/>
    <path d="M8 10v11c0 3.3 7.2 6 16 6s16-2.7 16-6V10" stroke="currentColor" strokeWidth="3"/>
    <path d="M8 21v11c0 3.3 7.2 6 16 6s16-2.7 16-6V21" stroke="currentColor" strokeWidth="3"/>
    <path d="M8 32v5c0 3.3 7.2 6 16 6s16-2.7 16-6v-5" stroke="currentColor" strokeWidth="3"/>
  </svg>;
  if (stage==="WT") return <svg viewBox="0 0 48 48" fill="none" aria-hidden="true" focusable="false">
    <path d="M24 4.5 30 17l13.8 1.9-10 9.8 2.5 13.9L24 36l-12.3 6.6 2.5-13.9-10-9.8L18 17 24 4.5Z" fill="currentColor" stroke="currentColor" strokeLinejoin="round" strokeWidth="1.8"/>
  </svg>;
  return <svg viewBox="0 0 48 48" fill="none" aria-hidden="true" focusable="false">
    <path d="M12 9h24l9 14-21 21L3 23 12 9Z" stroke="currentColor" strokeWidth="2.6" strokeLinejoin="round"/>
    <path d="M3 23h42M12 9l6 14 6 21 6-21 6-14M18 23h12" stroke="currentColor" strokeWidth="2.4" strokeLinejoin="round"/>
  </svg>;
}

