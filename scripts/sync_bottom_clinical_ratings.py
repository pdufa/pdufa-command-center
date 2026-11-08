"""Update ONLY existing exact-NCT rows through the canonical Sheets integration.

No tabs, columns, trials or validated probabilities are created. Retired /30
counts and original research/history notes stay untouched. Requires the same
GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON as the established roster integration.
The pure planner is also usable with authenticated connected Sheets read/write.
"""
from __future__ import annotations

# Permanent retirement: historical functions are importable for read-only audits only.
if __name__ == "__main__":
    raise SystemExit("RAAS_PERMANENTLY_RETIRED: this archived command cannot run or modify historical records.")

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXPORT=ROOT/'reports/bottom-only-20261107/bottom-score-sync.json'
SHEET_ID='1erY_z62b4mHhx5s_3HgJxXoJEslbLngMuQNfhcuSviU'
SHEET_NAME='FOCUS'
EXPECTED={1:'NCT ID',12:'Provisional Component Scores (Not Overall)',16:'RAAS Score Status',17:'Research Review As-Of',18:'Open RAAS Metric Details'}

def build_plan(rows,ratings):
    if not rows:raise ValueError('MISSING_CANONICAL_HEADERS')
    for column,title in EXPECTED.items():
        if len(rows[0])<=column or rows[0][column]!=title:raise ValueError('CANONICAL_HEADER_CHANGED:'+title)
    index={}
    for row_number,row in enumerate(rows[1:],start=4):
        if len(row)<2 or not row[1]:continue
        if row[1] in index:raise ValueError('DUPLICATE_EXACT_NCT:'+row[1])
        index[row[1]]=(row_number,row)
    if len({r['nctId'] for r in ratings})!=len(ratings):raise ValueError('DUPLICATE_RATING_NCT')
    changes=[]
    for rating in ratings:
        nct=rating['nctId']
        if nct not in index:continue
        row_number,row=index[nct]
        if row[0]!=rating['ticker']:raise ValueError('EXACT_NCT_TICKER_MISMATCH:'+nct)
        factors=rating['factors']
        if [f['id'] for f in factors]!=['post-1-'+str(i) for i in range(1,6)]:raise ValueError('INVALID_FIVE_FACTORS')
        if any(f['grade'] is not None and f['grade'] not in (0,25,50,75,100) for f in factors):raise ValueError('INVALID_RATING_ANCHOR')
        grades=[f['grade'] for f in factors if f['grade'] is not None]
        expected=round(sum(grades)/5,1) if len(grades)==5 else None
        if rating['clinicalFullScore']!=expected:raise ValueError('INVALID_COMBINED_SCORE:'+nct)
        component='CLINICAL_FIVE: '+'; '.join(f["id"]+':'+str(f['grade']) if f['grade'] is not None else f['id']+':'+f['state'] for f in factors)
        score='Not scored' if expected is None else str(expected)+'/100'
        values={12:component,16:f'CLINICAL_FIVE {len(grades)}/5; research {score}; NOT FDA PROBABILITY; archived /30 columns retained',17:rating['asOf'],18:'https://pdufa-new-dashboard.vercel.app/api/p3-post-data-research?nctId='+nct}
        for col,value in values.items():
            prior=row[col] if col<len(row) else ''
            if prior==value:continue
            changes.append({'nctId':nct,'row':row_number,'column':col,'previousValue':prior,'value':value,'note':rating['evidenceNote']})
    return changes

def batch_requests(changes,sheet_id,existing_notes=None):
    existing_notes=existing_notes or {}
    requests=[]
    for change in changes:
        row,col=change['row']-1,change['column']
        old_note=existing_notes.get((row,col),'')
        note=(old_note+'\n' if old_note else '')+'Prior value before clinical review: '+str(change['previousValue'])+'\n'+change['note']
        requests.append({'updateCells':{'range':{'sheetId':sheet_id,'startRowIndex':row,'endRowIndex':row+1,'startColumnIndex':col,'endColumnIndex':col+1},'rows':[{'values':[{'userEnteredValue':{'stringValue':change['value']},'note':note,'userEnteredFormat':{'wrapStrategy':'WRAP'}}]}],'fields':'userEnteredValue,note,userEnteredFormat.wrapStrategy'}})
    return requests

def persist_receipt(directory, report):
    """Keep latest receipt convenient without discarding earlier sync audits."""
    latest=directory/'sheets-sync-receipt.json'
    history_file=directory/'sheets-sync-history.json'
    history=json.loads(history_file.read_text()) if history_file.exists() else {'runs':[]}
    for receipt in ([json.loads(latest.read_text())] if latest.exists() else [])+[report]:
        if receipt not in history['runs']:history['runs'].append(receipt)
    history_file.write_text(json.dumps(history,indent=2)+'\n')
    latest.write_text(json.dumps(report,indent=2)+'\n')

def main():
    # Use established auth/identity/header validation and Sheets readback.
    from refresh_existing_p3_post_data import api_auth,sheets_values,validate_grid
    import requests
    auth=api_auth();before=sheets_values(auth,'A3:AB');validate_grid(before)
    ratings=json.loads(EXPORT.read_text())['records'];changes=build_plan(before,ratings)
    base=f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}'
    metadata=requests.get(base,headers=auth,params={'ranges':f"{SHEET_NAME}!M4:S204",'includeGridData':'true'},timeout=45);metadata.raise_for_status()
    sheet=next(s for s in metadata.json()['sheets'] if s['properties']['title']==SHEET_NAME)
    notes={}
    cells={}
    for grid in sheet.get('data',[]):
        for ri,row in enumerate(grid.get('rowData',[]),grid.get('startRow',0)):
            for ci,cell in enumerate(row.get('values',[]),grid.get('startColumn',0)):
                notes[(ri,ci)]=cell.get('note','');cells[(ri,ci)]=cell
    for change in changes:
        cell=cells.get((change['row']-1,change['column']),{})
        if cell.get('dataValidation') or 'formulaValue' in cell.get('userEnteredValue',{}) or cell.get('chipRuns'):
            raise RuntimeError('MANUAL_CELL_CONSTRAINT_REVIEW_REQUIRED:'+change['nctId'])
    if sheets_values(auth,'A3:AB')!=before:raise RuntimeError('CANONICAL_SHEET_CHANGED_NO_WRITE')
    if changes:
        response=requests.post(base+':batchUpdate',headers=auth,json={'requests':batch_requests(changes,sheet['properties']['sheetId'],notes)},timeout=60);response.raise_for_status()
    after=sheets_values(auth,'A3:AB');validate_grid(after)
    expected={ (c['row']-3,c['column']):c['value'] for c in changes }
    for ri,row in enumerate(before):
        for ci,prior in enumerate(row):
            actual=after[ri][ci] if ci<len(after[ri]) else ''
            if actual!=expected.get((ri,ci),prior):raise RuntimeError('SHEET_READBACK_MISMATCH')
    report={'writes':len(changes),'matchedNcts':sorted({c['nctId'] for c in changes}),'changes':changes,'verified':True}
    persist_receipt(ROOT/'reports/bottom-only-20261107',report)
    print(json.dumps({'writes':len(changes),'verified':True}))
if __name__=='__main__':main()
