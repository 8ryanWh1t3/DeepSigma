"""Optional stateless HTTP facade. No server starts on import.

Deploy behind a managed gateway with TLS, rate limits and process limits. The
reference bearer check is not enterprise IAM. No file paths or runtime regex
configuration are accepted over HTTP.
"""
from __future__ import annotations
import secrets
from .pipeline import VinculumPipeline
from .io import LoadLimits
from .utils import read_json
from .version import __version__


def create_app(*,token=None,allow_unauthenticated=False,max_body_bytes=2_000_000,
               max_nodes=1000,max_pairs=2000):
    if token is None and not allow_unauthenticated:
        raise ValueError('supply token, or explicitly enable a local unauthenticated demo')
    if token is not None and (not isinstance(token,str) or len(token)<16):
        raise ValueError('reference bearer token must be a string of at least 16 characters')
    if type(max_body_bytes) is not int or max_body_bytes<1:raise ValueError('max body must be positive')
    try:
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
        from starlette.concurrency import run_in_threadpool
    except ImportError as exc:
        raise ImportError('HTTP adapter requires vinculum-pylib[api]') from exc
    app=FastAPI(title='VINCULUM reference evaluation API',version=__version__,docs_url=None,redoc_url=None,openapi_url=None)
    engine=VinculumPipeline(limits=LoadLimits(max_bytes=max_body_bytes,max_rows=max_nodes,max_text_chars=100_000),
                           max_nodes=max_nodes,max_pairs=max_pairs)
    @app.get('/health')
    async def health():return {'status':'ready','version':__version__,'reference_only':True}
    async def evaluate(request):
        if token is not None:
            supplied=request.headers.get('authorization','')
            if not secrets.compare_digest(supplied.encode(),('Bearer '+token).encode()):
                return JSONResponse({'error':'unauthorized'},status_code=401)
        if request.headers.get('content-type','').split(';')[0].strip()!='application/json':
            return JSONResponse({'error':'application/json required'},status_code=415)
        chunks=[];size=0
        async for chunk in request.stream():
            size+=len(chunk)
            if size>max_body_bytes:return JSONResponse({'error':'body too large'},status_code=413)
            chunks.append(chunk)
        try:
            job=read_json(b''.join(chunks).decode('utf-8'))
            if not isinstance(job,dict):raise ValueError('job must be an object')
            if job.get('lexicon'):raise ValueError('HTTP jobs cannot supply executable regex lexicons; use deployment-owned extraction rules')
            for src in job.get('sources',()):
                if not isinstance(src,dict) or 'path' in src or src.get('format') not in {'txt','md','json','jsonl','csv'}:
                    raise ValueError('HTTP input supports bounded inline text/JSON/CSV sources only; no file paths')
            result=await run_in_threadpool(engine.run,job)
            return JSONResponse(result.to_dict())
        except (ValueError,TypeError,KeyError,OverflowError,UnicodeError,RecursionError) as exc:
            return JSONResponse({'error':'invalid_input','detail':str(exc)[:600]},status_code=422)
    # Local import + postponed annotations otherwise confuse FastAPI's dependency parser.
    evaluate.__annotations__['request']=Request
    app.add_api_route('/v1/evaluate',evaluate,methods=['POST'])
    return app
