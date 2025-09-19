"""Utility helpers for interacting with Neo4j instances.

The service layer keeps connection metadata in PostgreSQL and references a
`secret_id` instead of storing raw passwords.  For the purpose of local
development and automated tests we resolve those secrets from environment
variables using the convention `NEO4J_SECRET_<SECRET_ID>`.  The module provides
helpers to resolve secrets, open drivers and run lightweight connectivity
checks that are re-used across the CRUD operations of the Neo4j connection
service.
"""

from __future__ import annotations

import os
import re
import time
import uuid
from dataclasses import dataclass
from typing import Dict, Any, Optional

from neo4j import GraphDatabase, Driver
from neo4j.exceptions import Neo4jError

from app.utils.exceptions import NotFoundError, ValidationError

# Neo4j database names must start with a letter and only contain alphanumeric
# characters and underscores.  Enforce this early to avoid injection issues
# when the name is interpolated into SHOW/CREATE statements.
_DATABASE_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def validate_database_name(name: str) -> None:
    """Validate Neo4j database names according to Neo4j's naming rules."""

    if not _DATABASE_NAME_PATTERN.match(name):
        raise ValidationError(
            "Neo4j database name must start with a letter and only contain "
            "alphanumeric characters or underscores"
        )


def resolve_secret(secret_id: str) -> str:
    """Resolve the password for a Neo4j connection.

    The application stores only a `secret_id` reference.  To keep the example
    self-contained we look up a matching environment variable:

    * `env:FOO` -> resolves the password from the exact environment variable
      name `FOO`.
    * `bar`     -> resolves from `NEO4J_SECRET_BAR` (case-insensitive suffix).
    """

    if not secret_id:
        raise ValidationError("Secret identifier must be provided")

    if secret_id.startswith("env:"):
        env_var = secret_id.split(":", 1)[1]
    else:
        env_var = f"NEO4J_SECRET_{secret_id.upper()}"

    secret = os.getenv(env_var)
    if secret is None:
        raise NotFoundError(
            f"Neo4j secret '{secret_id}' not found. Set environment variable '{env_var}'."
        )

    return secret


@dataclass(slots=True)
class Neo4jConnectionConfig:
    uri: str
    username: str
    password: str
    database: str


class Neo4jClient:
    """Thin wrapper around the Neo4j Python driver used by the service layer."""

    def __init__(self, config: Neo4jConnectionConfig):
        self._config = config
        self._driver: Optional[Driver] = None

    @property
    def driver(self) -> Driver:
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self._config.uri,
                auth=(self._config.username, self._config.password),
            )
        return self._driver

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    # Context manager helpers -------------------------------------------------
    def __enter__(self) -> "Neo4jClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # pragma: no cover -
        self.close()

    # Connectivity -----------------------------------------------------------
    def verify(self) -> float:
        """Verify connectivity and return latency in milliseconds."""

        start = time.perf_counter()
        self.driver.verify_connectivity()
        with self.driver.session(database=self._config.database) as session:
            session.run("RETURN 1 AS ok").single()
        return (time.perf_counter() - start) * 1000.0

    # Diagnostic helpers -----------------------------------------------------
    def test_read(self) -> Dict[str, Any]:
        start = time.perf_counter()
        with self.driver.session(database=self._config.database) as session:
            record = session.run("RETURN 1 AS result").single()
        latency = (time.perf_counter() - start) * 1000.0
        if not record or record.get("result") != 1:
            raise ValidationError("Unexpected response from Neo4j read test")
        return {"status": "passed", "latency_ms": latency}

    def test_write(self) -> Dict[str, Any]:
        marker = str(uuid.uuid4())
        start = time.perf_counter()
        with self.driver.session(database=self._config.database) as session:
            session.execute_write(self._write_probe, marker)
        latency = (time.perf_counter() - start) * 1000.0
        return {"status": "passed", "latency_ms": latency}

    def _write_probe(self, tx, marker: str) -> None:
        tx.run(
            "MERGE (n:__GraphLabConnectionTest {marker: $marker}) RETURN n.marker",
            marker=marker,
        ).single()
        tx.run(
            "MATCH (n:__GraphLabConnectionTest {marker: $marker}) DETACH DELETE n",
            marker=marker,
        )

    def list_procedures(self, limit: int = 5) -> Dict[str, Any]:
        start = time.perf_counter()
        sanitized_limit = max(1, min(int(limit), 50))
        query = (
            "SHOW PROCEDURES YIELD name, signature "
            f"RETURN name, signature ORDER BY name ASC LIMIT {sanitized_limit}"
        )
        with self.driver.session(database=self._config.database) as session:
            records = session.run(query)
            procedures = [
                {"name": record.get("name"), "signature": record.get("signature")}
                for record in records
            ]
        latency = (time.perf_counter() - start) * 1000.0
        return {
            "status": "passed" if procedures else "no_procedures",
            "procedures_found": len(procedures),
            "latency_ms": latency,
            "sample": procedures,
        }

    def gather_health(self) -> Dict[str, Any]:
        """Collect lightweight health information about the instance."""

        health: Dict[str, Any] = {}

        # Connectivity + version (agent string looks like "Neo4j/5.18.0")
        latency = self.verify()
        health["latency_ms"] = latency

        try:
            server_info = self.driver.get_server_info()
            agent = getattr(server_info, "agent", None)
            if agent and "/" in agent:
                health["neo4j_version"] = agent.split("/", 1)[1]
            elif agent:
                health["neo4j_version"] = agent
        except Neo4jError:
            # Version lookup is best-effort; ignore failures.
            pass

        # Database status from the system database (best effort).
        try:
            with self.driver.session(database="system") as session:
                records = session.run("SHOW DATABASES")
                for record in records:
                    if record.get("name") == self._config.database:
                        health["database_status"] = record.get("currentStatus") or record.get("status")
                        break
        except Neo4jError:
            pass

        return health


def build_client(uri: str, username: str, secret_id: str, database: str) -> Neo4jClient:
    """Factory used by services to construct a ready-to-use client."""

    validate_database_name(database)
    password = resolve_secret(secret_id)
    config = Neo4jConnectionConfig(uri=uri, username=username, password=password, database=database)
    return Neo4jClient(config)
