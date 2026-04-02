# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A secure Text2SQL (Natural Language to SQL) server implementing the Model Context Protocol (MCP). Allows LLMs to query databases using natural language while strictly enforcing read-only access. Designed for integration with Dify.

Features:
- Only `SELECT` queries allowed, all write operations blocked
- Supports MySQL and PostgreSQL (including Supabase)
- Two server modes: STDIO (TypeScript) for local development, HTTP (Python Flask) for server deployment
- Provides two MCP tools: `get_schema` (get database schema info) and `execute_query` (execute SELECT queries)

## Commands

### TypeScript (STDIO Mode)
```bash
# Install dependencies
npm install

# Development with auto-reload
npm run dev

# Build for production
npm run build

# Start production build
npm start
```

### Python (HTTP Mode)
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python server_http.py

# Test database connection
python test_connection.py

# Production with gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 server_http:app -D
```

## Architecture

### Dual Implementation
- **src/index.ts** - TypeScript STDIO server using `@modelcontextprotocol/sdk`. Uses stdio transport for local MCP client connections. Supports both MySQL (mysql2) and PostgreSQL (pg).
- **server_http.py** - Python Flask HTTP server with SSE support for remote MCP connections. Designed for server deployment.

### Security Model
1. All SQL queries are validated before execution
2. Only queries starting with `SELECT` are allowed
3. Forbidden keywords (drop, delete, update, insert, truncate, alter, create, grant, etc.) are blocked
4. `.env` file containing database credentials is gitignored

### Database Support
- MySQL via `mysql2` (TypeScript) / `psycopg2-binary` (Python)
- PostgreSQL via `pg` (TypeScript) / `psycopg2-binary` (Python)
- Connection configuration via environment variables in `.env`

## Configuration

Copy `.env.example` to `.env` and set:
- `DB_TYPE` - `mysql` or `postgres`
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` - database connection details
- `DB_SSL` - `true` or `false` (enable for Supabase)

## Database Initialization
- MySQL: `init.sql` - creates sample tables (products, customers, orders, order_items) with demo data
- PostgreSQL/Supabase: `init-postgres.sql` - same schema for PostgreSQL
