# Minimal Agent — Implementation Plan

Based on `spec.md`. Builds on completed radrags infrastructure (chunker, vectorstore, server).

## Status

| Phase | Status | Notes |
|---|---|---|
| **Phase 1** — SSH Client & Config | **DONE** | `SSHClient` (renamed from `VyOSClient`), `CommandResult`, `AgentConfig`, `load_agent_config`. Tests in `tests/test_ssh.py`. |
| **Phase 2** — Tools | **DONE** | `query_docs`, `show_config_tool`, `run_command`, `read_file_tool`, `TOOL_REGISTRY`, `TOOL_SCHEMAS`. All in `src/radrags/agent.py`. Tests in `tests/test_agent.py`. |
| **Phase 3** — Agent Core | **NOT STARTED** | Next up. |
| **Phase 4** — REPL | NOT STARTED | |
| **Phase 5** — Integration | NOT STARTED | |

### Files created/modified so far

- `src/radrags/ssh.py` — `SSHClient`, `CommandResult` (generic SSH, no VyOS-specific logic)
- `src/radrags/agent.py` — four tool functions + registry + schemas
- `src/radrags/config.py` — added `AgentConfig` dataclass + `load_agent_config()`
- `pyproject.toml` — added `paramiko` to dependencies
- `tests/test_ssh.py` — 7 tests (config + SSH execute + connection errors)
- `tests/test_agent.py` — 11 tests (all four tools + registry)
- `examples/ssh.py` — live SSH to localhost demo
- `examples/tools.py` — live demo of each tool

### Key decisions made during execution

- **Renamed `VyOSClient` → `SSHClient`** — the SSH module is generic; VyOS-specific logic (`show_config`) moved to the tools layer in `agent.py`.
- **`show_config` is a tool, not an SSH method** — keeps SSH module reusable, VyOS knowledge lives in one place.
- **`os.path.expanduser()` on key_path** — paramiko doesn't expand `~`, fixed in `SSHClient.__init__`.

**Branch:** `feat/minimal-agent` (all commits so far on this branch)

**Test count:** 142 total passing (11 agent + 7 ssh + 124 existing).

## Summary

Add an interactive agent (`radrags.agent`) that uses RAG retrieval + Ollama chat + SSH to configure a VyOS router with human-in-the-loop command approval. REPL interface.

## Prerequisites

- ChromaDB indexed with VyOS docs (Phases 1–5 complete).
- Ollama running with a chat model (e.g. `qwen3:32b`) and `nomic-embed-text`.
- SSH access to a VyOS box.

## Decisions

| Decision | Choice |
|---|---|
| SSH library | `paramiko` (testable, Pythonic) |
| LLM chat | `ollama` Python client (already a dep) — native tool calling API |
| Agent pattern | ReAct-style: LLM calls tools in a loop until it has a final answer |
| Approval | Injectable `approve_fn`; production = stdin prompt, tests = mock |
| Config | `[agent]` section in existing INI |
| Modules | `src/radrags/ssh.py`, `src/radrags/agent.py` |
| Scope | Single-session, stateless between runs |

---

## Phase 1 — SSH Client & Config ✅

Branch: `feat/minimal-agent`

### 1.1 AgentConfig ✅

`AgentConfig` dataclass + `load_agent_config()` in `src/radrags/config.py`. Reads `[agent]` INI section with fields: `ssh_host`, `ssh_port`, `ssh_user`, `ssh_key_path`, `chat_model`, `max_iterations`.

### 1.2 SSH execute ✅

`SSHClient` class in `src/radrags/ssh.py` (originally `VyOSClient`, renamed to keep SSH layer generic). `execute(cmd) -> CommandResult(stdout, stderr, exit_code)`. Expands `~` in `key_path` via `os.path.expanduser()`.

### 1.3 Connection errors ✅

Catches `paramiko.NoValidConnectionsError`, `SSHException`, `OSError` → re-raises as `ConnectionError`.

---

## Phase 2 — Tools ✅

> **What this is:** The LLM agent works by calling "tools" — functions it can
> invoke during its reasoning loop. Ollama's chat API supports tool calling
> natively: the model receives tool schemas (name, description, parameters),
> decides which tool to call and with what arguments, and we execute it and
> feed the result back. Phase 2 defines the four tools the agent can use:
>
> - **query_docs** — search the RAG vector store for VyOS documentation
> - **show_config** — inspect the router's current config via SSH
> - **run_command** — execute a command on the router (human approval required)
> - **read_file** — read a local file (e.g. a wireguard .conf the user wants applied)
>
> Each tool is a plain Python function. The tool registry + schemas wire them
> into Ollama's tool-calling format. All testable with mocked deps.

