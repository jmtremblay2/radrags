# Minimal Agent — Implementation Plan

Based on `spec.md`. Builds on completed radrags infrastructure (chunker, vectorstore, server).

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

## Phase 1 — SSH Client & Config

Branch: `feat/minimal-agent`

### 1.1 AgentConfig

Test: Load INI with `[agent]` section → `AgentConfig` has `ssh_host`, `ssh_port`, `ssh_user`, `ssh_key_path`, `chat_model`. Test defaults when section is absent.

Impl: `AgentConfig` dataclass in `config.py`. Add `load_agent_config(path)`.

### 1.2 SSH execute

Test: `VyOSClient.execute("echo hello")` returns `CommandResult(stdout, stderr, exit_code)`. Mock paramiko's `SSHClient`.

Impl: `src/radrags/ssh.py` — `VyOSClient(host, port, user, key_path)` with `execute(cmd) -> CommandResult`.

### 1.3 show_config

Test: `client.show_config()` returns full config. `client.show_config("interfaces wireguard")` returns filtered subset. Mock SSH.

Impl: `show_config(path=None)` wraps `execute("show configuration commands ...")`.

### 1.4 Connection errors

Test: Unreachable host → `ConnectionError` with descriptive message.

Impl: Catch paramiko exceptions, re-raise as `ConnectionError`.

---

## Phase 2 — Tools

### 2.1 query_docs

Test: `query_docs("wireguard setup", store)` returns formatted string with chunk text + source file. Mock `ChromaStore.query()`.

Impl: Calls store.query(), formats results as text suitable for LLM context.

### 2.2 show_config tool

Test: `show_config_tool("interfaces", client)` returns config output string. Mock SSH client.

Impl: Thin wrapper over `VyOSClient.show_config()`.

### 2.3 run_command (with approval gate)

Test:
- `approve_fn` returns `True` → command runs, returns stdout.
- `approve_fn` returns `False` → command NOT executed, returns "Declined by user."

Impl: Calls `approve_fn(cmd)` first. Only executes if approved.

### 2.4 read_file

Test: Returns file contents for existing file. Returns error string for missing file.

Impl: Reads local file path, returns content or `"File not found: ..."`.

### 2.5 Tool registry & schemas

Test: `TOOL_REGISTRY` maps each tool name to its callable. `TOOL_SCHEMAS` is a list of dicts matching Ollama's tool-calling format (name, description, parameters).

Impl: Define the registry dict and schema list. Schemas follow `{"type": "function", "function": {"name": ..., "description": ..., "parameters": {...}}}`.

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

## Dependencies to add

```toml
# pyproject.toml [project.dependencies]
"paramiko"
```

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
