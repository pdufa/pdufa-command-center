"""NCT stream selftest does not mislabel absent dossier tables as medical failure."""
from app import nct_live_stream as stream

class _Result:
    def __init__(self, value):
        self.value=value
    def one(self):
        return self.value
    def scalar(self):
        return self.value

class _Connection:
    def __init__(self,tables,has_seed):
        self.tables=tables
        self.has_seed=has_seed
        self.queries=[]
    def __enter__(self):
        return self
    def __exit__(self,*_):
        return False
    def execute(self,sql,*_):
        statement=str(sql)
        self.queries.append(statement)
        if "to_regclass" in statement:
            return _Result(self.tables)
        if "EXISTS" in statement:
            return _Result(self.has_seed)
        raise AssertionError("Unexpected write or external lookup")

class _Engine:
    def __init__(self,tables,has_seed):
        self.connection=_Connection(tables,has_seed)
    def connect(self):
        return self.connection

def test_selftest_informs_when_historical_dossier_schema_is_not_present():
    engine=_Engine((None,None),False)
    assert stream.scientific_selftest_prerequisites(engine)=="SCIENTIFIC_DOSSIER_TABLES_NOT_INSTALLED"
    assert len(engine.connection.queries)==1

def test_selftest_informs_when_dossier_tables_exist_but_not_seeded():
    engine=_Engine(("scientific_candidate_dossiers","scientific_review_runs"),False)
    assert stream.scientific_selftest_prerequisites(engine)=="NO_SAVED_SCIENTIFIC_DOSSIERS"

def test_selftest_is_eligible_only_when_existing_dossier_can_be_read():
    engine=_Engine(("scientific_candidate_dossiers","scientific_review_runs"),True)
    assert stream.scientific_selftest_prerequisites(engine) is None
    assert len(engine.connection.queries)==2
