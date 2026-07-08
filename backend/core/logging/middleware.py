from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware that adds observability to every request.

    Injects a ``trace_id`` into the request state and logs:
    - API latency
    - Request method and path
    - Response status code
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process an incoming request with observability instrumentation.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware/route handler.

        Returns:
            The HTTP response with ``X-Trace-ID`` header.
        """
        trace_id = str(uuid.uuid4())
        request.state.trace_id = trace_id
        start_time = time.time()

        response = await call_next(request)

        elapsed_ms = (time.time() - start_time) * 1000
        response.headers["X-Trace-ID"] = trace_id

        logger.info(
            "API request",
            extra={
                "trace_id": trace_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "elapsed_ms": round(elapsed_ms, 2),
            },
        )

        return response