### 2.1 query_docs ✅

`query_docs(query, store=, top_k=5)` — calls `store.query()`, formats results as numbered list with source file. Returns `"No results found."` on empty.

### 2.2 show_config tool ✅

`show_config_tool(path=None, client=)` — runs `show configuration commands` (with optional grep filter) via `SSHClient.execute()`, returns stdout.

### 2.3 run_command ✅

`run_command(command, client=, approve_fn=)` — calls `approve_fn(command)` first; if `True`, executes via SSH and returns stdout; if `False`, returns `"Declined by user."`.

### 2.4 read_file ✅

`read_file_tool(path=)` — reads local file, returns contents or `"File not found: ..."`.

### 2.5 Tool registry & schemas ✅

`TOOL_REGISTRY` maps `{"query_docs", "show_config", "run_command", "read_file"}` to callables. `TOOL_SCHEMAS` is the matching list of Ollama tool-calling format dicts.

---

## Phase 3 — Agent Core

### 3.1 System prompt

Test: `build_system_prompt()` contains VyOS role context, safety rules ("always ask before running commands"), and tool usage instructions.

Impl: Returns the system prompt string. Parameterized so it can include router hostname/identity.

### 3.2 Chat turn

Test: `agent_step(messages, tools, model, client)` appends user message, calls `ollama.Client.chat()`, returns the response message (which may contain `tool_calls`). Mock Ollama.

Impl: Thin wrapper that calls `ollama.chat(model, messages, tools=TOOL_SCHEMAS)` and returns the message object.

### 3.3 Tool dispatch

Test: `dispatch("query_docs", {"query": "wireguard"}, deps)` calls the query_docs function with correct args, returns result string. Unknown tool name → error string.

Impl: Looks up `TOOL_REGISTRY[name]`, calls it with `**args` + injected deps (store, ssh_client, approve_fn).

### 3.4 Agent loop

Test: Multi-turn simulation —
1. User: "show wireguard interfaces"
2. LLM calls `show_config(path="interfaces wireguard")`
3. Tool returns config output
4. LLM responds with summary

All external deps mocked. Assert: correct tool was called, LLM received tool result, final response is a plain text message (no more tool calls).

Impl: `run_agent_loop(task, store, ssh_client, model, approve_fn)` — iterates: send to LLM → if tool_calls, dispatch each, append results, repeat → if no tool_calls, return final answer.

Max iterations safety cap (default 10).

---

## Phase 4 — REPL

### 4.1 Interactive REPL

Test: Feed scripted input (task + "y" approval) to the REPL via mock stdin. Assert it processes the task and prints output. Mock all external deps.

Impl: `python -m radrags.agent --config radrags.ini` starts the REPL. Reads user input, runs the agent loop, prints responses. Command approval prompts on stdout, reads y/n from stdin.

### 4.2 Multi-turn conversation

Test: User sends two tasks in sequence. Assert conversation history is maintained within the session (second turn can reference first).

Impl: REPL accumulates messages list across turns within one session.

---

## Phase 5 — Integration

### 5.1 Smoke test: inspect config

Test: With live Ollama + SSH + indexed docs, ask "show current wireguard interfaces." Assert agent calls `show_config`, returns output containing VyOS config syntax. Skip if services unavailable.

Impl: No new production code.

### 5.2 Smoke test: RAG + reasoning

Test: Ask "how do I generate wireguard keys on VyOS?" Assert agent calls `query_docs`, response references key generation commands from the documentation. Skip if services unavailable.

Impl: No new production code.

---

## Dependencies ✅

`paramiko` added to `pyproject.toml` `[project.dependencies]`. Already synced.

## Config additions

```ini
[agent]
# ssh_host = 192.168.1.1
# ssh_port = 22
# ssh_user = vyos
# ssh_key_path = ~/.ssh/id_ed25519
# chat_model = qwen3:32b
# max_iterations = 10
```

## Sequencing

- Phase 1 is testable with paramiko mocks, no live SSH needed.
- Phase 2 tools are all testable with mocked deps.
- Phase 3 agent loop is testable with mocked Ollama + mocked tools.
- Phase 4 REPL needs careful stdin/stdout mocking but no live services.
- Phase 5 is the only phase requiring live Ollama + SSH + ChromaDB.
