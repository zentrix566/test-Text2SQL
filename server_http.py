#!/usr/bin/env python3
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
from flask import Flask, request, jsonify, Response
from dotenv import load_dotenv
import time

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "postgres")
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

class PostgresClient:
    def __init__(self):
        self.connection = None

    def connect(self):
        sslmode = "require" if DB_SSL else "disable"
        self.connection = psycopg2.connect(
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
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()
            return [dict(row) for row in result]

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
            columns = []
            for row in cursor.fetchall():
                columns.append({
                    "name": row[0],
                    "type": row[1],
                    "nullable": row[2] == "YES"
                })
            return columns

app = Flask(__name__)
db = PostgresClient()

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
            schema = {}
            for table in tables:
                schema[table] = db.get_columns(table)
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

@app.route('/sse', methods=['GET'])
def sse_endpoint():
    msg_id = request.args.get('id', '1')
    
    scheme = request.scheme
    host = request.host
    endpoint_url = f"{scheme}://{host}/messages"
    
    def generate():
        yield f"event: endpoint\ndata: {endpoint_url}\n\n"
        result = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "text2sql-mcp-server",
                    "version": "1.0.0"
                }
            }
        }
        yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n"
        while True:
            yield ": heartbeat\n\n"
            time.sleep(30)
    
    return Response(generate(), content_type='text/event-stream')

@app.route('/messages', methods=['POST'])
def message_endpoint():
    data = request.get_json()
    msg_id = data.get('id')
    method = data.get('method')

    if method == 'tools/list':
        return jsonify({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": TOOLS
            }
        })

    elif method == 'tools/call':
        params = data.get('params', {})
        name = params.get('name')
        args = params.get('arguments', {})
        result = handle_call_tool(name, args)
        return jsonify({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result
        })

    else:
        return jsonify({
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        })

if __name__ == "__main__":
    db.connect()
    app.run(host='0.0.0.0', port=PORT, debug=False)