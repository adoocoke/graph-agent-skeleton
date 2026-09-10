# Graph Agent 骨架（最小可运行版）

纯 Python 3 标准库实现的**内存幸存者知识图谱 Agent**骨架，对应 GCP 实验中 Spanner Graph + ADK + Vertex AI Search 的本地玩具版。

无第三方依赖（无 ML、无 GCP SDK），开箱即跑。

## 快速开始

```bash
cd /workspace/graph-agent-skeleton

# 本机若无 python 命令，请用 python3（下同）
# 方式 1：模块直接运行
python3 -m graph_agent "Who can help with injuries?"

# 方式 2：脚本（自动选择 python3/python）
./run.sh "Who can help with injuries?"

# 混合检索示例（地点 + 概念 → hybrid / RRF）
python3 -m graph_agent "mountain healing for burns"

# Fan-out Join 救援匹配演示
python3 -m graph_agent --fanout "burns" --biome mountain

# JSON 输出
python3 -m graph_agent --json "Who has First Aid?"
```

可选安装（可编辑模式）：

```bash
pip install -e .
graph-agent "Who can help with injuries?"
```

## 项目结构

```
graph-agent-skeleton/
├── graph_agent/
│   ├── __init__.py
│   ├── __main__.py      # CLI 入口
│   ├── graph.py         # 内存图：节点 / 边 / 查询辅助
│   ├── seed.py          # 种子数据（Elena、First Aid、山脉/FOSSILIZED、烧伤等）
│   ├── search.py        # keyword / semantic(BoW cosine) / hybrid(RRF)
│   └── router.py        # 启发式路由 + fanout_join_router
├── pyproject.toml
├── run.sh
└── README.md
```

## 图谱模型

| 节点类型 | 含义 |
|---------|------|
| Survivor | 幸存者（如 Dr. Elena Frost） |
| Skill | 技能（Medical Training、First Aid…） |
| Need | 需求（Burns、Bleeding…，含 urgency） |
| Biome | 生物群系（Mountains、FOSSILIZED…） |

| 边关系 | 含义 |
|--------|------|
| `has_skill` | Survivor → Skill |
| `in_biome` | Survivor → Biome |
| `has_need` | Survivor → Need |
| `skill_treats_need` | Skill → Need |

种子亮点：

- **Dr. Elena Frost** + **Medical Training**
- **Kai Rivera / Jon Hale / Mira Chen** 具备 **First Aid**
- **Jon / Rio** 位于 **Mountains / FOSSILIZED**
- 紧急需求：**Burns**（critical）等

## 工具与路由

| 工具 | 实现 | 何时选用 |
|------|------|----------|
| `keyword_search` | 子串 / token 精确过滤 | 精确过滤、姓名、边类型线索 |
| `semantic_search` | 词袋余弦相似度（BoW cosine） | 概念性问题（injuries、healing…） |
| `hybrid_search` | 关键词 + 语义结果做 **Reciprocal Rank Fusion (RRF)** | 地点 + 概念同时出现 |

路由器启发式（`router.choose_tool`）：

1. **概念向** → `semantic_search`
2. **地点 + 概念** → `hybrid_search`
3. **精确过滤** → `keyword_search`

对「谁能帮忙治疗伤势」类问题，路由结果会额外跑一遍 **fan-out join**：

```
Need ← skill_treats_need ← Skill ← has_skill ← Survivor
（可选）Survivor → in_biome 过滤山脉等
```

## 与 GCP Lab 的对应关系

本骨架是本地最小替代，方便理解实验链路，**不是**云端实现本身：

| 本仓库（本地） | GCP Lab 组件 | 说明 |
|----------------|--------------|------|
| `SurvivorGraph` 内存图 | **Spanner Graph**（或属性图模型） | 生产环境用 Spanner 存节点/边，用 GQL/SQL 做多跳查询 |
| `keyword_search` | Spanner / 结构化过滤 + **Vertex AI Search** 关键词通道 | 精确属性、ID、关系过滤 |
| `semantic_search`（BoW cosine） | **Vertex AI Embeddings + Vector Search** | 真实环境用文本嵌入向量，而非词袋 |
| `hybrid_search` + RRF | Vertex AI Search **Hybrid / RRF** 或自建融合 | 关键词排序与向量排序融合 |
| `AgentRouter` 启发式 | **ADK（Agent Development Kit）** 工具选择 / 规划 | Lab 中由 LLM Agent 选 tool、填参、多步编排 |
| `fanout_join_router` | Spanner 多跳图查询 + Agent 编排 | 救援匹配：需求→技能→人→地点 |
| CLI `python -m graph_agent` | Cloud Run / Agent Engine 上的 Agent 服务入口 | 本地 REPL vs 云端 API |

建议学习路径：

1. 先在本仓库跑通三种检索与路由，理解「图 + 工具 + 路由」。
2. 把 `seed.py` 中的节点/边映射到 Spanner Graph schema。
3. 用 Vertex Embedding 替换 `search.semantic_search` 的 BoW。
4. 用 ADK 把三个 search tool + fanout join 注册成 Agent tools，由模型选型。

## 设计取舍

- **只依赖标准库**：便于在受限环境快速演示。
- **语义检索是玩具级**：token BoW cosine 仅用于讲清「向量检索」接口形状。
- **路由是规则而非 LLM**：对应 ADK 里「先有工具、再让模型选型」的教学顺序。

## 许可证

MIT
