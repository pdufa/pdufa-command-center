export const PEAK_KEY="APPLICATION|COGT|BEZUCLASTINIB_GIST_20261130";
type Question={id:string;question:string;layerName:string;researchObservation:string;uncertainties:string[];sourceIds:string[];missingDocumentIds:string[];independentlyReviewed:false;reviewStatus:string};
type Source={id:string;url:string;publishedAt:string|null;observedOn:string;accessStatus:string;originalBytesRetained:false;originalDocumentSha256:null};
export type PeakResearchView={schemaVersion:"peak-research-view-v1";exactKey:string;asOf:string;tradeAuthorized:false;sheetWritesEnabled:false;productionSchedulingEnabled:false;
 science40:{totalAssessments:40;sourceLeadsDiscovered:number;independentlyReviewedAssessments:number;readinessGrade:string;reviewedDepthLevels:number[]};
 outcome:{decisionReadinessGrade:"ABSTAIN";approvalProbability:null;confidence:null;modelValidated:false;tradeAuthorized:false;blockers:string[]};
 main?:{exactKey:string;asOf:string;prediction:"INSUFFICIENT_EVIDENCE";decisionReadinessGrade:"ABSTAIN";modelValidated:false;modelVersion:null;predictionTimestamp:null};
 researchRegister:null|{nctId:string;indexedOn:string;summary:{questionRecords:40;questionsWithSourceObservations:number;missingRequiredDocumentFamilies:number;historicalSourceContexts:number;independentlyAdjudicatedHistoricalCycles:0};questions:Question[];sources:Source[];requiredDocuments:{id:string;name:string;status:string}[];historicalContexts:{id:string;drug:string;applicationId:string;reviewCycle:null;actionClaim:string;differences:string[];sourceIds:string[];independentlyAdjudicated:false;modelEligible:false}[];timeline:{date:string;event:string;basis:string;sourceId:string}[];criticalConcerns:string[];evidenceDiscrepancies:{id:string;status:string;observation:string;sourceIds:string[]}[]};};
