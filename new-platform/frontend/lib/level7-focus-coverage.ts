import snapshot from '../data/p3PostDataActive.json';

export type Level7CoverageRow = {
  nct: string;
  sourceVersions: number;
  distinctSources: number;
  statusCounts: Record<'verified'|'unverified'|'missing'|'inaccessible'|'conflicting',number>;
  readiness: 'NO_LEVEL7_EVIDENCE'|'SOURCE_COVERAGE_PRESENT'|'CONFLICT_REVIEW';
  assessmentStatus: 'NOT_SCORED';
  fdaPrediction: null;
};
export type Level7CoverageReport = {
  kind: 'FOCUS_LEVEL7_EVIDENCE_COVERAGE_NOT_FDA_PREDICTIONS';
  total: number;
  trialsWithEvidence: number;
  rosterAsOf: string;
  trials: Level7CoverageRow[];
};
const expected = new Set(snapshot.records.map(row=>row.nct));
export function validateLevel7CoverageReport(value: unknown): Level7CoverageReport {
  if (!value || typeof value !== 'object') throw Error('Level 7 coverage unavailable');
  const report=value as Partial<Level7CoverageReport>;
  if(report.kind!=='FOCUS_LEVEL7_EVIDENCE_COVERAGE_NOT_FDA_PREDICTIONS'||
    report.total!==32||report.rosterAsOf!==snapshot.asOf||
    !Array.isArray(report.trials)||report.trials.length!==32||
    expected.size!==32) throw Error('Level 7 report does not match current FOCUS roster');
  const seen=new Set<string>();
  for(const row of report.trials){
    if(!row||typeof row.nct!=='string'||!expected.has(row.nct)||seen.has(row.nct)||
      row.assessmentStatus!=='NOT_SCORED'||row.fdaPrediction!==null||
      !Number.isInteger(row.sourceVersions)||row.sourceVersions<0||
      !Number.isInteger(row.distinctSources)||row.distinctSources<0||
      row.distinctSources>row.sourceVersions||
      !['NO_LEVEL7_EVIDENCE','SOURCE_COVERAGE_PRESENT','CONFLICT_REVIEW'].includes(row.readiness)||
      !row.statusCounts||
      !(['verified','unverified','missing','inaccessible','conflicting'] as const)
        .every(status=>Number.isInteger(row.statusCounts[status])&&row.statusCounts[status]>=0)||
      Object.values(row.statusCounts).reduce((a,b)=>a+b,0)!==row.distinctSources
    ) throw Error('Invalid Level 7 evidence coverage row');
    seen.add(row.nct);
  }
  if(!Number.isInteger(report.trialsWithEvidence)||report.trialsWithEvidence!==
    report.trials.filter(row=>row.sourceVersions>0).length)
    throw Error('Level 7 evidence totals do not reconcile');
  return report as Level7CoverageReport;
}
