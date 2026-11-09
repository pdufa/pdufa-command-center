"""Read-only GitHub lookup for each workstream's latest completed history.

Never guesses a previous chain after an API failure. No token or download URL
is logged; the official download-artifact action performs the actual transfer.
"""
import argparse,json,os
from urllib.parse import quote
from urllib.request import Request,urlopen

WORKFLOWS={'A':('main-r47-parallel-focus-historical-research.yml','main-focus-research-history-'),
           'B':('main-r47-historical-source-track-b.yml','main-historical-research-history-')}

def select(track,branch,get_json):
    workflow,prefix=WORKFLOWS[track]
    for page in range(1,6):
        runs=get_json('actions/workflows/'+workflow+'/runs?branch='+quote(branch,safe='')+'&status=completed&per_page=20&page='+str(page))['workflow_runs']
        for run in runs:
            if run.get('head_branch')!=branch or run.get('status')!='completed':raise ValueError('INVALID_PRIOR_RESEARCH_RUN')
            wanted=prefix+str(run['id'])
            artifacts=get_json('actions/runs/'+str(run['id'])+'/artifacts?per_page=100')['artifacts']
            if any(a.get('name')==wanted and a.get('expired') is True for a in artifacts):
                raise ValueError('PRIOR_HISTORY_EXPIRED_REQUIRES_ARCHIVE_RESTORE')
            matches=[a for a in artifacts if a.get('name')==wanted and a.get('expired') is False]
            if len(matches)>1:raise ValueError('AMBIGUOUS_PRIOR_RESEARCH_HISTORY')
            if matches:return {'run_id':str(run['id']),'artifact_name':wanted}
        if len(runs)<20:return {'run_id':'','artifact_name':''}
    raise ValueError('HISTORY_LOOKUP_PAGE_LIMIT_NO_RESET_ALLOWED')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--track',choices=['A','B'],required=True);a=p.parse_args()
    if os.environ.get('GITHUB_REPOSITORY')!='pdufa/pdufa-command-center':raise ValueError('FIXED_RESEARCH_REPOSITORY_REQUIRED')
    branch=os.environ['GITHUB_REF_NAME'];token=os.environ['GH_TOKEN']
    def get_json(path):
        req=Request('https://api.github.com/repos/pdufa/pdufa-command-center/'+path,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json'})
        with urlopen(req,timeout=30) as response:
            raw=response.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError('HISTORY_LOOKUP_TOO_LARGE')
        return json.loads(raw)
    result=select(a.track,branch,get_json)
    with open(os.environ['GITHUB_OUTPUT'],'a') as f:
        for k,v in result.items():f.write(k+'='+v+'\n')
    print('Previous track '+a.track+' history: '+('FOUND' if result['run_id'] else 'NO_PRIOR_HISTORY_ARTIFACT; earlier source artifacts remain preserved'))
if __name__=='__main__':main()
