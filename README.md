
> <small>An AI-powered system that autonomously verifies building designs against regulatory codes using agentic AI and dynamic tool generation.</small>

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-181717?logo=github)](https://github.com/blau1234/AdaptiveACC)


<h4>Overview</h4>

<small>The ACC System transforms building code compliance checking from a manual, time-consuming process into an automated workflow powered by agentic AI. By leveraging Large Language Models (LLMs) with the ReAct (Reasoning + Acting) framework, the system autonomously interprets building regulations, explores IFC (Industry Foundation Classes) building models, and generates specialized tools on-demand to verify compliance.</small>

<small>**Key Innovation**: Instead of requiring pre-programmed rules for every regulation, the system uses an autonomous agent that can reason about requirements, discover what data it needs, select or create custom analysis tools, and adapt its strategy based on findings - all without human intervention.</small>

---

<h4>System Architecture</h4>

<p align="center">
  <img src="images/architecture.png" alt="System Architecture" width="80%">
</p>

<small>The system implements a **single-agent ReAct architecture** where one autonomous agent orchestrates the entire compliance checking workflow by dynamically selecting and invoking specialized tools. The agent maintains global state through a shared context and can create new tools on-demand when existing capabilities are insufficient.</small>

<h5>Compliance Agent</h5>
<small>Autonomous reasoning engine (`agents/compliance_agent.py`) that runs ReAct loops: Thought (analyze situation) → Action (select tool) → Observation (process result). Each iteration is logged in SharedContext for complete audit trail.</small>

<h5>Agent Tools (7 tools)</h5>
- <small>**Subgoal Management** (2): `generate_subgoals`, `review_and_update_subgoals` - Dynamic planning and progress tracking</small>
- <small>**IFC Tool Lifecycle** (5): `select_ifc_tool`, `create_ifc_tool`, `execute_ifc_tool`, `fix_ifc_tool`, `store_ifc_tool` - Manage tool creation, testing, and persistence</small>

<h5>IFC Tools (Hierarchical)</h5>
- <small>**ifc_tool_utils**: Atomic operations (IfcOpenShell wrappers)</small>
- <small>**Core Tools** (32 pre-built): Generic exploratory tools, quantification, aggregation, topological operations</small>
- <small>**Generated Tools**: Domain-specific tools dynamically created by agent</small>

<h5>Global Components (Singleton Pattern)</h5>
- <small>**SharedContext**: Global state management - stores session info, subgoals, agent history, search summaries, compliance results</small>
- <small>**ToolRegistry**: Auto-discovery and schema generation for all tools</small>
- <small>**VectorDatabase**: ChromaDB for semantic tool search</small>

---

<h4>How It Works: Three-Phase Workflow</h4>

<h5>Phase 1: Task Decomposition</h5>
<small>The agent starts by interpret the regulation (use `search_and_summarize` when necessary), disambiguating technical terms to IFC concepts, then generating executable subgoals that follow a logical flow: Identification → Data Collection → Analysis → Verification.</small>

<h5>Phase 2: Adaptive Execution</h5>
<small>The agent executes subgoals using ReAct loops (Thought → Action → Observation). For each step, it searches for existing IFC tools and executes them. The agent can dynamically adjust its plan by reviewing progress and updating subgoals based on execution results.</small>

**ReAct Example:**
```
THOUGHT: "I need to find all walls. Let me search for existing IFC tools."
ACTION: select_ifc_tool(description="retrieve all wall elements")
OBSERVATION: Found tool "get_elements_by_type"

THOUGHT: "Perfect. I'll execute this tool."
ACTION: execute_ifc_tool(tool_name="get_elements_by_type", parameters={"element_type": "IfcWall"})
OBSERVATION: Success - Found 245 wall elements
```

<small>When no suitable tool exists, the agent creates one via `create_ifc_tool` → sandbox test with `execute_ifc_tool` → fix errors with `fix_ifc_tool` → persist with `store_ifc_tool`.</small>

<h5>Phase 3: Result Generation</h5>
<small>When the agent stops calling tools, the system automatically generates a compliance report with pass/fail status, evidence from successful tool executions, list of violations, and recommendations.</small>

---

<h4>Technical Stack</h4>

<small>
<table>
  <thead>
    <tr>
      <th>Layer</th>
      <th>Technologies</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>AI/ML</strong></td>
      <td>OpenAI GPT-4 / DeepSeek / <strong>Gemini</strong>, Instructor (structured outputs), ReAct framework</td>
    </tr>
    <tr>
      <td><strong>Backend</strong></td>
      <td>FastAPI, Pydantic models, Python 3.8+</td>
    </tr>
    <tr>
      <td><strong>BIM Processing</strong></td>
      <td>IfcOpenShell</td>
    </tr>
    <tr>
      <td><strong>Storage</strong></td>
      <td>ChromaDB (vector database), File system (tool persistence)</td>
    </tr>
    <tr>
      <td><strong>Frontend</strong></td>
      <td>Three.js (3D IFC visualization)</td>
    </tr>
    <tr>
      <td><strong>Observability</strong></td>
      <td>Phoenix (Arize) for distributed tracing, custom execution logging</td>
    </tr>
  </tbody>
</table>
</small>

---

<h4>Quick Start</h4>

<h5>Prerequisites</h5>

- <small>Python 3.8+</small>
- <small>Node.js 16+ (optional, for frontend development)</small>

<h5>Installation</h5>

```bash

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your API keys:
# - OPENAI_API_KEY (for all LLM operations: OpenAI, DeepSeek, or Gemini)
# - EMBEDDING_API_KEY
# - PHOENIX_API_KEY (optional, for tracing)

# For Gemini API setup, see GEMINI_SETUP_GUIDE.md
```

<h5>Build Frontend (Optional)</h5>

<small>If you want to use the 3D IFC viewer interface:</small>

```bash
cd frontend
npm install
npm run build
cd ..
```

<small>This builds the Three.js-based frontend and outputs to `templates/`. Skip this if you only need API access.</small>

<h5>Run the System</h5>

```bash
# Start FastAPI server
python main.py

# Access web interface at http://localhost:8000
```
