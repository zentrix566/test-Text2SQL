#!/usr/bin/env python3
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
from mcp.server import Server
from mcp.types import Tool, CallToolRequest, ListToolsRequest
from mcp.server.stdio import stdio_server
from dotenv import load_dotenv

print(f"Current working directory: {os.getcwd()}")
print(f".env file exists: {os.path.exists('.env')}")
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        print(f".env content (masking passwords):")
        for line in f:
            if line.strip() and not line.startswith('#'):
                key = line.split('=')[0].strip()
                print(f"{key}=***")

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_SSL = os.getenv("DB_SSL", "false").lower() == "true"

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

    def close(self):
        if self.connection:
            self.connection.close()

    def query(self, sql: str) -> List[Dict[str, Any]]:
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()
            return [dict(row) for row in result]

    def get_tables(self) -> List[str]:
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            return [row[0] for row in cursor.fetchall()]

    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
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

server = Server("text2sql-mcp-server")
db: Optional[PostgresClient] = None

@server.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="execute_query",
            description="Execute a SELECT SQL query on the database. Only SELECT queries are allowed. All write operations are forbidden.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "The SELECT SQL query to execute"
                    }
                },
                "required": ["sql"]
            }
        ),
        Tool(
            name="get_schema",
            description="Get the database schema information (tables and columns)",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def call_tool(request: CallToolRequest):
    global db
    name = request.name
    args = request.arguments or {}

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

async def main():
    global db
    db = PostgresClient()
    db.connect()
    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
