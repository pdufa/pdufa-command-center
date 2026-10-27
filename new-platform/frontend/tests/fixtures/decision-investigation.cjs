// Synthetic software-contract fixture only. This is not scientific evidence.
exports.investigation=(identity,asOf,indication='B')=>({identity:{...identity},asOf,drug:'Synthetic contract drug',indication,
 companyCik:'0000000001',fdaApplication:'NDA999999',
 layers:Array.from({length:8},(_,i)=>({id:'subject-'+i,label:'Synthetic subject '+i})),
 levels:Array.from({length:20},(_,i)=>({id:'level-'+i,label:'Synthetic investigation '+i,layerId:'subject-'+(i%8),
  assessments:Array.from({length:2},(_,j)=>({id:'assessment-'+i+'-'+j,status:'COMPLETE',reviewer:'Synthetic reviewer',
   criticalEvaluation:'Synthetic review argument, used only to exercise the software boundary.',
   uncertainty:'This fixture is not an observed trial or an accuracy estimate.',unresolvedCriticalFindings:0,
   sources:[{url:'https://example.org/original-source',publishedAt:'2026-10-24T10:00:00Z',observedAt:'2026-10-24T11:00:00Z',independentlyReviewed:true}]}))}))});
