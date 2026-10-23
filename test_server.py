import os
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy.exc import OperationalError

import server


class PrototypeTests(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        server.get_engine.cache_clear()

    def tearDown(self):
        server.get_engine.cache_clear()

    def test_home_does_not_connect_to_database(self):
        with patch("server.get_engine") as get_engine:
            response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        get_engine.assert_not_called()

    def test_missing_configuration_fails_safely(self):
        with patch.dict(os.environ, {}, clear=True):
            response = self.client.get("/db-check")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json, {"database": "unavailable"})

    def test_query_uses_parameters_and_closes_connection(self):
        engine = MagicMock()
        connection = engine.connect.return_value.__enter__.return_value
        connection.execute.return_value.scalar_one.side_effect = [1, True]
        with patch("server.get_engine", return_value=engine):
            response = self.client.get("/db-check")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["select_1"], 1)
        self.assertTrue(response.json["assigned_schema_accessible"])
        query, parameters = connection.execute.call_args_list[0].args
        self.assertEqual(str(query), "SELECT :value")
        self.assertEqual(parameters, {"value": 1})
        engine.connect.return_value.__exit__.assert_called_once()

    def test_database_error_does_not_expose_exception_details(self):
        engine = MagicMock()
        engine.connect.side_effect = OperationalError(
            "SELECT 1", {}, Exception("sensitive test-only connection detail")
        )
        with patch("server.get_engine", return_value=engine):
            with self.assertLogs(server.app.logger, level="WARNING") as logs:
                response = self.client.get("/db-check")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json, {"database": "unavailable"})
        self.assertNotIn("sensitive test-only", "\n".join(logs.output))

    def test_engine_configuration_and_special_characters(self):
        settings = {"DB_USER": "test_user", "DB_PASSWORD": "test-only:@/?"}
        with patch.dict(os.environ, settings, clear=True):
            with patch("server.create_engine") as create_engine:
                server.get_engine()
                server.get_engine()
        create_engine.assert_called_once()
        url = create_engine.call_args.args[0]
        self.assertEqual(url.password, settings["DB_PASSWORD"])
        self.assertEqual(url.host, "127.0.0.1")
        self.assertEqual(url.port, 5454)
        self.assertEqual(url.database, "proj1part2")
        options = create_engine.call_args.kwargs
        self.assertEqual(options["pool_size"], 1)
        self.assertEqual(options["max_overflow"], 0)
        self.assertTrue(options["pool_pre_ping"])
        self.assertEqual(options["connect_args"]["connect_timeout"], 5)


if __name__ == "__main__":
    unittest.main()
