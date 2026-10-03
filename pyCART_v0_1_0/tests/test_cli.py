import json
import pytest
from deepsigma_cartography.cli import main
from deepsigma_cartography.sample import AS_OF


def test_demo_generates_working_artifacts(tmp_path,capsys):
    out=tmp_path/'demo'
    assert main(['demo','--out',str(out)])==0
    result=json.loads(capsys.readouterr().out)
    assert result['nodes']==10 and result['route_hops']==3 and result['editions']==2
    assert (out/'editions.sqlite3').exists()
    assert main(['demo','--out',str(out)])==2

def test_validate(atlas,tmp_path,capsys):
    p=atlas.save(tmp_path/'a.json')
    assert main(['validate',str(p)])==0
    assert json.loads(capsys.readouterr().out)['valid'] is True

def test_bad_input_no_traceback(tmp_path,capsys):
    p=tmp_path/'a.json';p.write_text('{}')
    assert main(['validate',str(p)])==2
    assert 'Traceback' not in capsys.readouterr().err

@pytest.mark.parametrize('command,args',[
    ('assess',[]),('trace',['mission:readiness','evidence:report']),
    ('impact',['evidence:report']),('dependencies',['mission:readiness']),('fold',[]),
])
def test_analysis_commands(atlas,tmp_path,command,args):
    p=atlas.save(tmp_path/'a.json');out=tmp_path/'result.json'
    assert main([command,str(p),*args,'--as-of',AS_OF,'--out',str(out)])==0
    assert json.loads(out.read_text())

@pytest.mark.parametrize('format',['json','jsonl','jsonld','nt','csv','vinculum'])
def test_export_commands(atlas,tmp_path,format):
    p=atlas.save(tmp_path/'a.json');out=tmp_path/('out.'+format)
    assert main(['export',str(p),'--as-of',AS_OF,'--format',format,'--out',str(out)])==0
    assert out.exists()

def test_archive_cli(atlas,tmp_path,capsys):
    p=atlas.save(tmp_path/'a.json');db=tmp_path/'a.db'
    assert main(['archive','init',str(db),'--atlas-id',atlas.id])==0
    assert main(['archive','append',str(db),str(p),'--recorded-at',AS_OF,'--expected-parent','GENESIS'])==0
    assert main(['archive','verify',str(db)])==0
    assert main(['archive','show',str(db),'1'])==0
    assert main(['archive','append',str(db),str(p),'--recorded-at',AS_OF,'--expected-parent','GENESIS'])==2
