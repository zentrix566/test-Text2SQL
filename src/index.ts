import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from '@modelcontextprotocol/sdk/types.js';
import mysql from 'mysql2/promise';
import pg from 'pg';

const DB_TYPE = process.env.DB_TYPE || 'mysql';

const DB_CONFIG = {
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT || (DB_TYPE === 'postgres' ? '5432' : '3306')),
  user: process.env.DB_USER || 'root',
  password: process.env.DB_PASSWORD || 'yj1234',
  database: process.env.DB_NAME || 'text2sql_demo',
  ssl: process.env.DB_SSL === 'true' ? { rejectUnauthorized: false } : undefined,
};

const FORBIDDEN_STATEMENTS = [
  'drop',
  'delete',
  'update',
  'insert',
  'truncate',
  'alter',
  'create',
  'grant',
  'revoke',
  'commit',
  'rollback',
];

function isReadOnlyQuery(sql: string): boolean {
  const normalized = sql.trim().toLowerCase();
  if (!normalized.startsWith('select')) {
    return false;
  }
  for (const keyword of FORBIDDEN_STATEMENTS) {
    if (normalized.includes(keyword)) {
      return false;
    }
  }
  return true;
}

type QueryResult = any[];

abstract class DatabaseClient {
  abstract connect(): Promise<void>;
  abstract close(): Promise<void>;
  abstract query(sql: string): Promise<QueryResult>;
  abstract getTables(): Promise<string[]>;
  abstract getColumns(tableName: string): Promise<any[]>;
}

class MySQLClient implements DatabaseClient {
  private connection: mysql.Connection | null = null;

  async connect() {
    this.connection = await mysql.createConnection(DB_CONFIG);
  }

  async close() {
    if (this.connection) {
      await this.connection.end();
      this.connection = null;
    }
  }

  async query(sql: string): Promise<QueryResult> {
    const [rows] = await this.connection!.query(sql);
    return rows as QueryResult;
  }

  async getTables(): Promise<string[]> {
    const [rows] = await this.connection!.query(
      `SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = ?`,
      [DB_CONFIG.database]
    ) as [mysql.RowDataPacket[], any];
    return rows.map(row => row.TABLE_NAME as string);
  }

  async getColumns(tableName: string): Promise<any[]> {
    const [rows] = await this.connection!.query(
      `SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, IS_NULLABLE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? ORDER BY ORDINAL_POSITION`,
      [DB_CONFIG.database, tableName]
    ) as [mysql.RowDataPacket[], any];
    return rows.map(col => ({
      name: col.COLUMN_NAME,
      type: col.DATA_TYPE,
      nullable: col.IS_NULLABLE === 'YES',
    }));
  }
}

class PostgresClient implements DatabaseClient {
  private pool: pg.Pool | null = null;
  private client: pg.PoolClient | null = null;

  async connect() {
    this.pool = new pg.Pool({
      host: DB_CONFIG.host,
      port: DB_CONFIG.port,
      user: DB_CONFIG.user,
      password: DB_CONFIG.password,
      database: DB_CONFIG.database,
      ssl: DB_CONFIG.ssl,
    });
    this.client = await this.pool.connect();
  }

  async close() {
    if (this.client) {
      this.client.release();
    }
    if (this.pool) {
      await this.pool.end();
    }
  }

  async query(sql: string): Promise<QueryResult> {
    const result = await this.client!.query(sql);
    return result.rows;
  }

  async getTables(): Promise<string[]> {
    const result = await this.client!.query(
      `SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'`
    );
    return result.rows.map(row => row.table_name as string);
  }

  async getColumns(tableName: string): Promise<any[]> {
    const result = await this.client!.query(
      `SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_schema = 'public' AND table_name = $1 ORDER BY ordinal_position`,
      [tableName]
    );
    return result.rows.map(col => ({
      name: col.column_name,
      type: col.data_type,
      nullable: col.is_nullable === 'YES',
    }));
  }
}

class Text2SQLServer {
  private server: Server;
  private db: DatabaseClient | null = null;

  constructor() {
    this.server = new Server(
      {
        name: 'text2sql-mcp-server',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupHandlers();
  }

  private setupHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: 'execute_query',
            description: 'Execute a SELECT SQL query on the database. Only SELECT queries are allowed.',
            inputSchema: {
              type: 'object',
              properties: {
                sql: {
                  type: 'string',
                  description: 'The SELECT SQL query to execute',
                },
              },
              required: ['sql'],
            },
          },
          {
            name: 'get_schema',
            description: 'Get the database schema information (tables and columns)',
            inputSchema: {
              type: 'object',
              properties: {},
            },
          },
        ],
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      switch (request.params.name) {
        case 'execute_query': {
          const sql = request.params.arguments?.sql as string;
          if (!isReadOnlyQuery(sql)) {
            throw new McpError(
              ErrorCode.InvalidParams,
              'Only SELECT queries are allowed. All write operations (drop/delete/update/insert/etc) are forbidden.'
            );
          }
          try {
            const rows = await this.db!.query(sql);
            return {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(rows, null, 2),
                },
              ],
            };
          } catch (error) {
            throw new McpError(
              ErrorCode.InternalError,
              `Query execution failed: ${(error as Error).message}`
            );
          }
        }

        case 'get_schema': {
          try {
            const tables = await this.db!.getTables();
            const schema: any = {};
            for (const tableName of tables) {
              const columns = await this.db!.getColumns(tableName);
              schema[tableName] = columns;
            }

            return {
              content: [
                {
                  type: 'text',
                  text: JSON.stringify(schema, null, 2),
                },
              ],
            };
          } catch (error) {
            throw new McpError(
              ErrorCode.InternalError,
              `Failed to get schema: ${(error as Error).message}`
            );
          }
        }

        default:
          throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${request.params.name}`);
      }
    });
  }

  async connect() {
    if (DB_TYPE === 'postgres' || DB_TYPE === 'supabase') {
      this.db = new PostgresClient();
    } else {
      this.db = new MySQLClient();
    }
    await this.db.connect();
  }

  async run() {
    await this.connect();
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
  }

  async close() {
    if (this.db) {
      await this.db.close();
      this.db = null;
    }
    await this.server.close();
  }
}

const server = new Text2SQLServer();

server.run().catch((error) => {
  console.error('Server error:', error);
  process.exit(1);
});

process.on('SIGINT', async () => {
  await server.close();
  process.exit(0);
});
