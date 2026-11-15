"""PAST exact-event roster safety tests. Fixtures are synthetic, not real FDA data."""
import json
from datetime import datetime
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import assessment_runtime as runtime
from app import past_assessment_cohort as past
from test_assessment_runtime import engine, snapshot

NCT='NCT04576949'
EVENT=past.expected(2026)[0]['eventKey']


def seed(engine, *,official=True):
    tables=[
      'CREATE TABLE phase3_fda_applications(application_id TEXT PRIMARY KEY,application_number TEXT,drug TEXT,indication TEXT)',
      'CREATE TABLE phase3_fda_decisions(decision_id TEXT PRIMARY KEY,application_id TEXT,decision_date TEXT,pdufa_date TEXT,verification_status TEXT)',
      'CREATE TABLE phase3_trial_applications(nct_id TEXT,application_id TEXT,verification_status TEXT,evidence_id TEXT)',
      'CREATE TABLE phase3_evidence(evidence_id TEXT PRIMARY KEY,url TEXT,document TEXT,verification_status TEXT,publisher_kind TEXT)'
    ]
    with engine.begin() as c:
        for sql in tables:c.execute(text(sql))
        c.execute(text("INSERT INTO phase3_fda_applications VALUES('synthetic-app','BLA123456','Synthetic RGX-121','Synthetic indication')"))
        c.execute(text("INSERT INTO phase3_fda_decisions VALUES('synthetic-cycle','synthetic-app','2026-02-08','2026-02-08','VERIFIED')"))
        c.execute(text("INSERT INTO phase3_evidence VALUES('synthetic-proof','https://www.fda.gov/example','BLA123456 Synthetic RGX-121 NCT04576949','VERIFIED',:publisher)"),{'publisher':'FDA' if official else 'UNVERIFIED'})
        c.execute(text("INSERT INTO phase3_trial_applications VALUES(:nct,'synthetic-app','VERIFIED','synthetic-proof')"),{'nct':NCT})


def link(**changes):
    return {**{'eventKey':EVENT,'applicationId':'synthetic-app','decisionId':'synthetic-cycle',
               'ncts':[NCT],'cutoffDate':'2026-01-02','evidenceId':'synthetic-proof'},**changes}


def test_no_fabricated_past_cohort_from_unverified_queue(engine):
    summary=past.roster(engine,2026)
    assert summary['total']==20 and summary['linked']==0
    assert summary['ready'] is False and summary['tasks']==[] and summary['eligibleTasks']==[]
    assert all(item['status']=='MISSING_VERIFIED_LINK' for item in summary['events'])
    year=past.roster(engine,2025)
    assert year['total'] is None and year['ready'] is False


def test_wrong_review_cycle_nct_date_and_unverified_proof_are_rejected(engine):
    seed(engine)
    for invalid in [
      link(ncts=['NCT99999999']),link(decisionId='other-cycle'),
      link(cutoffDate='2026-02-09'),link(evidenceId='wrong-source'),
      link(eventKey='OTHER|2026-02-08|untrusted')
    ]:
        with pytest.raises(ValueError):past.import_verified_link(engine,invalid)
    assert past.roster(engine,2026)['linked']==0


def test_past_single_verified_link_requires_original_predecision_snapshot(engine):
    seed(engine)
    digest=past.import_verified_link(engine,link())
    assert past.import_verified_link(engine,link())==digest
    first=past.roster(engine,2026)
    assert first['linked']==0 and first['events'][0]['status']=='LINK_OR_PRE_CUTOFF_EVIDENCE_INCOMPLETE'
    source=snapshot(captured='2025-12-01T00:00:00+00:00')
    with engine.begin() as c:
        c.execute(text("""INSERT INTO assessment_v2_sources
          (snapshot_id,nct_id,captured_at,published_at,source_url,raw_sha256,input_sha256,document_json)
          VALUES(:snapshot_id,:nct_id,:captured_at,:published_at,:source_url,:raw_sha256,:input_sha256,:document_json)"""),source)
    partial=past.roster(engine,2026)
    assert partial['linked']==1 and partial['ready'] is False  # the other 19 are not linked
    assert partial['tasks']==[], 'A partial roster is never misreported as fully verified'
    assert partial['eligibleTasks']==[{'nct':NCT,'cutoffDate':'2026-01-02','eventKey':EVENT}]
    assert sum(item['status']!='READY' for item in partial['events'])==19
    with engine.begin() as c:
        with pytest.raises(Exception):
            c.execute(text("UPDATE past_assessment_event_links SET cutoff_date='2027-01-01'"))
    assert past.roster(engine,2026)['tasks']==[]


def test_year_roster_route_requires_owner_auth(engine):
    def deny():raise HTTPException(401,'Owner required')
    def ok():return None
    app=FastAPI();app.include_router(runtime.router(lambda:engine,deny,ok,ok,allow_local=True))
    client=TestClient(app)
    assert client.get('/api/assessment-runtime/past/roster?year=2026').status_code==401
    app.dependency_overrides[deny]=ok
    assert client.get('/api/assessment-runtime/past/roster?year=2026').json()['ready'] is False
    assert client.get('/api/assessment-runtime/past/roster?year=2016').status_code==422
