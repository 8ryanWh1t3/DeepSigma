import io
import json
from pathlib import Path
import pytest
from vinculum.io import load_source,LoadLimits,OptionalDependencyError,load_config
from vinculum.represent import extract_records,FieldMapping
from vinculum import NumericRange

S={'scope_id':'x','population':'cookies','denominator':'one order','granularity':'line','timeless':True}

@pytest.mark.parametrize('fmt,data,n',[('txt','dozen\npair',2),('md','dozen',1),('json',[{'x':1}],1),('json',{'x':1},1),('jsonl','{"x":1}\n{"x":2}',2),('csv','x,y\n1,2\n3,4\n',2),('yaml','- x: 1\n- x: 2',2)])
def test_source_formats(fmt,data,n):
    batch=load_source(source_id='s',format=fmt,data=data)
    assert len(batch.rows)==n
    assert len(batch.source.sha256)==64
    assert len(batch.locators)==n

@pytest.mark.parametrize('data',['{"a":1,"a":2}','{"x":NaN}','[1,2]','true'])
def test_bad_json(data):
    with pytest.raises(ValueError):load_source(source_id='s',format='json',data=data)

@pytest.mark.parametrize('data',['x: 1\nx: 2','a: &ref [1,2]\nb: *ref','!!python/object/apply:os.system [echo evil]'])
def test_yaml_failclosed(data):
    with pytest.raises(ValueError):load_source(source_id='s',format='yaml',data=data)

@pytest.mark.parametrize('data',['a,a\n1,2','a,b\n1,2,3','a,b\n1'])
def test_bad_csv(data):
    with pytest.raises(ValueError):load_source(source_id='s',format='csv',data=data)

def test_size_caps():
    with pytest.raises(ValueError):load_source(source_id='s',format='txt',data='abcdef',limits=LoadLimits(max_bytes=3))
    with pytest.raises(ValueError):load_source(source_id='s',format='txt',data='a\nb',limits=LoadLimits(max_rows=1))
    with pytest.raises(ValueError):load_source(source_id='s',format='txt',data='abcd',limits=LoadLimits(max_text_chars=3))

def test_local_root_and_hash(tmp_path):
    p=tmp_path/'a.txt';p.write_text('dozen')
    with pytest.raises(ValueError):load_source(source_id='s',format='txt',path='a.txt',base_dir=tmp_path)
    b=load_source(source_id='s',format='txt',path='a.txt',base_dir=tmp_path,allow_files=True)
    assert b.source.locator=='a.txt'
    with pytest.raises(ValueError):load_source(source_id='s',format='txt',path='../outside.txt',base_dir=tmp_path,allow_files=True)
    with pytest.raises(ValueError):load_source(source_id='s',format='txt',data='dozen',expected_sha256='0'*64)
    b2=load_source(source_id='s',format='txt',data='dozen',expected_sha256=b.source.sha256)
    assert b2.source.sha256==b.source.sha256

def test_empty_and_unsupported():
    assert load_source(source_id='s',format='txt',data='').warnings
    with pytest.raises(ValueError):load_source(source_id='s',format='exe',data='abc')
    with pytest.raises(ValueError):load_source(source_id='s',format='txt')

def test_text_expectation_and_trace():
    b=load_source(source_id='s',format='txt',data="baker's dozen\nmaybe a dozen")
    nodes,traces=extract_records(b,FieldMapping('L',defaults={'entity':'x','scope':S}))
    assert nodes[0].quantity==NumericRange.point(13)
    assert nodes[1].quantity is None
    assert traces[1].status=='UNRESOLVED' and traces[1].locator.endswith('line=2')
    assert nodes[0].source_ids==('s',)

def test_math_unknown_defense_not_one():
    b=load_source(source_id='s',format='json',data=[{'q':12}])
    nodes,traces=extract_records(b,FieldMapping('M',columns={'value':'q'},defaults={'entity':'x','concept':'item_count','unit':'count','scope':S}))
    assert nodes[0].quantity==NumericRange.point(12)
    assert nodes[0].support.assess()['strength'] is None

@pytest.mark.parametrize('q',[True,'NaN','inf','1e100000'])
def test_bad_quantities(q):
    with pytest.raises(ValueError):
        b=load_source(source_id='s',format='json',data=[{'q':q}])
        extract_records(b,FieldMapping('M',columns={'value':'q'}))

def test_missing_interval_not_invented_unbounded():
    b=load_source(source_id='s',format='json',data=[{'lo':0}])
    nodes,traces=extract_records(b,FieldMapping('M',columns={'lower':'lo','upper':'hi'}))
    assert nodes[0].quantity is None
    assert any('endpoint absent' in x for x in traces[0].warnings)

def test_lexical_value_conflict():
    b=load_source(source_id='s',format='json',data=[{'text':"baker's dozen",'q':12}])
    with pytest.raises(ValueError,match='contradicts'):
        extract_records(b,FieldMapping('L',columns={'text':'text','value':'q'}))

def test_wrong_lexical_unit():
    b=load_source(source_id='s',format='txt',data='dozen')
    with pytest.raises(ValueError,match='unit differs'):extract_records(b,FieldMapping('L',defaults={'unit':'m'}))

def test_turtle_mapped_rows():
    data='@prefix x: <urn:x:> . x:order x:quantity 12; x:label "baker\'s dozen" .'
    b=load_source(source_id='s',format='ttl',data=data)
    assert len(b.rows)==2
    assert any(x['value']=='12' for x in b.rows)
    assert b.warnings

def test_docx_text_loader():
    docx=pytest.importorskip('docx')
    doc=docx.Document();doc.add_paragraph('dozen');t=doc.add_table(rows=1,cols=2);t.cell(0,0).text='quantity';t.cell(0,1).text='12'
    buf=io.BytesIO();doc.save(buf)
    b=load_source(source_id='word',format='docx',data=buf.getvalue())
    assert b.rows[0]['text']=='dozen' and b.rows[1]['text']=='quantity | 12'
    assert 'table' in b.locators[1]
    assert b.warnings

def test_pdf_text_and_blank():
    pytest.importorskip('pypdf');c=pytest.importorskip('reportlab.pdfgen.canvas')
    buf=io.BytesIO();p=c.Canvas(buf);p.drawString(70,750,'bakers dozen');p.showPage();p.showPage();p.save()
    b=load_source(source_id='pdf',format='pdf',data=buf.getvalue())
    assert any('bakers dozen' in r['text'] for r in b.rows)
    assert any('no usable text' in w for w in b.warnings)

def test_parquet_optional_dependency():
    try:import pyarrow
    except ImportError:
        with pytest.raises(OptionalDependencyError):load_source(source_id='s',format='parquet',data=b'PAR1')
        return
    import pyarrow.parquet as pq
    buf=io.BytesIO();pq.write_table(pyarrow.table({'value':[12]}),buf)
    assert load_source(source_id='s',format='parquet',data=buf.getvalue()).rows[0]['value']==12

def test_config_loader(tmp_path):
    p=tmp_path/'job.yaml';p.write_text('schema: test\nid: x')
    assert load_config(p)['id']=='x'
    p.write_text('- x\n- y')
    with pytest.raises(ValueError):load_config(p)


def test_parquet_actual_roundtrip_when_dependency_available():
    pa=pytest.importorskip('pyarrow',reason='optional pyarrow unavailable in release environment')
    import pyarrow.parquet as pq
    from io import BytesIO
    stream=BytesIO();pq.write_table(pa.table({'value':[12,13]}),stream)
    result=load_source(source_id='real-parquet',format='parquet',data=stream.getvalue())
    assert [r['value'] for r in result.rows]==[12,13]
