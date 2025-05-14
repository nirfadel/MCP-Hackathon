# run_server.py  – minimal, no custom loop
import uvicorn

uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)

