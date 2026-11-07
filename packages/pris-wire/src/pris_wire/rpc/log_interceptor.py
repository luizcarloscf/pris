from __future__ import annotations

from ..core import Logger, StatusCode, now
from .context import Context
from .interceptor import Interceptor


class LogInterceptor(Interceptor):
    """Log how long each request took and its status: info if OK, error for INTERNAL_ERROR,
    warning otherwise."""

    def __init__(self) -> None:
        self.log = Logger(name='LogInterceptor')

    def before_call(self, context: Context) -> None:
        self.begin = now()

    def after_call(self, context: Context) -> None:
        took = now() - self.begin
        status = context.reply.status
        assert status is not None
        if status.ok():
            self.log.info("took={}s, code={}", took, status.code.name)
        elif status.code == StatusCode.INTERNAL_ERROR:
            self.log.error('took={}s status={} request={}', took, status,
                           context.request.short_string())
        else:
            self.log.warn('took={}s status={} request={}', took, status,
                          context.request.short_string())
