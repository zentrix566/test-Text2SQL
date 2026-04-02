# Text2SQL MCP Server

Text2SQL MCP 服务端，支持 MySQL 和 PostgreSQL (Supabase)，只允许 SELECT 查询，禁止所有写操作。

可以在 Dify 中集成，让 LLM 自然语言查询数据库。

## 功能

- ✅ 只允许 `SELECT` 查询
- ✅ 禁止所有写操作 (`drop/delete/update/insert/truncate/alter/create/grant` 等)
- ✅ 提供两个工具：
  - `get_schema` - 获取数据库 schema (表和列信息)
  - `execute_query` - 执行 SELECT 查询
- ✅ 支持 MySQL 和 PostgreSQL (Supabase)
- ✅ 支持 STDIO 模式 和 HTTP 模式

## 快速开始

### 1. 初始化数据库

**MySQL:**
```sql
source init.sql
```

**PostgreSQL / Supabase:**
在 Supabase SQL Editor 中执行 `init-postgres.sql`

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入你的数据库信息
```

配置示例 (Supabase):
```env
DB_TYPE=postgres
DB_HOST=aws-xxx.pooler.supabase.com
DB_PORT=6543
DB_USER=postgres.xxxx
DB_PASSWORD=your-password
DB_NAME=postgres
DB_SSL=true
```

### 3. 运行

#### 方式一：STDIO 模式 (本地开发，Dify STDIO 配置)

TypeScript 版本:
```bash
npm install
npm run dev
```

Dify 中配置命令:
```
npx tsx /path/to/test-Text2SQL/src/index.ts
```

#### 方式二：HTTP 模式 (服务器部署，Dify HTTP 配置)

Python 版本:
```bash
pip install -r requirements.txt
python server_http.py
```

后台运行 (gunicorn):
```bash
gunicorn -w 4 -b 0.0.0.0:8000 server_http:app -D
```

Dify 中配置 URL:
```
http://your-server-ip:8000
```

## 在 Dify 中集成

1. 打开 Dify → 工具 → MCP → 添加 MCP 服务
2. 选择 HTTP 模式，填入你的服务 URL
3. 保存，就可以在 Agent 中使用了

## 安全

- `.env` 文件已经在 `.gitignore` 中，不会提交密码到 git
- 只允许 SELECT 查询，完全只读，不会修改数据库

## 项目结构

```
├── src/index.ts          # TypeScript STDIO 版本
├── server_http.py        # Python HTTP 版本 (服务器部署)
├── init.sql              # MySQL 初始化
├── init-postgres.sql     # PostgreSQL 初始化
├── package.json          # Node 依赖
├── requirements.txt      # Python 依赖
├── .env.example          # 环境变量示例
└── .gitignore           # 排除敏感文件
```

## License

MIT
