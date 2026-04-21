#!/bin/bash
cd "$(dirname "$0")"
exec venv/bin/python -m uvicorn main:app --reload --port 8000
