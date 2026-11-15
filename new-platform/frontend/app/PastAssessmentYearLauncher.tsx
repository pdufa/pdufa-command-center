'use client';
import {useState} from 'react';
import AssessmentLauncher from './AssessmentLauncher';

/** Explicit PAST controls on ASSESSMENTS; never alias the FOCUS whole-list roster. */
export default function PastAssessmentYearLauncher(){
 const [year,setYear]=useState('2026');
 return <section aria-label="PAST cohort assessments" style={{margin:'16px 0',border:'1px solid #b9cebe',borderRadius:8,padding:12}}>
  <h2>PAST · Historical PDUFA assessments</h2>
  <p>Single trial, selected trials and whole-year preflight use exact NCT identities. Whole-year execution requires all events to have verified FDA application/review-cycle links and original pre-decision evidence.</p>
  <label>PAST year <select aria-label="PAST assessment year" value={year} onChange={e=>setYear(e.target.value)}>
   {Array.from({length:10},(_,i)=>2026-i).map(y=><option key={y} value={String(y)}>{y}</option>)}
  </select></label>
  <AssessmentLauncher source="HISTORICAL" historicalYear={year} lockSource/>
 </section>;
}
