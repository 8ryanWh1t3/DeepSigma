"""Bounded, local-only source loading. File parsing is not semantic understanding.

Optional formats import their libraries lazily. No OCR, macro execution, remote
fetch, SQL execution, or inference from a filename is performed.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import csv
import io
import json
import zipfile
from typing import Any
from .evidence import EvidenceSource
from .utils import canonical_json, read_json


@dataclass(frozen=True)
class LoadLimits:
    max_bytes: int = 25_000_000
    max_rows: int = 10_000
    max_text_chars: int = 1_000_000
    max_pages: int = 200
    max_expanded_bytes: int = 50_000_000

    def __post_init__(self):
        if any(type(x) is not int or x < 1 for x in self.__dict__.values()):
            raise ValueError('loader limits must be positive integers')


@dataclass(frozen=True)
class SourceBatch:
    source: EvidenceSource
    rows: tuple[dict[str, Any], ...]
    locators: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    extraction_kind: str = 'explicit records'


class OptionalDependencyError(ImportError):
    pass


def _dependency(module, extra):
    import importlib
    try: return importlib.import_module(module)
    except ImportError as exc:
        raise OptionalDependencyError(f'{module} is required; install vinculum-pylib[{extra}]') from exc


def _zip_preflight(payload, limits):
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        if len(z.infolist()) > 10_000 or sum(x.file_size for x in z.infolist()) > limits.max_expanded_bytes:
            raise ValueError('archive exceeds expanded-size or entry limit')
        if any(x.flag_bits & 1 for x in z.infolist()):
            raise ValueError('encrypted Office archives are not supported')


def _yaml(text):
    yaml = _dependency('yaml', 'config')
    class StrictLoader(yaml.SafeLoader):
        def compose_node(self, parent, index):
            if self.check_event(yaml.AliasEvent):
                raise ValueError('YAML aliases are not supported in replayable configuration')
            return super().compose_node(parent, index)
    def mapping(loader, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key in result:
                raise ValueError('YAML keys must be unique strings')
            result[key] = loader.construct_object(value_node, deep=deep)
        return result
    StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    try: return yaml.load(text, Loader=StrictLoader)
    except yaml.YAMLError as exc: raise ValueError('invalid or unsafe YAML') from exc


def load_config(path, *, max_bytes=1_000_000):
    p = Path(path)
    if p.stat().st_size > max_bytes: raise ValueError('configuration exceeds byte limit')
    text = p.read_text(encoding='utf-8-sig')
    data = _yaml(text) if p.suffix.lower() in {'.yaml', '.yml'} else read_json(text)
    if not isinstance(data, dict): raise ValueError('configuration must be an object')
    return data


def load_source(*, source_id: str, format: str, data=None, path=None,
                base_dir=None, allow_files=False, sheet=None, limits=None,
                expected_sha256=None) -> SourceBatch:
    """Load inline data or a contained relative file. API callers use allow_files=False.

    PDF/DOCX are emitted as located text segments; structured files become rows.
    Unrecognized data is never reported as a complete semantic extraction.
    """
    limits = limits or LoadLimits()
    if (data is None) == (path is None):
        raise ValueError('supply exactly one of inline data or a local path')
    fmt = format.lower().lstrip('.')
    fmt = {'yml':'yaml', 'text':'txt', 'ndjson':'jsonl'}.get(fmt, fmt)
    loc = 'inline:' + source_id
    if path is not None:
        if not allow_files or base_dir is None:
            raise ValueError('file access requires explicit local root and allow_files=True')
        base = Path(base_dir).resolve()
        p = (base / path).resolve()
        if not p.is_relative_to(base) or not p.is_file():
            raise ValueError('source path is missing or outside the allowed root')
        if p.stat().st_size > limits.max_bytes: raise ValueError('source exceeds byte limit')
        payload = p.read_bytes()
        loc = str(p.relative_to(base))
    elif isinstance(data, bytes):
        payload = data
    elif isinstance(data, str):
        payload = data.encode('utf-8')
    else:
        payload = canonical_json(data).encode('utf-8')
    if len(payload) > limits.max_bytes: raise ValueError('source exceeds byte limit')
    source = EvidenceSource.from_bytes(source_id, payload,
        basis='bytes read by local loader; content identity does not prove factual accuracy',
        locator=loc, media_type=fmt)
    if expected_sha256 is not None and source.sha256 != expected_sha256:
        raise ValueError('source SHA-256 does not match the declared expected content')
    warnings, rows, locators = [], [], []
    kind = 'explicit records'
    def add(row, where):
        if not isinstance(row, dict): raise ValueError('each mapped record must be an object')
        if len(rows) >= limits.max_rows: raise ValueError('source exceeds row/segment limit')
        rows.append(row); locators.append(where)
    def text_segment(value, where):
        if not isinstance(value, str): raise ValueError('text segment must be a string')
        if len(value) > limits.max_text_chars: raise ValueError('text exceeds character limit')
        # Keep blank page/paragraph placeholders visible as unhandled material.
        add({'text': value}, where)
    if fmt in {'txt','md'}:
        kind = 'line segmentation, not semantic parsing'
        text = payload.decode('utf-8-sig')
        if len(text) > limits.max_text_chars: raise ValueError('text exceeds character limit')
        for i, line in enumerate(text.splitlines(), 1):
            if line.strip(): text_segment(line.strip(), f'{loc}#line={i}')
    elif fmt in {'json','yaml'}:
        value = _yaml(payload.decode('utf-8-sig')) if fmt == 'yaml' else read_json(payload.decode('utf-8-sig'))
        if isinstance(value, dict): value = [value]
        if not isinstance(value, list): raise ValueError('record source must be an object or array of objects')
        for i, row in enumerate(value, 1): add(row, f'{loc}#row={i}')
    elif fmt == 'jsonl':
        for i,line in enumerate(payload.decode('utf-8-sig').splitlines(),1):
            if line.strip(): add(read_json(line),f'{loc}#line={i}')
    elif fmt == 'csv':
        reader = csv.DictReader(io.StringIO(payload.decode('utf-8-sig')))
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError('CSV requires unique headers')
        for i,row in enumerate(reader,2):
            if None in row or any(v is None for v in row.values()): raise ValueError('CSV row has the wrong number of fields')
            add(row,f'{loc}#row={i}')
    elif fmt == 'pdf':
        kind = 'PDF text layer; no OCR or layout/table understanding'
        pypdf = _dependency('pypdf','documents')
        reader = pypdf.PdfReader(io.BytesIO(payload))
        if reader.is_encrypted: raise ValueError('encrypted PDF is not supported')
        if len(reader.pages) > limits.max_pages: raise ValueError('PDF exceeds page limit')
        for i,page in enumerate(reader.pages,1):
            content = page.get_contents()
            if content is not None and len(content.get_data()) > limits.max_expanded_bytes:
                raise ValueError('PDF content stream exceeds expanded-size limit')
            text = page.extract_text() or ''
            if not text.strip(): warnings.append(f'page {i}: no usable text layer; not OCRed')
            for j,line in enumerate(text.splitlines() or [''],1):
                text_segment(line,f'{loc}#page={i}&line={j}')
        warnings.append('PDF extraction may omit images and misrepresent visual reading order; review the original')
    elif fmt == 'docx':
        kind = 'DOCX body paragraphs/tables; no images, footnotes, comments, or tracked-change interpretation'
        _zip_preflight(payload, limits)
        docx = _dependency('docx','documents')
        doc = docx.Document(io.BytesIO(payload))
        # XML body order is retained; these are text segments, not an inferred ontology.
        for i,block in enumerate(doc.iter_inner_content(),1):
            if isinstance(block,docx.text.paragraph.Paragraph):
                if block.text.strip(): text_segment(block.text,f'{loc}#body={i}')
            else:
                for j,row in enumerate(block.rows,1):
                    text_segment(' | '.join(c.text for c in row.cells),f'{loc}#table={i}&row={j}')
        warnings.append('Only body text and tables extracted; other Word content needs an application adapter')
    elif fmt == 'xlsx':
        _zip_preflight(payload, limits)
        try:
            from artifact_tool import Blob, SpreadsheetFile
        except ImportError as exc:
            raise OptionalDependencyError('XLSX adapter requires artifact_tool in the host; CSV is portable') from exc
        book = SpreadsheetFile.import_xlsx(Blob(payload))
        ws = book.worksheets.get_item(sheet) if sheet else book.worksheets.get_item_at(0)
        # Explicit bounded range; do not infer arbitrary spreadsheet formula meaning.
        warnings.append(f'XLSX extraction is limited to columns A:AZ and the first {limits.max_rows} data rows; not full workbook coverage')
        used = ws.get_range('A1:AZ' + str(limits.max_rows + 1))
        values, formulas = used.values, used.formulas
        if not values: raise ValueError('workbook sheet has no values')
        headers = values[0]
        while headers and headers[-1] is None: headers.pop()
        if not headers or any(not isinstance(x,str) or not x for x in headers) or len(set(headers)) != len(headers):
            raise ValueError('worksheet row 1 needs unique text column names')
        for i,row in enumerate(values[1:],2):
            if not any(v is not None for v in row): continue
            out = dict(zip(headers,row[:len(headers)]))
            for j,head in enumerate(headers):
                formula = formulas[i-1][j] if i-1 < len(formulas) and j < len(formulas[i-1]) else None
                if formula:
                    out[head] = None
                    warnings.append(f'row {i} / {head}: formula not admitted as a verified numeric observation')
            add(out,f'{loc}#sheet={sheet or "first"}&row={i}')
    elif fmt in {'ttl','turtle'}:
        from .rdf import _parse
        from rdflib import URIRef, Literal
        graph = _parse(payload.decode('utf-8-sig'))
        kind = 'RDF triples; predicate selection and numeric meaning require explicit field mapping'
        for i,(subject,predicate,obj) in enumerate(sorted(graph,key=lambda t:tuple(str(x) for x in t)),1):
            add({'subject':str(subject) if isinstance(subject,URIRef) else None,
                 'predicate':str(predicate),'object':str(obj),
                 'value':str(obj) if isinstance(obj,Literal) else None,
                 'text':str(obj) if isinstance(obj,Literal) else '',
                 'datatype':str(obj.datatype) if isinstance(obj,Literal) and obj.datatype else None,
                 'language':obj.language if isinstance(obj,Literal) else None},f'{loc}#triple={i}')
        warnings.append('Unmapped RDF predicates are not inferred as measurements; blank-node identities are unresolved across sources')
    elif fmt == 'parquet':
        pq = _dependency('pyarrow.parquet','parquet')
        reader = pq.ParquetFile(io.BytesIO(payload))
        if reader.metadata.num_rows > limits.max_rows: raise ValueError('Parquet exceeds row limit')
        for batch in reader.iter_batches(batch_size=min(1024,limits.max_rows)):
            for row in batch.to_pylist(): add(row,f'{loc}#row={len(rows)+1}')
    else:
        raise ValueError(f'unsupported mapped-source format: {fmt}; use the native scenario RDF adapter for Turtle')
    if sum(len(canonical_json(r)) for r in rows) > limits.max_expanded_bytes:
        raise ValueError('extracted records exceed expanded-size limit')
    if not rows: warnings.append('source yielded zero records; no completeness claim')
    return SourceBatch(source,tuple(rows),tuple(locators),tuple(warnings),kind)
