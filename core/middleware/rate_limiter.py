from fastapi import Request, HTTPException
import time
from collections import defaultdict
from typing import Dict
import asyncio

class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)
        self._cleanup_task = asyncio.create_task(self._cleanup_old_requests())

    async def _cleanup_old_requests(self):
        while True:
            current_time = time.time()
            for ip in list(self.requests.keys()):
                self.requests[ip] = [req_time for req_time in self.requests[ip]
                                   if current_time - req_time < 60]
                if not self.requests[ip]:
                    del self.requests[ip]
            await asyncio.sleep(60)

    async def __call__(self, request: Request):
        ip = request.client.host
        current_time = time.time()
        
        self.requests[ip] = [req_time for req_time in self.requests[ip]
                           if current_time - req_time < 60]
        
        if len(self.requests[ip]) >= self.requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail="Too many requests"
            )
        
        self.requests[ip].append(current_time)

