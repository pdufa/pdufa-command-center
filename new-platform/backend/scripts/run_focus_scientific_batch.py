"""Reproduce a real-source batch in an explicit isolated local database.

Run from new-platform/backend with PYTHONPATH=. This validation runner never
reads production DATABASE_URL or modifies the owner's source roster.
"""
import argparse
import json
from pathlib import Path
from sqlalchemy import create_engine
from app import focus_assessment_batch as batch


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--roster-json',type=Path,required=True,help='Trusted dated owner roster: sourceUrl, retrievedAt, members')
    parser.add_argument('--local-database',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    engine=create_engine('sqlite:///'+str(args.local_database.resolve()),connect_args={'check_same_thread':False})
    document=json.loads(args.roster_json.read_text())
    batch.import_roster(engine,document);batch_id=batch.create(engine)
    try:
        # At most 500 trials × three levels × two attempts, six items at a time.
        for _ in range(500):
            result=batch.execute(engine,batch_id,workers=2,max_items=6)
            args.output.write_text(json.dumps(result,indent=2))
            print(json.dumps({k:result[k] for k in ('batchId','total','fullyProcessed','counts')}),flush=True)
            slots=[s for trial in result['trials'] for s in trial['levels'].values()]
            if all(s['state']=='COMPLETED' or s['attempts']>=2 for s in slots):break
        else:raise RuntimeError('Bounded execution exhausted; retained checkpoints require inspection')
    finally:engine.dispose()


if __name__=='__main__':main()
