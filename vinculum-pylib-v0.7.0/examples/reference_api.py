"""Optional reference HTTP adapter. No embedded token and no listener on import.

Install the api extra. Set VINCULUM_API_TOKEN using your deployment's secret
management; then start an ASGI server with examples.reference_api:app.
This is not enterprise IAM or an operational certification.
"""
import os
from vinculum.api import create_app

app = create_app(token=os.environ["VINCULUM_API_TOKEN"])
