goal is:

* create a robust way to serve the chroma DB (docker whatever)
* document how persistnet the DB is
* create an integration step in this repository (src/one_simple_rag) where a framework would be able to call my DB and do something with the output in the context of writing my own agent.
* can be a http server, grpc, whatever.
* I don't care about auth yet.

desired approximate use
curl myserver:post -d {"query": "how do I do X and Y", "top": 5}
and I'd get a json with all the relevant documents returned to me.

---

## Questions before planning

1. The server wraps `ChromaStore.query()` — should it also expose `add()` (indexing new chunks via HTTP), or is indexing always done offline via library code?
does not matter. For now simplest is to assume that we only query the static document DB

2. You mention `src/one_simple_rag` — is this a new package/module, or did you mean adding a server module inside the existing `src/radrags/` (e.g. `radrags.server`)?
what do you think? I was thinking it may be part of a bigger infra test, hence my suggestion. Dose it make more sense to simply have a serve option in the module directy and instructions.

3. For the server framework: any preference between FastAPI, Flask, or plain stdlib (`http.server`)? FastAPI gives you automatic OpenAPI docs and async for free.
FastAPI is the hot new thing innit?

4. Should the server embed the query on the fly (requires Ollama reachable from the server), or do you expect a pre-running ChromaDB server that handles embeddings itself? Currently `ChromaStore` calls Ollama directly.
assume the server lives on a machine where he can embed the query by making a call. (or actually advise. at the end of the day this will all run on a VM in my basement)

5. Docker: do you want a single container running both Ollama + the query server, or two separate containers (Ollama + your server) composed together? Or is Docker only for the query server, assuming Ollama runs on the host?
ollama currently running on bare metal because ... GPU. unless you're really convincing I'd like to keep it like that.

6. For the JSON response shape, is the current `query()` return (`{"text", "metadata", "distance"}` per result) sufficient, or do you want a different/simpler schema?
I want suggestions. Anything that can be useful for my agent RAG pipeline. 

7. Should the server support multiple collections, or is it always a single pre-configured collection?
eventually. at a later version.

8. The `chroma_db/` directory already exists at repo root — should the server use that same path by default, or a configurable one?
configurable. today we use this one.

9. Do you need a health/readiness endpoint (e.g. `/health`) so Docker or an orchestrator can probe it?
sure

10. Any preference on how the server gets configured — env vars, CLI args, a config file, or just constructor defaults?
simplest. I say config file (ini).