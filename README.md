<a name="readme-top"></a>

<h2 align="center">
    <a href="https://www.onyx.app/?utm_source=onyx_repo&utm_medium=github&utm_campaign=readme"> <img width="50%" src="https://github.com/onyx-dot-app/onyx/blob/logo/OnyxLogoCropped.jpg?raw=true" /></a>
</h2>

<p align="center">
    <a href="https://discord.gg/TDJ59cGV2X" target="_blank">
        <img src="https://img.shields.io/badge/discord-join-blue.svg?logo=discord&logoColor=white" alt="Discord" />
    </a>
    <a href="https://docs.onyx.app/?utm_source=onyx_repo&utm_medium=github&utm_campaign=readme" target="_blank">
        <img src="https://img.shields.io/badge/docs-view-blue" alt="Documentation" />
    </a>
    <a href="https://www.onyx.app/?utm_source=onyx_repo&utm_medium=github&utm_campaign=readme" target="_blank">
        <img src="https://img.shields.io/website?url=https://www.onyx.app&up_message=visit&up_color=blue" alt="Website" />
    </a>
    <a href="https://github.com/onyx-dot-app/onyx/blob/main/LICENSE" target="_blank">
        <img src="https://img.shields.io/static/v1?label=license&message=MIT&color=blue" alt="License" />
    </a>
</p>

<p align="center">
  <a href="https://trendshift.io/repositories/12516" target="_blank">
    <img src="https://trendshift.io/api/badge/repositories/12516" alt="onyx-dot-app/onyx | Trendshift" style="width: 250px; height: 55px;" />
  </a>
</p>

# Loge - The context layer powered by all your apps

