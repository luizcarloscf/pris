from __future__ import annotations

from .context import Context


class Interceptor(object):
    """Code a ServiceProvider runs around every request; subclasses override either method."""

    def before_call(self, context: Context) -> None:
        """Run before the service function.

        Args:
            context: the request, and the reply being built.
        """

    def after_call(self, context: Context) -> None:
        """Run after the service function, before the reply is published.

        Args:
            context: the request, and the reply with its status.
        """
