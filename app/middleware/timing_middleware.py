"""Timing middleware to log API request duration"""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to log total time taken for each API request"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        elapsed_time = time.time() - start_time
        print(f"{elapsed_time:.3f}s")
        return response

