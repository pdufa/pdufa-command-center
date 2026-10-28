/** Existing entry signal is technical timing evidence, not a validated FDA outcome model. */
export type EntrySignalSnapshot={programId?:unknown;ticker?:unknown;status?:unknown;green?:unknown;calculatedAt?:unknown;checks?:unknown};
export type EntryDecisionBridge={status:"NOT_READY";reasonCodes:string[];technicalEntryObserved:boolean};
/** Fail closed until an independent, source-verified SCIENCE/OUTCOME record and calibrated event model are available. */
export function bridgeEntrySignalToDecision(input:unknown,expectedProgramId:string,expectedTicker:string,now=new Date()):EntryDecisionBridge{
 const reasons=["SCIENTIFIC_OUTCOME_EVIDENCE_NOT_CONNECTED","CALIBRATED_EVENT_MODEL_NOT_CONNECTED","PRICE_SCENARIOS_NOT_CONNECTED"];
 if(!input||typeof input!=="object")return {status:"NOT_READY",reasonCodes:[...reasons,"ENTRY_SIGNAL_UNAVAILABLE"],technicalEntryObserved:false};
 const x=input as EntrySignalSnapshot;
 if(x.programId!==expectedProgramId||x.ticker!==expectedTicker||!/^PDUFA-\d{6,}$/.test(expectedProgramId)||!/^[A-Z][A-Z0-9.-]{0,9}$/.test(expectedTicker))return {status:"NOT_READY",reasonCodes:[...reasons,"IDENTITY_MISMATCH"],technicalEntryObserved:false};
 const stamp=typeof x.calculatedAt==="string"?Date.parse(x.calculatedAt):NaN;
 const age=now.getTime()-stamp;
 if(!Number.isFinite(age)||age<0||age>=60000)return {status:"NOT_READY",reasonCodes:[...reasons,"ENTRY_SIGNAL_STALE"],technicalEntryObserved:false};
 const technicalEntryObserved=x.status==="BUY"&&x.green===true;
 return {status:"NOT_READY",reasonCodes:reasons,technicalEntryObserved};
}
