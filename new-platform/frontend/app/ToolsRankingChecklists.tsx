"use client";
import {useEffect,useMemo,useState} from "react";
import {BENEFIT_GROUPS} from "../lib/benefit-assessments";
import {
  TOOLS_RANKING_GROUPS,movePriority,normalizeRankingSelection,
  type RankingChecklistSelection
} from "../lib/tools-ranking-config";
import css from "./ToolsRankingChecklists.module.css";

const STORAGE_KEY="pdufa-tools-ranking-checklists-v1";
const BLANK:RankingChecklistSelection={groupIds:[],groupAssessments:[],groupCriteria:{},priorities:[],priorityCriteria:{}};
const byId=new Map(BENEFIT_GROUPS.map(g=>[g.number,g]));
const name=(id:number)=>byId.get(id)?.name||"Unknown assessment";
const fieldName=(id:number,key:string)=>byId.get(id)?.fields.find(f=>f.id===key)?.label||key;
const letter=(index:number)=>String.fromCharCode(97+index);
/** Each selectable row gets a circled branch label: 1a/6 = first option at level 1 out of six. */
function NumberCircle({text}:{text:string}){
  return <span className={css.numberCircle} aria-hidden="true">{text}</span>;
}
function StepHeading({number,children}:{number:string;children:React.ReactNode}){
  return <div className={css.stepHeading}>
    <NumberCircle text={number}/><strong>{children}</strong>
  </div>;
}

/**
 * Mobile-first progressive disclosure. The left and right selectors are independent:
 * selecting an option opens its next step immediately, hiding every unselected
 * option's descendants. Neither selector changes POOL/FDA filters or trial scores.
 */
