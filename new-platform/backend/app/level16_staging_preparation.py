"""Preparation-only health entrypoint. Never authenticates or activates reviewers."""
from pathlib import Path
import json
from fastapi import FastAPI
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / 'infra/level16-staging/owner-approval.json'


def check_package(document):
    if (not isinstance(document,dict) or type(document.get('schemaVersion')) is not int or document.get('schemaVersion')!=1
            or document.get('kind')!='LEVEL16_OWNER_DECISION_PACKAGE_NOT_AUTHORIZATION'
            or document.get('liveAccessEnabled') is not False):
        raise ValueError('A decision package cannot enable reviewer access')
    decisions=document.get('decisions')
    if not isinstance(decisions,list) or any(not isinstance(d,dict) for d in decisions) or [d.get('id') for d in decisions] != [f'A{i:02}' for i in range(1,15)]:
        raise ValueError('All fourteen explicit owner decisions are required')
    if any(d.get('required') is not True or not isinstance(d.get('decision'),str) or not d['decision'].strip() for d in decisions):
        raise ValueError('Invalid owner decision checklist')
    return {'status':'BLOCKED','liveIntegrationEnabled':False,
            'decisionReferencesMissing':[d['id'] for d in decisions if not d.get('approvalReference')],
            'blockers':['DECISION_FILE_IS_NOT_AUTHORIZATION','LIVE_ACTIVATION_CODE_NOT_RELEASED',
                        'REAL_TOKEN_PROFILE_QUALIFICATION_REQUIRED','EXTERNAL_APPROVAL_AND_INFRASTRUCTURE_REQUIRED'],
            'databaseProbe':'NOT_PERFORMED_NO_AUTHORIZATION','actualAuthenticatedSources':0,'actualScientificReviews':0}


app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)


@app.middleware('http')
async def no_cache(request,call_next):
    response=await call_next(request)
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    return response


@app.get('/livez')
def livez():
    return {'status':'ALIVE_PREPARATION_ONLY','reviewerAccessEnabled':False}


@app.get('/readyz')
def readyz():
    try:
        result=check_package(json.loads(PACKAGE.read_text(encoding='utf-8')))
    except (ValueError,OSError):
        result={'status':'BLOCKED','liveIntegrationEnabled':False,'blockers':['INVALID_OR_MISSING_APPROVAL_PACKAGE']}
    return JSONResponse(result,status_code=503)


@app.api_route('/{path:path}',methods=['GET','POST','PUT','PATCH','DELETE'])
def blocked(path:str):
    return JSONResponse({'status':'BLOCKED','liveIntegrationEnabled':False,
                         'reason':'Preparation entrypoint has no reviewer or source mutation routes'},status_code=503)
