from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AddressRequest(BaseModel):
    address: str

@contextmanager
def suppress_output():
    # Temporarily suppress stdout/stderr
    stdout, stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = None, None
    try:
        yield
    finally:
        sys.stdout, sys.stderr = stdout, stderr

def run_main_sync(address: str):
    from main_a2a import user_proxy, manager, group
    
    # Reset the group chat messages
    group.messages = []
    
    with suppress_output():
        user_proxy.initiate_chat(
            manager,
            message=f"Please give me the Table-5 JSON for: {address}",
        )
    
    last = group.messages[-1]
    if isinstance(last, dict):
        return last
    return {"result": last.content if hasattr(last, 'content') else str(last)}

@app.post("/search")
async def search_address(request: AddressRequest):
    try:
        with ThreadPoolExecutor() as executor:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                executor,
                run_main_sync,
                request.address
            )
        return result
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing address: {str(e)}"
        )