export default function ToolsRankingChecklists(){
  const [value,setValue]=useState<RankingChecklistSelection>(BLANK);
  const [rankPanelOpen,setRankPanelOpen]=useState(false);
  const [priorityPanelOpen,setPriorityPanelOpen]=useState(false);
  const [summaryPanelOpen,setSummaryPanelOpen]=useState(false);
  const [hydrated,setHydrated]=useState(false);
  useEffect(()=>{
    try{
      const stored=window.localStorage.getItem(STORAGE_KEY);
      if(stored)setValue(normalizeRankingSelection(JSON.parse(stored) as unknown));
    }catch{/* Storage is optional; invalid or old drafts fall back to empty. */}
    setHydrated(true);
  },[]);
  useEffect(()=>{
    if(!hydrated)return;
    try{window.localStorage.setItem(STORAGE_KEY,JSON.stringify(value));}catch{/* Saving is optional. */}
  },[hydrated,value]);

  const selectedCount=value.groupIds.length+value.groupAssessments.length+
    Object.values(value.groupCriteria).reduce((n,fields)=>n+fields.length,0)+value.priorities.length+
    Object.values(value.priorityCriteria).reduce((n,fields)=>n+fields.length,0);
  const prioritySet=useMemo(()=>new Set(value.priorities),[value.priorities]);
  const assessmentList=useMemo(()=>
    [...value.priorities,...BENEFIT_GROUPS.filter(g=>!prioritySet.has(g.number)).map(g=>g.number)],
    [value.priorities,prioritySet]);

  const setGroups=(id:number,checked:boolean)=>setValue(prev=>normalizeRankingSelection({
    ...prev,groupIds:checked?[...prev.groupIds,id]:prev.groupIds.filter(x=>x!==id)
  }));
  const setAssessment=(id:number,checked:boolean)=>setValue(prev=>normalizeRankingSelection({
    ...prev,groupAssessments:checked?[...prev.groupAssessments,id]:prev.groupAssessments.filter(x=>x!==id)
  }));
  const setCriterion=(id:number,field:string,checked:boolean)=>setValue(prev=>{
    const existing=prev.groupCriteria[String(id)]||[];
    return normalizeRankingSelection({...prev,groupCriteria:{
      ...prev.groupCriteria,[String(id)]:checked?[...existing,field]:existing.filter(x=>x!==field)
    }});
  });
  const setPriority=(id:number,checked:boolean)=>setValue(prev=>normalizeRankingSelection({
    ...prev,priorities:checked?[...prev.priorities,id]:prev.priorities.filter(x=>x!==id)
  }));
  const setPriorityCriterion=(id:number,field:string,checked:boolean)=>setValue(prev=>{
    const existing=prev.priorityCriteria[String(id)]||[];
    return normalizeRankingSelection({...prev,priorityCriteria:{
      ...prev.priorityCriteria,[String(id)]:checked?[...existing,field]:existing.filter(x=>x!==field)
    }});
  });
  const move=(id:number,rank:number)=>setValue(prev=>({
    ...prev,priorities:movePriority(prev.priorities,id,rank)
  }));

  return <section className={css.root} aria-label="Guided cascading ranking checklists">
    <div className={css.columns}>
      <div className={css.panel}>
        <button type="button" className={css.panelHeader} aria-expanded={rankPanelOpen}
          aria-controls="tools-rank-trials-body" onClick={()=>{
            setRankPanelOpen(open=>!open);
            setPriorityPanelOpen(false);
          }}>
          <span>Rank Trials By</span><span aria-hidden="true">{rankPanelOpen?"⌃":"⌄"}</span>
        </button>
      </div>
      <div className={css.panel}>
        <button type="button" className={css.panelHeader} aria-expanded={priorityPanelOpen}
          aria-controls="tools-rank-priorities-body" onClick={()=>{
            setPriorityPanelOpen(open=>!open);
            setRankPanelOpen(false);
          }}>
          <span>Rank 20 Assessments</span><span aria-hidden="true">{priorityPanelOpen?"⌃":"⌄"}</span>
        </button>
      </div>
    </div>
    {rankPanelOpen&&<div id="tools-rank-trials-body" className={css.cascadeBody}>
      <p className={css.hint}>Choose a group. Its assessments appear immediately; checking an assessment opens its research fields.</p>
      <StepHeading number="1">Choose group(s)</StepHeading>
      <div className={css.list}>
        {TOOLS_RANKING_GROUPS.map((group,groupIndex)=>{
          const active=value.groupIds.includes(group.id);
          return <div key={group.id} className={active?css.activeItem:css.group}>
            <label className={css.choice}>
              <input type="checkbox" checked={active} onChange={event=>setGroups(group.id,event.target.checked)}/>
              <NumberCircle text={"1"+letter(groupIndex)+"/"+TOOLS_RANKING_GROUPS.length}/>
              <span>Group #{group.id} — {group.title}</span>
            </label>
            {active&&<div className={css.children} data-cascade-for={"group-"+group.id}>
              <StepHeading number="2">Choose assessment(s) in this group</StepHeading>
              {group.assessmentIds.map((id,index)=>{
                const assessment=byId.get(id)!;
                const chosen=value.groupAssessments.includes(id);
                const selectedFields=value.groupCriteria[String(id)]||[];
                return <div key={id} className={chosen?css.activeItem:css.assessment}>
                  <label className={css.choice}>
                    <input type="checkbox" checked={chosen} onChange={event=>setAssessment(id,event.target.checked)}/>
                    <NumberCircle text={"2"+letter(index)+"/"+group.assessmentIds.length}/>
                    <span>#{id} — {assessment.name}</span>
                  </label>
                  {chosen&&<div className={css.children} data-cascade-for={"assessment-"+id}>
                    <StepHeading number="3">Choose research criterion/criteria</StepHeading>
                    <div className={css.fields}>
                      {assessment.fields.map((field,fieldIndex)=><label key={field.id} className={css.choice}>
                        <input type="checkbox" checked={selectedFields.includes(field.id)}
                          onChange={event=>setCriterion(id,field.id,event.target.checked)}/>
                        <NumberCircle text={"3"+letter(fieldIndex)+"/"+assessment.fields.length}/>
                        <span>{field.label}</span>
                      </label>)}
                    </div>
                  </div>}
                </div>;
              })}
            </div>}
          </div>;
        })}
      </div>
      <button type="button" className={css.clear} onClick={()=>setValue(prev=>({
        ...prev,groupIds:[],groupAssessments:[],groupCriteria:{}
      }))}>Clear Rank Trials By</button>
    </div>}
    {priorityPanelOpen&&<div id="tools-rank-priorities-body" className={css.cascadeBody}>
      <p className={css.hint}>Choose any original assessment. It immediately reveals two next steps: priority and optional research fields.</p>
      <StepHeading number="1">Choose original assessment(s) #1–#20</StepHeading>
      <div className={css.list}>
        {assessmentList.map((id,index)=>{
          const rank=value.priorities.indexOf(id)+1;
          const fields=byId.get(id)!.fields;
          const selectedFields=value.priorityCriteria[String(id)]||[];
          return <div key={id} className={rank>0?css.activeItem:css.priorityItem}>
            <label className={css.choice}>
              <input type="checkbox" checked={prioritySet.has(id)}
                onChange={event=>setPriority(id,event.target.checked)}/>
              <NumberCircle text={"1"+letter(index)+"/20"}/>
              <span>Original #{id} — {name(id)}</span>
            </label>
            {rank>0&&<div className={css.children} data-cascade-for={"priority-"+id}>
              <div className={css.stepRow}>
                <NumberCircle text="2a/2"/>
                <label className={css.priorityControl}>
                  <span>Priority rank</span>
                  <select value={rank} onChange={event=>move(id,Number(event.target.value))}
                    aria-label={"Priority of original assessment #"+id}>
                    {value.priorities.map((_,i)=><option key={i} value={i+1}>#{i+1}</option>)}
                  </select>
                </label>
              </div>
              <StepHeading number="2b/2">Choose research field(s) (optional)</StepHeading>
              <div className={css.fields}>
                {fields.map((field,fieldIndex)=><label key={field.id} className={css.choice}>
                  <input type="checkbox" checked={selectedFields.includes(field.id)}
                    onChange={event=>setPriorityCriterion(id,field.id,event.target.checked)}/>
                  <NumberCircle text={"3"+letter(fieldIndex)+"/"+fields.length}/>
                  <span>{field.label}</span>
                </label>)}
              </div>
            </div>}
          </div>;
        })}
      </div>
      <button type="button" className={css.clear} onClick={()=>setValue(prev=>({
        ...prev,priorities:[],priorityCriteria:{}
      }))}>Clear Rank 20 Assessments</button>
    </div>}
    <div className={css.results}>
      <button type="button" className={css.panelHeader} aria-expanded={summaryPanelOpen}
        aria-controls="tools-selected-ranking-body" onClick={()=>setSummaryPanelOpen(open=>!open)}>
        <span>Selected Ranking Criteria <span className={css.count}>({selectedCount})</span></span>
        <span aria-hidden="true">{summaryPanelOpen?"⌃":"⌄"}</span>
      </button>
      {summaryPanelOpen&&<div id="tools-selected-ranking-body" className={css.panelBody} aria-live="polite">
        {selectedCount===0?<p className={css.hint}>No ranking criteria selected. Select from either list or both.</p>:<>
          {value.groupIds.length>0&&<div className={css.summarySection}>
            <strong>Rank Trials By</strong>
            {TOOLS_RANKING_GROUPS.filter(group=>value.groupIds.includes(group.id)).map(group=><div key={group.id}>
              <span>Group #{group.id} — {group.title}</span>
              {group.assessmentIds.filter(id=>value.groupAssessments.includes(id)).map(id=><div key={id} className={css.summaryIndent}>
                <span>Assessment #{id} — {name(id)}</span>
                {(value.groupCriteria[String(id)]||[]).map(field=><div className={css.summaryIndent} key={field}>
                  ✓ {fieldName(id,field)}
                </div>)}
              </div>)}
            </div>)}
          </div>}
          {value.priorities.length>0&&<div className={css.summarySection}>
            <strong>Rank 20 Assessments</strong>
            {value.priorities.map((id,i)=><div key={id}>
              <span>Priority #{i+1}:</span> Original #{id} — {name(id)}
              {(value.priorityCriteria[String(id)]||[]).map(field=><div className={css.summaryIndent} key={field}>
                ✓ {fieldName(id,field)}
              </div>)}
            </div>)}
          </div>}
          <p className={css.hint}>Selections are saved on this device. They set research priorities, not calculated trial superiority or FDA predictions. Matching trial records and existing filters are unchanged.</p>
        </>}
      </div>}
    </div>
  </section>;
}
