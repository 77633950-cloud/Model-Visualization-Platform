# 模型运转可视化平台 V1

实时（3-5 秒）查看大模型 API 运行状态的可观测性平台。左侧对话调试，右侧实时监控，首版单机 Docker 即可部署。

## 功能

- **API 网关代理**：代理上游 LLM 接口（`chat/completions`、`responses`），在请求/响应两侧采集事件
- **秒级聚合**：进程内事件总线 + 异步 worker，将原始请求聚合为秒级指标
- **实时推送**：WebSocket 每 3-5 秒推送窗口指标与模型健康状态
- **全局健康看板**：QPS、成功率、P50/P95 延迟、错误率、模型可用性
- **趋势与回溯**：5/15/60 分钟滚动趋势，数据保留 7 天
- **错误分析**：错误类型 TopN、最近异常请求列表
- **对话调试**：页面左侧直接填写 API Key 发起对话，右侧实时观测
- 默认上游：**智谱 AI**（`glm-4-flash` 完全免费）

## 目录结构

```
model-viz-platform/
├── backend/                 # Python + FastAPI 单体后端
│   ├── app/
│   │   ├── api/             # 指标查询 API
│   │   ├── db/              # 数据库连接
│   │   ├── models/          # ORM 模型与 Pydantic 结构
│   │   ├── proxy/           # API 网关代理层
│   │   ├── services/        # 事件总线与 WebSocket 管理
│   │   ├── config.py        # 配置（环境变量）
│   │   └── main.py          # 应用入口
│   ├── tests/               # 后端测试
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                # React + Vite 前端
│   ├── src/
│   │   ├── components/      # 看板与对话组件
│   │   ├── App.jsx
│   │   ├── api.js
│   │   └── useWebSocket.js
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.js       # 固定端口 5111，/api /proxy /ws 代理到 8000
├── docker-compose.yml       # 单机部署（后端 8000 / 前端 5111）
├── .env.example             # 环境变量模板
└── README.md
```

## 本地开发运行

### 1. 后端（端口 8000）

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

可选：复制 `.env.example` 为 `backend/.env` 并填入 API Key（也可在页面上填写）。

### 2. 前端（端口 5111）

```bash
cd frontend
npm install
npm run dev
```

打开 http://localhost:5111 ，点击左侧「配置 Key」填入智谱 AI API Key 后即可对话。

## Docker 部署

```bash
cp .env.example .env   # 编辑填入 UPSTREAM_API_KEY
docker compose up --build -d
```

- 前端：http://localhost:5111
- 后端 API 文档：http://localhost:8000/docs

## 接口一览

| 接口 | 说明 |
|------|------|
| `POST /proxy/v1/chat/completions` | 代理聊天补全 |
| `POST /proxy/v1/responses` | 代理响应接口 |
| `GET /api/metrics/overview` | 概览指标 |
| `GET /api/metrics/timeseries` | 时间序列（支持 model 筛选） |
| `GET /api/errors/top` | 错误类型 TopN |
| `GET /api/errors/recent` | 最近错误请求 |
| `WS /ws/status` | 实时指标推送 |
| `GET /health` | 健康检查 |

## 获取免费 API Key

1. 访问 https://open.bigmodel.cn 注册
2. 控制台 → API Keys → 创建 Key
3. 在页面「配置 Key」中粘贴保存（仅存浏览器本地）

## 技术栈

- 后端：FastAPI、httpx、SQLAlchemy（async）+ SQLite、APScheduler、websockets
- 前端：React、Vite、Recharts
