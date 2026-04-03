#!/usr/bin/env python3
import os
import json
from queue import Queue
from typing import List, Dict, Any
from flask import Flask, request, Response
from dotenv import load_dotenv
import time

load_dotenv()

# 配置读取
DB_TYPE = os.getenv("DB_TYPE", "mysql")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT_DEFAULT = "5432" if DB_TYPE == "postgres" else "3306"
DB_PORT = int(os.getenv("DB_PORT", DB_PORT_DEFAULT))
DB_USER = os.getenv("DB_USER", "root" if DB_TYPE == "mysql" else "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "text2sql_demo" if DB_TYPE == "mysql" else "postgres")
DB_SSL = os.getenv("DB_SSL", "false").lower() == "true"
PORT = int(os.getenv("PORT", "8000"))

FORBIDDEN_STATEMENTS = [
    "drop", "delete", "update", "insert", "truncate", "alter",
    "create", "grant", "revoke", "commit", "rollback", "execute"
]

def is_read_only_query(sql: str) -> bool:
    normalized = sql.strip().lower()
    if not normalized.startswith("select"):
        return False
    for keyword in FORBIDDEN_STATEMENTS:
        if keyword in normalized:
            return False
    return True

class DatabaseClient:
    def connect(self):
        pass
    def ensure_connection(self):
        pass
    def close(self):
        pass
    def query(self, sql: str) -> List[Dict[str, Any]]:
        pass
    def get_tables(self) -> List[str]:
        pass
    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        pass

class PostgresClient(DatabaseClient):
    import psycopg2
    from psycopg2.extras import RealDictCursor

    def __init__(self):
        self.connection = None

    def connect(self):
        sslmode = "require" if DB_SSL else "disable"
        self.connection = self.psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME,
            sslmode=sslmode
        )

    def ensure_connection(self):
        if self.connection is None or self.connection.closed != 0:
            self.connect()

    def close(self):
        if self.connection:
            self.connection.close()

    def query(self, sql: str) -> List[Dict[str, Any]]:
        self.ensure_connection()
        with self.connection.cursor(cursor_factory=self.RealDictCursor) as cursor:
            cursor.execute(sql)
            return [dict(row) for row in cursor.fetchall()]

    def get_tables(self) -> List[str]:
        self.ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            return [row[0] for row in cursor.fetchall()]

    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        self.ensure_connection()
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            return [{
                "name": row[0],
                "type": row[1],
                "nullable": row[2] == "YES"
            } for row in cursor.fetchall()]

class MySQLClient(DatabaseClient):
    import mysql.connector

    def __init__(self):
        self.connection = None

    def connect(self):
        self.connection = self.mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )

    def ensure_connection(self):
        if self.connection is None or not self.connection.is_connected():
            self.connect()

    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()

    def query(self, sql: str) -> List[Dict[str, Any]]:
        self.ensure_connection()
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(sql)
        result = cursor.fetchall()
        cursor.close()
        return result

    def get_tables(self) -> List[str]:
        self.ensure_connection()
        cursor = self.connection.cursor()
        cursor.execute(f"SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s", (DB_NAME,))
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return tables

    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        self.ensure_connection()
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """, (DB_NAME, table_name))
        columns = [{
            "name": row[0],
            "type": row[1],
            "nullable": row[2] == "YES"
        } for row in cursor.fetchall()]
        cursor.close()
        return columns

app = Flask(__name__)
sse_queue = Queue()

# 根据 DB_TYPE 创建客户端
if DB_TYPE in ("postgres", "supabase"):
    db = PostgresClient()
else:
    db = MySQLClient()

TOOLS = [
    {
        "name": "execute_query",
        "description": "Execute a SELECT SQL query on the database. Only SELECT queries are allowed. All write operations are forbidden.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "The SELECT SQL query to execute"
                }
            },
            "required": ["sql"]
        }
    },
    {
        "name": "get_schema",
        "description": "Get the database schema information (tables and columns)",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]

def handle_call_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if name == "execute_query":
        sql = args.get("sql", "")
        if not is_read_only_query(sql):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: Only SELECT queries are allowed. All write operations (drop/delete/update/insert/etc) are forbidden."
                    }
                ],
                "isError": True
            }
        try:
            result = db.query(sql)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2, ensure_ascii=False)
                    }
                ]
            }
        except Exception as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Query execution failed: {str(e)}"
                    }
                ],
                "isError": True
            }

    elif name == "get_schema":
        try:
            tables = db.get_tables()
            schema = {table: db.get_columns(table) for table in tables}
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(schema, indent=2, ensure_ascii=False)
                    }
                ]
            }
        except Exception as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Failed to get schema: {str(e)}"
                    }
                ],
                "isError": True
            }

    else:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Unknown tool: {name}"
                }
            ],
            "isError": True
        }

@app.route("/sse", methods=["GET"])
def sse_endpoint():
    scheme = request.scheme
    host = request.host
    endpoint_url = f"{scheme}://{host}/messages"

    local_queue = Queue()
    global sse_queue
    sse_queue = local_queue

    def generate():
        yield f"event: endpoint\ndata: {endpoint_url}\n\n"
        while True:
            if not local_queue.empty():
                message = local_queue.get()
                yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
            yield ": heartbeat\n\n"
            time.sleep(0.1)

    return Response(generate(), content_type="text/event-stream")

@app.route("/messages", methods=["POST"])
def message_endpoint():
    data = request.get_json()
    msg_id = data.get("id")
    method = data.get("method")

    # 通知消息没有 id，不需要响应
    if msg_id is None:
        return "", 200

    response = {
        "jsonrpc": "2.0",
        "id": msg_id,
    }

    if method == "initialize":
        response["result"] = {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "text2sql-mcp-server", "version": "1.0.0"}
        }
    elif method == "tools/list":
        response["result"] = {"tools": TOOLS}
    elif method == "tools/call":
        params = data.get("params", {})
        response["result"] = handle_call_tool(params.get("name"), params.get("arguments", {}))
    else:
        response["error"] = {
            "code": -32601,
            "message": f"Method not found: {method}"
        }

    sse_queue.put(response)
    return "", 200

if __name__ == "__main__":
    try:
        db.connect()
        print(f"✓ Successfully connected to {DB_TYPE} database")
        print(f"✓ MCP SSE server running on http://0.0.0.0:{PORT}")
        print(f"✓ SSE endpoint: http://0.0.0.0:{PORT}/sse")
    except Exception as e:
        print(f"✗ Failed to connect to {DB_TYPE} database: {str(e)}")
        print("Please check your database connection settings in .env")
        exit(1)
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
