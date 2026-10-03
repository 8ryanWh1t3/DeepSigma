import json
from pathlib import Path
import pytest
from vinculum import NumericRange,VinculumPipeline,interval_calculate
from vinculum.store import RunArchive
from vinculum.api import create_app

EX=Path(__file__).resolve().parents[1]/'examples'
def job():return json.loads((EX/'bakery_pipeline.json').read_text())

@pytest.mark.parametrize('expression,value',[('2+2',4),('0.1+0.2','0.3'),('1/3','1/3'),('-2+7',5),('2*3+1',7),('2*(3+1)',8),('1e-3+1','1.001'),('+2',2)])
def test_exact_scalar_arithmetic(expression,value):assert interval_calculate(expression,{})==NumericRange.point(value)

def test_interval_uncertainty_propagates_not_value_discount():
    r=interval_calculate('x*2',{'x':NumericRange(9,11)})
    assert r==NumericRange(18,22)
    r=interval_calculate('x-x',{'x':NumericRange(9,11)})
    assert r==NumericRange(-2,2) # enclosure; dependency is not guessed away

@pytest.mark.parametrize('expression',["__import__('os').system('echo bad')",'x.real','x[0]','x**100000','[1,2]','(lambda:1)()','True','unknown','1/0'])
def test_expression_restrictions(expression):
    with pytest.raises(ValueError):interval_calculate(expression,{'x':NumericRange.point(1)})

def test_zero_interval_denominator():
    with pytest.raises(ValueError):interval_calculate('1/x',{'x':NumericRange(-1,1)})

def test_expression_budget():
    with pytest.raises(ValueError):interval_calculate('1+'*100+'1',{})
    with pytest.raises(ValueError):interval_calculate('x',{'x':NumericRange(None,1)})

@pytest.fixture
def client():
    pytest.importorskip('fastapi');pytest.importorskip('httpx')
    from fastapi.testclient import TestClient
    with TestClient(create_app(token='a-test-token-at-least-16')) as c:yield c

H={'Authorization':'Bearer a-test-token-at-least-16'}

def test_api_auth_required_factory():
    with pytest.raises(ValueError):create_app()
    with pytest.raises(ValueError):create_app(token='short')

def test_api_evaluation(client):
    assert client.get('/health').json()['version']=='0.7.0'
    assert client.post('/v1/evaluate',json=job()).status_code==401
    r=client.post('/v1/evaluate',json=job(),headers=H)
    assert r.status_code==200 and r.json()['report']['pairs'][0]['status']=='CONFLICT'

def test_api_paths_forbidden(client):
    j=job();j['sources'][0].pop('data');j['sources'][0]['path']='/etc/passwd'
    assert client.post('/v1/evaluate',json=j,headers=H).status_code==422

def test_api_regex_forbidden(client):
    j=job();j['lexicon']=[{'pattern':'(a+)+$'}]
    assert client.post('/v1/evaluate',json=j,headers=H).status_code==422

def test_api_json_boundary(client):
    assert client.post('/v1/evaluate',content='x',headers=H).status_code==415
    assert client.post('/v1/evaluate',content='{"x":1,"x":2}',headers={**H,'Content-Type':'application/json'}).status_code==422
    assert client.post('/v1/evaluate',json=[1,2],headers=H).status_code==422

def test_api_body_limit():
    from fastapi.testclient import TestClient
    with TestClient(create_app(allow_unauthenticated=True,max_body_bytes=20)) as c:
        assert c.post('/v1/evaluate',json=job()).status_code==413

def test_archive_append_identity_and_integrity(tmp_path):
    r=VinculumPipeline().run(job())
    p=tmp_path/'runs.db'
    with RunArchive(p)as a:
        assert a.put(r) is True and a.put(r) is False
        assert a.get(r.job_fingerprint)['report']['pairs'][0]['status']=='CONFLICT'
    with RunArchive(p)as a:
        a.connection.execute('UPDATE runs SET payload=? WHERE job_id=?',('tampered',r.job_fingerprint));a.connection.commit()
        with pytest.raises(ValueError):a.get(r.job_fingerprint)
        with pytest.raises(KeyError):a.get('not-present')
