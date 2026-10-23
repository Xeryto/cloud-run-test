import os
from functools import lru_cache

from flask import Flask, jsonify
from sqlalchemy import URL, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

app = Flask(__name__)


@lru_cache(maxsize=1)
def get_engine():
    db_url = URL.create(
        "postgresql+psycopg2",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", "5454")),
        database=os.environ.get("DB_NAME", "proj1part2"),
    )
    return create_engine(
        db_url,
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
        pool_timeout=5,
        connect_args={"connect_timeout": 5, "options": "-c statement_timeout=5000"},
    )


@app.route("/")
def home():
    return "<h1>COMS W4111 Cloud Run Test</h1><p>Database prototype: automatic redeployment test.</p>"


@app.route("/db-check")
def database_check():
    try:
        with get_engine().connect() as conn:
            result = conn.execute(text("SELECT :value"), {"value": 1}).scalar_one()
            schema_accessible = conn.execute(
                text(
                    "SELECT EXISTS ("
                    "SELECT 1 FROM pg_namespace "
                    "WHERE nspname = current_user "
                    "AND has_schema_privilege(oid, 'USAGE'))"
                )
            ).scalar_one()
    except (SQLAlchemyError, KeyError, ValueError) as exc:
        # Exception messages can contain connection details; log only the error type.
        app.logger.warning("Database check failed (%s)", type(exc).__name__)
        return jsonify(database="unavailable"), 503

    return jsonify(
        database="ok",
        select_1=result,
        assigned_schema_accessible=bool(schema_accessible),
        revision=os.environ.get("K_REVISION", "local"),
    )
