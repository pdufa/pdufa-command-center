'use client';
import {useState} from 'react';
import AssessmentLauncher from './AssessmentLauncher';

/** Explicit PAST controls on ASSESSMENTS; never alias the FOCUS whole-list roster. */
export default function PastAssessmentYearLauncher(){
 const [year,setYear]=useState('2026');
 return <section aria-label="PAST cohort assessments" style={{margin:'16px 0',border:'1px solid #b9cebe',borderRadius:8,padding:12}}>
  <h2>PAST · Historical PDUFA assessments</h2>
  <p>Single and selected trials use exact NCT identity. Whole-year PAST can audit every imported historical event and run assessments only for source-verified trials with original pre-decision evidence; unresolved events remain Not Assessed instead of blocking the audit.</p>
  <label>PAST year <select aria-label="PAST assessment year" value={year} onChange={e=>setYear(e.target.value)}>
   {Array.from({length:10},(_,i)=>2026-i).map(y=><option key={y} value={String(y)}>{y}</option>)}
  </select></label>
  <AssessmentLauncher source="HISTORICAL" historicalYear={year} lockSource/>
 </section>;
}
