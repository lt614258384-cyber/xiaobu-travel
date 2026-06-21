from unittest.mock import patch

from fastapi.testclient import TestClient

import app as app_module


def test_lifespan_initializes_resources_and_stops_scheduler():
    with (
        patch.object(app_module, "init_db") as init_db,
        patch.object(app_module, "cleanup_activity_prompt_templates", create=True) as cleanup,
        patch.object(app_module, "Scheduler") as scheduler_class,
    ):
        scheduler = scheduler_class.return_value

        with TestClient(app_module.app):
            assert getattr(app_module.app.state, "scheduler", None) is scheduler

        init_db.assert_called_once_with()
        cleanup.assert_called_once_with()
        scheduler.start.assert_called_once_with()
        scheduler.shutdown.assert_called_once_with()
