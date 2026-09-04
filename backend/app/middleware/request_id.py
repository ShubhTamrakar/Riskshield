"""
Request ID middleware.

Injects a unique X-Request-ID on every request and response.
Propagates an existing ID if the caller provides one (e.g., from an upstream system).
The ID is stored in request.state.request_id for use in logs and error responses.
"""
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Accept upstream request ID or generate a new one
        req_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = req_id

        response: Response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = req_id
        return response
