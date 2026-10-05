# -*- coding: utf-8 -*-
"""Install-time hooks."""

import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Create a partial index on mail_mail(state).

    Stock Odoo does not index mail_mail.state. On instances that retain a
    large mail history, counting the queue is a sequential scan -- which is
    exactly the kind of cost this module must not introduce. The index is
    partial, so it only covers rows still in flight and stays tiny.

    CONCURRENTLY is not used because module installation runs inside a
    transaction. On a very large mail_mail this will briefly lock writes;
    build it by hand out of hours if that matters to you.
    """
    try:
        env.cr.execute("""
            CREATE INDEX IF NOT EXISTS mail_mail_state_pending_idx
                ON mail_mail (state)
             WHERE state IN ('outgoing', 'exception')
        """)
    except Exception:
        _logger.warning(
            "Could not create mail_mail queue index; the mail queue probe "
            "will fall back to a sequential scan.", exc_info=True)