> Private fork of [Onyx](https://github.com/onyx-dot-app/onyx) rebranded as Loge.
> Full feature code lives under `backend/loge/` and `web/src/loge/` and remains
> under the Onyx Enterprise License (see root `LICENSE`). MIT applies to the rest.
>
> For local unlock of paid features, use `backend/scripts/seed_dev_license.py`
> (development only).

**Loge** is the knowledge/context layer for your team and AI agents.

Loge connects to your applications to index and surface knowledge from 50+
sources while protecting data sovereignty through self-hosted deployments.

Beyond search, Loge enables LLMs with advanced features like web search,
sandboxes, skills, and more.


> [!TIP]
> Deploy with a single command:
> ```
> curl -fsSL https://onyx.app/install_onyx.sh | bash
> ```

![Onyx chat answering a question about use cases](docs/assets/onyx-chat-use-cases.png)

---

## Local development (Loge)

Run Docker dependencies, then four processes in separate terminals. Use the
repo-root `.venv` and `.vscode/.env` for the Python services.

### 1. One-time setup

```bash
# From the repo root
uv sync --frozen
cp .vscode/env_template.txt .vscode/.env   # if you do not have .vscode/.env yet
# Edit .vscode/.env: set GEN_AI_API_KEY (or other LLM keys) as needed.
# Keep MODEL_SERVER_PORT=9001 in sync with the model server command below.

cd web && bun install && cd ..
```

Start Postgres, Redis, OpenSearch, and object storage (MinIO):

```bash
cd deployment/docker_compose
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d \
  relational_db cache object-store opensearch
cd ../..
```

Optional (dev license unlock): `uv run --directory backend python scripts/seed_dev_license.py`

### 2. Run the four services

Use **four terminals**. Keep them running.

**Model server** (embeddings / NLP — port **9001**):

```bash
cd backend
uv run uvicorn model_server.main:app --reload --port 9001
```

**API backend** (port **8080**):

```bash
uv run --env-file .vscode/.env --directory backend \
  uvicorn onyx.main:app --reload --port 8080
```

**Background jobs** (indexing, Celery workers — required for connectors):

```bash
uv run --env-file .vscode/.env --directory backend \
  python ./scripts/dev_run_background_jobs.py
```

**Frontend** (port **3000**; proxies `/api` to the backend):

```bash
cd web
bun run dev
```

Open the app at [http://localhost:3000](http://localhost:3000). Call the API
through the frontend (for example `http://localhost:3000/api/...`), not
directly on `:8080`, unless you know you need to.

| Service        | Port  | Notes                                      |
|----------------|-------|--------------------------------------------|
| Frontend       | 3000  | Main UI                                    |
| API            | 8080  | FastAPI                                    |
| Model server   | 9001  | Must match `MODEL_SERVER_PORT` in `.env`   |
| OpenSearch     | 9200  | Document / vector index                    |
| MinIO          | 9004  | File store (`S3_ENDPOINT_URL`)             |
| Postgres       | 5432  | Default local password often `password`    |

If indexing fails with `Connection reset by peer` on embed calls, check that
background jobs use `MODEL_SERVER_PORT=9001` and that nothing else (for example
php-fpm) is bound to port **9000**.

For deeper contribution setup, see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## How does Onyx work

Onyx creates a representation of knowledge across all connected sources. It pulls data along with metadata, permissions, etc. and ingests it so that the information is easily accessible for downstream use cases.

Compared to MCP based searches and index-free approaches, Onyx provides a more reliable, low latency, and low cost context for any given query whether it's a simple keyword query or a complex research task.

Instead of an agent coordinating and iteratively searching dozens of MCP and burning many thousands of tokens, Onyx fetches the context across its internal representation instantly and filters down to only the most relevant ground truth documents.

## ⭐ Features

- **🔍 Agentic RAG:** Get best in class search and answer quality based on hybrid index + a custom agent harness tuned for information retrieval.
- **🔬 Deep Research:** Get in depth reports with a multi-step research flow.
- **🤖 Custom Agents:** Build AI Agents with unique subsets of knowledge, custom instructions, and the ability to take actions.
- **🌍 Web Search:** Augment internal knowledge with live web search.
  - Supports Serper, Google PSE, Brave, SearXNG, and others.
  - Comes with an in house web crawler and support for Firecrawl/Exa.
- **▶️ External Actions & MCP:** Let Onyx agents take actions in external applications to complete tasks end to end.
- **💻 Secure Sandbox:** Execute code and work with intermediate artifacts in a sandbox for complex workflows.
- **📄 Artifacts:** Generate documents, graphics, and other downloadable artifacts.
- **🎙️ Voice Mode:** Interact with Onyx via text-to-speech and speech-to-text.

Onyx supports all major LLM providers, both self-hosted (like Ollama, LiteLLM, vLLM, etc.) and proprietary (like Anthropic, OpenAI, Gemini, etc.).

To learn more - check out our [docs](https://docs.onyx.app/welcome?utm_source=onyx_repo&utm_medium=github&utm_campaign=readme)!

---

## Security and Data Processing

![Onyx architecture: everything runs inside your environment](docs/assets/architecture.png)

When connecting up your organization's knowledge, it's critical that this sensitive IP is not leaked to the wrong parties both external and internal.

Onyx provides an air-gappable, self-hosted deployment where the document index, database, and processing all happen within a self-contained set of services.

You can also choose a trusted embedding model and LLM provider (both of which can also run locally).

---

## Access Onyx from anywhere

The same security and fine grained permissions apply no matter where the question comes from.

- **Web and desktop app** - Ask questions, interface with Onyx AI agents, and everything else in the feature list above.
- **Slack and Discord bot** - Get answers directly in Slack or Discord from a bot connected to your org's knowledge.
- **MCP server** - Point Claude Code, Open Code, Codex, or any MCP client at Onyx. Your AI agents get company context with the same access controls as the person running them.
- **Chrome extension** - Query Onyx from any tab with context from the page, directly in Chrome.
- **Embeddable Widget** - Easily add Onyx functionality to your app or website.

---

## 🚀 Deployment Modes

> Onyx supports deployments in Docker, Kubernetes, Helm/Terraform and provides guides for major cloud providers.
> Detailed deployment guides found [here](https://docs.onyx.app/deployment/overview).

Onyx supports two separate deployment options: standard and lite.

#### Standard Onyx

The complete feature set of Onyx which is recommended for serious users and larger teams. Additional components not included in Lite mode:
- Vector + Keyword index for RAG.
- Background containers to run job queues and workers for syncing knowledge from connectors.
- AI model inference servers to run deep learning models used during indexing and inference.
- Performance optimizations for large scale use via in memory cache (Redis) and blob store (MinIO).

#### Onyx Lite

The Lite mode can be thought of as a lightweight AI Chat UI. It requires less resources (under 1GB memory) and runs a less complex stack but is not capable of indexing documents.
It is great for users who want to test out the Onyx UI quickly or for teams who are only interested in the Chat UI and Agents functionalities.

> [!TIP]  
> **To try Onyx for free without deploying, visit [Onyx Cloud](https://cloud.onyx.app/signup?utm_source=onyx_repo&utm_medium=github&utm_campaign=readme)**.

---

## 🏢 Onyx for Enterprise

Onyx is built for teams of all sizes, from individual users to the largest global enterprises:
- 👥 Collaboration: Share chats and agents with other members of your organization.
- 🔐 Single Sign On: SSO via Google OAuth, OIDC, or SAML. Group syncing and user provisioning via SCIM.
- 🛡️ Role Based Access Control: RBAC for sensitive resources like access to agents, actions, etc.
- 📊 Analytics: Usage graphs broken down by teams, LLMs, or agents.
- 🕵️ Query History: Audit usage to ensure safe adoption of AI in your organization.
- 💻 Custom code: Run custom code to remove PII, reject sensitive queries, or to run custom analysis.
- 🎨 Whitelabeling: Customize the look and feel of Onyx with custom naming, icons, banners, and more.

## 📚 Licensing

There are two editions of Onyx:

- Onyx Community Edition (CE) is available freely under the MIT license and covers all of the core features for RAG, AI Chat, Agents, and Actions.
- Onyx Enterprise Edition (EE) includes extra features that are primarily useful for larger organizations.

For feature details, check out [our website](https://www.onyx.app/pricing?utm_source=onyx_repo&utm_medium=github&utm_campaign=readme).

## 👪 Community

Join our open source community on **[Discord](https://discord.gg/TDJ59cGV2X)**!

## 💡 Contributing

Looking to contribute? Please check out the [Contribution Guide](CONTRIBUTING.md) for more details.
