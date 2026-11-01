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

/**
 * An independent ranking-criteria planner. No changes to selected POOL stage/FDA
 * filters, pagination, trial eligibility, evidence source or claimed clinical rank.
 * The two checklists are deliberately independent; combined summary is read-only.
 */
export default function ToolsRankingChecklists(){
  const [value,setValue]=useState<RankingChecklistSelection>(BLANK);
  const [hydrated,setHydrated]=useState(false);
  useEffect(()=>{
    try {
      const stored=window.localStorage.getItem(STORAGE_KEY);
      if(stored)setValue(normalizeRankingSelection(JSON.parse(stored) as unknown));
    }catch{/* Storage can be disabled or contain older data; use an empty selection. */}
    setHydrated(true);
  },[]);
  useEffect(()=>{
    if(!hydrated)return;
    try{window.localStorage.setItem(STORAGE_KEY,JSON.stringify(value));}catch{/* Saving is optional. */}
  },[hydrated,value]);
  const selectedCount=value.groupIds.length+value.groupAssessments.length+
    Object.values(value.groupCriteria).reduce((n,keys)=>n+keys.length,0)+value.priorities.length+
    Object.values(value.priorityCriteria).reduce((n,keys)=>n+keys.length,0);
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
    const old=prev.groupCriteria[String(id)]||[];
    return normalizeRankingSelection({...prev,groupCriteria:{
      ...prev.groupCriteria,[String(id)]:checked?[...old,field]:old.filter(x=>x!==field)
    }});
  });
  const setPriority=(id:number,checked:boolean)=>setValue(prev=>normalizeRankingSelection({
    ...prev,priorities:checked?[...prev.priorities,id]:prev.priorities.filter(x=>x!==id)
  }));
  const setPriorityCriterion=(id:number,field:string,checked:boolean)=>setValue(prev=>{
    const old=prev.priorityCriteria[String(id)]||[];
    return normalizeRankingSelection({...prev,priorityCriteria:{
      ...prev.priorityCriteria,[String(id)]:checked?[...old,field]:old.filter(x=>x!==field)
    }});
  });
  const move=(id:number,rank:number)=>setValue(prev=>({
    ...prev,priorities:movePriority(prev.priorities,id,rank)
  }));
  return <section className={css.root} aria-label="Independent cascading ranking checklists">
    <div className={css.columns}>
      <details className={css.panel}>
        <summary className={css.panelHeader}>Rank Trials By</summary>
        <div className={css.panelBody}>
          <p className={css.hint}>Check a group, then its assessments, then the exact research fields.</p>
          <div className={css.list}>
            {TOOLS_RANKING_GROUPS.map(group=>{
              const checked=value.groupIds.includes(group.id);
              return <div key={group.id} className={css.group}>
                <label className={css.choice}>
                  <input type="checkbox" checked={checked} onChange={e=>setGroups(group.id,e.target.checked)}/>
                  <span><strong>#{group.id}</strong> — {group.title}</span>
                </label>
                {checked&&<div className={css.children}>
                  {group.assessmentIds.map(id=>{
                    const assessment=byId.get(id)!;
                    const active=value.groupAssessments.includes(id);
                    const selectedFields=value.groupCriteria[String(id)]||[];
                    return <div key={id} className={css.assessment}>
                      <label className={css.choice}>
                        <input type="checkbox" checked={active} onChange={e=>setAssessment(id,e.target.checked)}/>
                        <span><strong>#{id}</strong> — {assessment.name}</span>
                      </label>
                      {active&&<div className={css.fields}>
                        {assessment.fields.map(field=><label key={field.id} className={css.choice}>
                          <input type="checkbox" checked={selectedFields.includes(field.id)}
                            onChange={e=>setCriterion(id,field.id,e.target.checked)}/>
                          <span>{field.label}</span>
                        </label>)}
                      </div>}
                    </div>;
                  })}
                </div>}
              </div>;
            })}
          </div>
          <button type="button" className={css.clear} onClick={()=>setValue(prev=>({
            ...prev,groupIds:[],groupAssessments:[],groupCriteria:{}
          }))}>Clear trial ranking selections</button>
        </div>
      </details>
      <details className={css.panel}>
        <summary className={css.panelHeader}>Rank 20 Assessments</summary>
        <div className={css.panelBody}>
          <p className={css.hint}>Check an assessment, set its priority, then select the research fields to emphasize.</p>
          <div className={css.list}>
            {assessmentList.map(id=>{
              const rank=value.priorities.indexOf(id)+1;
              return <div key={id} className={css.priorityItem}>
                <label className={css.choice}>
                  <input type="checkbox" checked={prioritySet.has(id)}
                    onChange={e=>setPriority(id,e.target.checked)}/>
                  <span><strong>#{id}</strong> — {name(id)}</span>
                </label>
                {rank>0&&<>
                  <label className={css.priorityControl}>
                    Priority
                    <select value={rank} onChange={e=>move(id,Number(e.target.value))}
                      aria-label={"Priority of original assessment #"+id}>
                      {value.priorities.map((_,i)=><option key={i} value={i+1}>#{i+1}</option>)}
                    </select>
                  </label>
                  <details className={css.priorityFields}>
                    <summary>Choose research fields ({(value.priorityCriteria[String(id)]||[]).length})</summary>
                    <div className={css.fields}>
                      {byId.get(id)!.fields.map(field=><label key={field.id} className={css.choice}>
                        <input type="checkbox" checked={(value.priorityCriteria[String(id)]||[]).includes(field.id)}
                          onChange={e=>setPriorityCriterion(id,field.id,e.target.checked)}/>
                        <span>{field.label}</span>
                      </label>)}
                    </div>
                  </details>
                </>}
              </div>;
            })}
          </div>
          <button type="button" className={css.clear} onClick={()=>setValue(prev=>({...prev,priorities:[],priorityCriteria:{}}))}>Clear assessment priorities</button>
        </div>
      </details>
    </div>
    <details className={css.results}>
      <summary className={css.panelHeader}>
        Selected Ranking Criteria <span className={css.count}>({selectedCount})</span>
      </summary>
      <div className={css.panelBody} aria-live="polite">
        {selectedCount===0?<p className={css.hint}>No ranking criteria selected. Check items in either list or both.</p>:<>
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
          <p className={css.hint}>Selections are saved on this device. These are research priorities, not calculated trial superiority or FDA approval predictions. The existing MATCHING TRIAL RECORDS remain unchanged.</p>
        </>}
      </div>
    </details>
  </section>;
}