const object=(v:unknown):v is Record<string,any>=>!!v&&typeof v==="object"&&!Array.isArray(v);
const text=(v:unknown):v is string=>typeof v==="string"&&v.length>0&&v.length<=5000;
const strings=(v:unknown):v is string[]=>Array.isArray(v)&&v.length<=50&&v.every(text);
const day=(v:unknown):v is string=>typeof v==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v))&&new Date(v).toISOString().slice(0,10)===v;
const count=(v:unknown):v is number=>typeof v==="number"&&Number.isInteger(v)&&v>=0&&v<=100;
export function safeResearchUrl(v:unknown):v is string{
 if(!text(v)||/[\s\u0000-\u001f]/.test(v))return false;
 try{const u=new URL(v);return u.protocol==="https:"&&!!u.hostname&&!u.username&&!u.password&&!u.hash;}catch{return false;}
}
export function validatePeakResearchView(v:unknown):PeakResearchView{
 const fail=():never=>{throw new Error("PEAK research identity or evidence boundary was not confirmed");};
 if(!object(v)||JSON.stringify(v).length>250000||v.schemaVersion!=="peak-research-view-v1"||v.exactKey!==PEAK_KEY||!day(v.asOf)||v.tradeAuthorized!==false||v.sheetWritesEnabled!==false||v.productionSchedulingEnabled!==false)return fail();
 const s=v.science40,o=v.outcome;
 if(!object(s)||s.exactKey!==PEAK_KEY||s.asOf!==v.asOf||s.totalAssessments!==40||!count(s.sourceLeadsDiscovered)||!count(s.independentlyReviewedAssessments)||s.independentlyReviewedAssessments>40||s.tradeAuthorized!==false||s.approvalProbability!==null||!text(s.readinessGrade)||!object(o)||o.exactKey!==PEAK_KEY||o.asOf!==v.asOf||o.decisionReadinessGrade!=="ABSTAIN"||o.decision!=="ABSTAIN"||o.approvalProbability!==null||o.nonapprovalProbability!==null||o.confidence!==null||o.modelValidated!==false||o.tradeAuthorized!==false||!strings(o.blockers))return fail();
 // Older deployed research reads omit MAIN. When present, it must preserve
 // exact identity/cutoff and cannot smuggle a prediction or model promotion.
 const m=v.main;
 if(m!==undefined&&(!object(m)||m.schemaVersion!=="phase3-main-readiness-v1"||m.exactKey!==v.exactKey||m.asOf!==v.asOf||m.researchReadinessGrade!==s.readinessGrade||m.decisionReadinessGrade!=="ABSTAIN"||m.prediction!=="INSUFFICIENT_EVIDENCE"||m.modelValidated!==false||m.modelVersion!==null||m.predictionTimestamp!==null||m.approvalProbability!==null||m.confidence!==null||m.tradeAuthorized!==false||JSON.stringify(m.researchRegister)!==JSON.stringify(v.researchRegister)))return fail();
 if(o.predictionClasses!==undefined&&(JSON.stringify(o.predictionClasses)!==JSON.stringify(["PASS","CRL","EXTENSION"])||!object(o.probabilities)||Object.keys(o.probabilities).sort().join(",")!=="CRL,EXTENSION,PASS"||Object.values(o.probabilities).some(p=>p!==null)||o.extensionIsNonapproval!==false||o.modelVersion!==null))return fail();
 // This route submits no scientific observations or reviewer claims. It may
 // display research leads, but cannot promote this empty submission to signoff.
 if(s.independentlyReviewedAssessments!==0||s.readinessGrade!=="RELUCTANT"||!Array.isArray(s.reviewedDepthLevels)||s.reviewedDepthLevels.length||!Array.isArray(s.records)||s.records.length!==40||s.records.some((q:any,i:number)=>!object(q)||q.id!==`S${String(i+1).padStart(2,"0")}`||q.independentlyReviewed!==false||q.status!=="NOT_SUBMITTED")||s.sourceLeadsDiscovered!==s.records.filter((q:any)=>q.sourceLead!==null).length)return fail();
 const r=v.researchRegister;
 if(r===null)return v as PeakResearchView;
 if(!object(r)||r.exactKey!==PEAK_KEY||r.nctId!=="NCT05208047"||!day(r.indexedOn)||r.indexedOn>v.asOf||r.modelValidated!==false||r.approvalProbability!==null||r.tradeAuthorized!==false||!Array.isArray(r.questions)||r.questions.length!==40||!Array.isArray(r.sources)||r.sources.length>30||!Array.isArray(r.requiredDocuments)||r.requiredDocuments.length>30||!Array.isArray(r.historicalContexts)||r.historicalContexts.length>20||!Array.isArray(r.timeline)||r.timeline.length>30||!strings(r.criticalConcerns))return fail();
 const ids=new Set<string>(),docs=new Set<string>();
 for(const x of r.sources){if(!object(x)||!text(x.id)||ids.has(x.id)||!safeResearchUrl(x.url)||!day(x.observedOn)||x.observedOn>v.asOf||x.publishedAt!==null&&(!day(x.publishedAt)||x.publishedAt>x.observedOn)||x.originalBytesRetained!==false||x.originalDocumentSha256!==null||x.independentlyReviewed!==false)return fail();ids.add(x.id);}
 for(const d of r.requiredDocuments){if(!object(d)||!text(d.id)||docs.has(d.id)||!text(d.name)||!["MISSING","UNVERIFIED"].includes(d.status))return fail();docs.add(d.id);}
 for(const [i,q] of r.questions.entries())if(!object(q)||q.id!==`S${String(i+1).padStart(2,"0")}`||q.exactKey!==PEAK_KEY||q.nctId!==r.nctId||q.independentReviewRequired!==true||!text(q.question)||!text(q.layerName)||!text(q.researchObservation)||!strings(q.uncertainties)||!strings(q.sourceIds)||q.sourceIds.some((id:string)=>!ids.has(id))||!strings(q.missingDocumentIds)||q.missingDocumentIds.some((id:string)=>!docs.has(id))||q.independentlyReviewed!==false||!["MISSING","UNADJUDICATED_RESEARCH"].includes(q.reviewStatus)||!Array.isArray(q.reviewedDepthLevels)||q.reviewedDepthLevels.length)return fail();
 for(const h of r.historicalContexts)if(!object(h)||!text(h.id)||!text(h.drug)||!text(h.applicationId)||h.reviewCycle!==null||h.modelEligible!==false||h.independentlyAdjudicated!==false||!text(h.actionClaim)||!strings(h.differences)||!strings(h.sourceIds)||h.sourceIds.some((id:string)=>!ids.has(id)))return fail();
 for(const t of r.timeline)if(!object(t)||!day(t.date)||!text(t.event)||!text(t.basis)||!ids.has(t.sourceId))return fail();
 if(!Array.isArray(r.evidenceDiscrepancies)||r.evidenceDiscrepancies.length>20)return fail();
 for(const d of r.evidenceDiscrepancies)if(!object(d)||!text(d.id)||!text(d.status)||!text(d.observation)||!strings(d.sourceIds)||d.sourceIds.some((id:string)=>!ids.has(id)))return fail();
 const n=r.summary;
 if(!object(n)||n.questionRecords!==40||n.questionsWithSourceObservations!==r.questions.filter((q:Question)=>q.sourceIds.length).length||n.missingRequiredDocumentFamilies!==r.requiredDocuments.length||n.historicalSourceContexts!==r.historicalContexts.length||n.independentlyAdjudicatedHistoricalCycles!==0)return fail();
 return v as PeakResearchView;
}
