
> <small>An AI-powered system that autonomously verifies building designs against regulatory codes using agentic AI and dynamic tool generation.</small>

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-181717?logo=github)](https://github.com/blau1234/AdaptiveACC)


<h3>Overview</h3>

<small>The ACC System transforms building code compliance checking from a manual, time-consuming process into an automated workflow powered by agentic AI. By leveraging Large Language Models (LLMs) with the ReAct (Reasoning + Acting) framework, the system autonomously interprets building regulations, explores IFC (Industry Foundation Classes) building models, and generates specialized tools on-demand to verify compliance.</small>

<small><strong>Key Innovation</strong>: Instead of requiring pre-programmed rules for every regulation, the system uses an autonomous agent that can reason about requirements, discover what data it needs, select or create custom analysis tools, and adapt its strategy based on findings - all without human intervention.</small>

---

<h3>System Architecture</h3>

<p align="center">
  <img src="images/architecture.svg" alt="System Architecture" width="80%">
</p>

<small>The system implements a <strong>single-agent ReAct architecture</strong> where one autonomous agent orchestrates the entire compliance checking workflow by dynamically selecting and invoking specialized tools. The agent maintains global state through a shared context and can create new tools on-demand when existing capabilities are insufficient.</small>

<h4>Compliance Agent</h4>
<small>Autonomous reasoning engine (`agents/compliance_agent.py`) that runs ReAct loops: Thought (analyze situation) → Action (select tool) → Observation (process result). Each iteration is logged in SharedContext for complete audit trail.</small>

<h4>Agent Tools </h4>

- <small><strong>Subgoal Management</strong>: `generate_subgoals`, `review_and_update_subgoals` - Dynamic planning and progress tracking</small>
- <small><strong>IFC Tool Lifecycle</strong>: `select_ifc_tool`, `create_ifc_tool`, `execute_ifc_tool`, `fix_ifc_tool`, `store_ifc_tool` - Manage tool creation, testing, and persistence</small>


<h4>IFC Tools</h4>

- <small><strong>ifc_tool_utils</strong>: Atomic operations (IfcOpenShell wrappers)</small>

- <small><strong>Core Tools</strong> (20 pre-built): Generic exploratory tools, quantification, aggregation, topological operations</small>
- <small><strong>Generated Tools</strong>: Domain-specific tools dynamically created by agent</small>

<h4>Global Components</h4>

- <small><strong>SharedContext</strong>: Global state management - stores session info, subgoals, agent history, search summaries, compliance results</small>
- <small><strong>ToolRegistry</strong>: Auto-discovery and schema generation for all tools</small>
- <small><strong>VectorDatabase</strong>: ChromaDB for semantic tool search</small>

---

<h3>How It Works: Three-Phase Workflow</h3>
<p align="center">
  <img src="images/workflow.svg" alt="workflow" width="80%">
</p>

<h4>Phase 1: Task Decomposition</h4>
<small>The agent starts by interpret the regulation, disambiguating technical terms to IFC concepts, then generating executable subgoals that follow a logical flow: Identification → Data Collection → Analysis → Verification.</small>

<h4>Phase 2: Adaptive Execution</h4>
<small>The agent executes subgoals using ReAct loops (Thought → Action → Observation). For each step, it searches for existing IFC tools and executes them. The agent can dynamically adjust its plan by reviewing progress and updating subgoals based on execution results.</small>


<small>When no suitable tool exists, the agent creates one via `create_ifc_tool` → sandbox test with `execute_ifc_tool` → fix errors with `fix_ifc_tool` → persist with `store_ifc_tool`.</small>



---

<h3>Technical Stack</h3>

<table>
  <thead>
    <tr>
      <th><small>Layer</small></th>
      <th><small>Technologies</small></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><small><strong>AI/ML</strong></small></td>
      <td><small>OpenAI GPT-4 / DeepSeek / <strong>Gemini</strong>, Instructor (structured outputs), ReAct framework</small></td>
    </tr>
    <tr>
      <td><small><strong>Backend</strong></small></td>
      <td><small>FastAPI, Pydantic models, Python 3.8+</small></td>
    </tr>
    <tr>
      <td><small><strong>BIM Processing</strong></small></td>
      <td><small>IfcOpenShell</small></td>
    </tr>
    <tr>
      <td><small><strong>Storage</strong></small></td>
      <td><small>ChromaDB (vector database), File system (tool persistence)</small></td>
    </tr>
    <tr>
      <td><small><strong>Frontend</strong></small></td>
      <td><small>Three.js (3D IFC visualization)</small></td>
    </tr>
    <tr>
      <td><small><strong>Observability</strong></small></td>
      <td><small>Phoenix (Arize) for distributed tracing, custom execution logging</small></td>
    </tr>
  </tbody>
</table>

---

<h3>Quick Start</h3>

<h4>Prerequisites</h4>

- <small>Python 3.8+</small>
- <small>Node.js 16+ (optional, for frontend development)</small>

<h4>Installation</h4>

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

<h4>Build Frontend (Optional)</h4>

<small>If you want to use the 3D IFC viewer interface:</small>

```bash
cd frontend
npm install
npm run build
cd ..
```

<small>This builds the Three.js-based frontend and outputs to `templates/`. Skip this if you only need API access.</small>

<h4>Run the System</h4>

```bash
# Start FastAPI server
python main.py

# Access web interface at http://localhost:8000
```
