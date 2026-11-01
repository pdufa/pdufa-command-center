"use client";
import {useEffect,useState} from "react";
import {parseBenefitFeed,type BenefitFeed} from "../lib/benefit-assessments";
import type {ToolsSpreadsheetRow} from "./ToolsResultsSpreadsheet";
import ToolsBenefitMatrix from "./ToolsBenefitMatrix";

/** Step 4 immediately follows the Step 3 filters and feeds the final Step 5
 * spreadsheet beneath it. All twenty original assessments retain the exact
 * same evidence rules; a missing fact is never treated as a failed trial. */
export default function ToolsAssessmentSection({rows,total,offset,loading,error}:{
  rows:ToolsSpreadsheetRow[];total:number;offset:number;loading:boolean;error:string;
}){
  const [feed,setFeed]=useState<BenefitFeed|null>(null);
  const [feedError,setFeedError]=useState("");
  useEffect(()=>{
    const controller=new AbortController();
    void fetch("/api/benefit-assessments",{cache:"no-store",signal:controller.signal})
      .then(async response=>{
        if(!response.ok)throw Error("BENEFIT_FEED_UNAVAILABLE");
        return parseBenefitFeed(await response.json());
      })
      .then(data=>{if(!controller.signal.aborted)setFeed(data);})
      .catch(()=>{if(!controller.signal.aborted)setFeedError("Assessment evidence unavailable. Missing facts remain Not assessed.");});
    return ()=>controller.abort();
  },[]);
  return <ToolsBenefitMatrix
    rows={rows} hasSelection total={total} offset={offset} loading={loading}
    error={error} benefitFeed={feed} benefitError={feedError}/>;
}
