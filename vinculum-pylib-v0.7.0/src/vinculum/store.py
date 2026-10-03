"""Optional SQLite run archive. Persistence is not an authority or root of trust."""
import hashlib
import sqlite3
from .utils import canonical_json,read_json


class RunArchive:
    def __init__(self,path):
        self.connection=sqlite3.connect(str(path))
        self.connection.execute('CREATE TABLE IF NOT EXISTS runs (job_id TEXT PRIMARY KEY, payload TEXT NOT NULL, digest TEXT NOT NULL)')
        self.connection.commit()

    def put(self,result):
        payload=canonical_json(result.to_dict())
        digest=hashlib.sha256(payload.encode()).hexdigest()
        with self.connection:
            current=self.connection.execute('SELECT digest FROM runs WHERE job_id=?',(result.job_fingerprint,)).fetchone()
            if current:
                if current[0]!=digest:raise ValueError('same run identity has different output; use a new run/version')
                return False
            self.connection.execute('INSERT INTO runs VALUES (?,?,?)',(result.job_fingerprint,payload,digest))
        return True

    def get(self,job_id):
        row=self.connection.execute('SELECT payload,digest FROM runs WHERE job_id=?',(job_id,)).fetchone()
        if row is None:raise KeyError(job_id)
        if hashlib.sha256(row[0].encode()).hexdigest()!=row[1]:raise ValueError('stored run content failed its fingerprint check')
        return read_json(row[0])

    def close(self):self.connection.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
