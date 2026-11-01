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
  const [rankPanelOpen,setRankPanelOpen]=useState(false);
  const [priorityPanelOpen,setPriorityPanelOpen]=useState(false);
  const [summaryPanelOpen,setSummaryPanelOpen]=useState(false);
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
  // Presentation-only navigation. Selection remains independent and saved.
  const [activePanel,setActivePanel]=useState<"trials"|"assessments"|null>(null);
  const [activeGroup,setActiveGroup]=useState<number|null>(null);
  const [activeAssessment,setActiveAssessment]=useState<number|null>(null);
  const [activePriority,setActivePriority]=useState<number|null>(null);
  const enterGroup=(id:number)=>{
    if(!value.groupIds.includes(id))setGroups(id,true);
    setActiveGroup(id);setActiveAssessment(null);
  };
  const enterAssessment=(id:number)=>{
    if(!value.groupAssessments.includes(id))setAssessment(id,true);
    setActiveAssessment(id);
  };
  const enterPriority=(id:number)=>{
    if(!value.priorities.includes(id))setPriority(id,true);
    setActivePriority(id);
  };
  const currentGroup=TOOLS_RANKING_GROUPS.find(g=>g.id===activeGroup);
  const currentAssessment=activeAssessment===null?null:byId.get(activeAssessment);
  const currentPriority=activePriority===null?null:byId.get(activePriority);
  return <section className={css.root} aria-label="Independent cascading ranking checklists">
    <div className={css.columns}>
      <button type="button" className={css.panelHeader} aria-expanded={activePanel==="trials"}
        aria-controls="tools-rank-trials-body" onClick={()=>setActivePanel(prev=>prev==="trials"?null:"trials")}>
        <span>Rank Trials By</span><span aria-hidden="true">{activePanel==="trials"?"⌃":"⌄"}</span>
      </button>
      <button type="button" className={css.panelHeader} aria-expanded={activePanel==="assessments"}
        aria-controls="tools-rank-priorities-body" onClick={()=>setActivePanel(prev=>prev==="assessments"?null:"assessments")}>
        <span>Rank 20 Assessments</span><span aria-hidden="true">{activePanel==="assessments"?"⌃":"⌄"}</span>
      </button>
    </div>
    {activePanel==="trials"&&<div id="tools-rank-trials-body" className={css.drillPanel}>
      {activeGroup===null?<div className={css.panelBody}>
        <p className={css.hint}>Step 1 of 3 · Choose a group to reveal its assessments.</p>
        <div className={css.list}>
          {TOOLS_RANKING_GROUPS.map(group=>{
            const checked=value.groupIds.includes(group.id);
            return <div key={group.id} className={css.optionRow}>
              <label className={css.choice}>
                <input type="checkbox" checked={checked} aria-label={"Select group #"+group.id}
                  onChange={e=>{
                    setGroups(group.id,e.target.checked);
                    if(e.target.checked){setActiveGroup(group.id);setActiveAssessment(null);}
                  }}/>
                <span><strong>#{group.id}</strong> — {group.title}</span>
              </label>
              <button type="button" className={css.drillButton} onClick={()=>enterGroup(group.id)}
                aria-label={"Open assessments for group #"+group.id}>›</button>
            </div>;
          })}
        </div>
      </div>:activeAssessment===null?<div className={css.panelBody}>
        <button type="button" className={css.back} onClick={()=>{setActiveGroup(null);setActiveAssessment(null);}}>‹ All groups</button>
        <h4 className={css.stepTitle}>#{activeGroup} — {currentGroup?.title}</h4>
        <p className={css.hint}>Step 2 of 3 · Choose an assessment to reveal its research fields.</p>
        <div className={css.list}>
          {currentGroup?.assessmentIds.map(id=>{
            const checked=value.groupAssessments.includes(id);
            return <div key={id} className={css.optionRow}>
              <label className={css.choice}>
                <input type="checkbox" checked={checked} aria-label={"Select assessment #"+id}
                  onChange={e=>{
                    setAssessment(id,e.target.checked);
                    if(e.target.checked)setActiveAssessment(id);
                  }}/>
                <span><strong>#{id}</strong> — {name(id)}</span>
              </label>
              <button type="button" className={css.drillButton} onClick={()=>enterAssessment(id)}
                aria-label={"Open fields for assessment #"+id}>›</button>
            </div>;
          })}
        </div>
      </div>:<div className={css.panelBody}>
        <button type="button" className={css.back} onClick={()=>setActiveAssessment(null)}>
          ‹ Assessments
        </button>
        <h4 className={css.stepTitle}>#{activeAssessment} — {currentAssessment?.name}</h4>
        <p className={css.hint}>Step 3 of 3 · Check the fields you want. You can select several.</p>
        <div className={css.list}>
          {currentAssessment?.fields.map(field=><label key={field.id} className={css.fieldChoice}>
            <input type="checkbox" checked={(value.groupCriteria[String(activeAssessment)]||[]).includes(field.id)}
              onChange={e=>setCriterion(activeAssessment,field.id,e.target.checked)}/>
            <span>{field.label}</span>
          </label>)}
        </div>
        <button type="button" className={css.done} onClick={()=>setActiveAssessment(null)}>Done · Choose another assessment</button>
      </div>}
      <div className={css.panelFooter}>
        <span>{value.groupAssessments.length} assessments · {Object.values(value.groupCriteria).reduce((n,fields)=>n+fields.length,0)} fields selected</span>
        <button type="button" className={css.clear} onClick={()=>{
          setValue(prev=>({...prev,groupIds:[],groupAssessments:[],groupCriteria:{}}));
          setActiveGroup(null);setActiveAssessment(null);
        }}>Clear this list</button>
      </div>
    </div>}
    {activePanel==="assessments"&&<div id="tools-rank-priorities-body" className={css.drillPanel}>
      {activePriority===null?<div className={css.panelBody}>
        <p className={css.hint}>Step 1 of 2 · Select any of the original 20 assessments to set its priority and fields.</p>
        <div className={css.list}>
          {assessmentList.map(id=>{
            const checked=prioritySet.has(id);
            return <div key={id} className={css.optionRow}>
              <label className={css.choice}>
                <input type="checkbox" checked={checked} aria-label={"Prioritize assessment #"+id}
                  onChange={e=>{
                    setPriority(id,e.target.checked);
                    if(e.target.checked)setActivePriority(id);
                  }}/>
                <span><strong>#{id}</strong> — {name(id)}
                  {checked&&<small className={css.priorityNumber}> · Priority {value.priorities.indexOf(id)+1}</small>}
                </span>
              </label>
              <button type="button" className={css.drillButton} onClick={()=>enterPriority(id)}
                aria-label={"Open priority and fields for assessment #"+id}>›</button>
            </div>;
          })}
        </div>
      </div>:<div className={css.panelBody}>
        <button type="button" className={css.back} onClick={()=>setActivePriority(null)}>‹ All 20 assessments</button>
        <h4 className={css.stepTitle}>#{activePriority} — {currentPriority?.name}</h4>
        <p className={css.hint}>Step 2 of 2 · Set its rank and choose research fields.</p>
        <label className={css.priorityControl}>Priority
          <select value={value.priorities.indexOf(activePriority)+1}
            onChange={e=>move(activePriority,Number(e.target.value))}
            aria-label={"Priority of original assessment #"+activePriority}>
            {value.priorities.map((_,i)=><option key={i} value={i+1}>#{i+1}</option>)}
          </select>
        </label>
        <div className={css.list}>
          {currentPriority?.fields.map(field=><label key={field.id} className={css.fieldChoice}>
            <input type="checkbox" checked={(value.priorityCriteria[String(activePriority)]||[]).includes(field.id)}
              onChange={e=>setPriorityCriterion(activePriority,field.id,e.target.checked)}/>
            <span>{field.label}</span>
          </label>)}
        </div>
        <button type="button" className={css.done} onClick={()=>setActivePriority(null)}>Done · Choose another assessment</button>
      </div>}
      <div className={css.panelFooter}>
        <span>{value.priorities.length} of 20 priorities selected</span>
        <button type="button" className={css.clear} onClick={()=>{
          setValue(prev=>({...prev,priorities:[],priorityCriteria:{}}));
          setActivePriority(null);
        }}>Clear this list</button>
      </div>
    </div>}
    <div className={css.results}>
      <button type="button" className={css.panelHeader} aria-expanded={summaryPanelOpen}
        aria-controls="tools-selected-ranking-body" onClick={()=>setSummaryPanelOpen(open=>!open)}>
        <span>Selected Ranking Criteria <span className={css.count}>({selectedCount})</span></span>
        <span aria-hidden="true">{summaryPanelOpen?"⌃":"⌄"}</span>
      </button>
      {summaryPanelOpen&&<div id="tools-selected-ranking-body" className={css.panelBody} aria-live="polite">
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
      </div>}
    </div>
  </section>;
}
