goals:
* learn LLMs and AI in general
* toy with local models
    * mostly out of "convenience" and cheapness 
    * privacy -- the AI can access my secrets and produce configs and what not
    * more choices -- can compare models, sizes, etc. inspect embeddings, memory
    * no smoke and mirror: can correlate what I do with the result. no magic of AI models changing overnight blurring results
* ... but not opposed to integration with paid models when it serves education / personal development goals
* my idea (could be wrong) is that improving a workflow / testing agents to improve them is a valid endeavor on "weak" local models just the same as on better performing models anyways
* want to learn the ecosystem along with the AI part of it. maybe even more the ecosystem.
    * get a much better understanding of the role of each component / boundary
        * when do I need MCP, LangChain, use built-ins from ollama, etc

tools:
* doing a bunch of DIY when the big frameworks get in the way of learning concepts
* not opposed to using the frameworks however (LangChain, ChromaDB) when bypassing them is a lot of wasted work -- use the time to learn the framework in that case
* really curious about the cline open source agent... unless it's too involved I'd like to try it.
* comparing models will have to be part of the exercice. I was thinking whatever biggest qwen (qwen3:32b) I can fit on 24GB VRAM. when testing on a laptop I may have to substitute for something that can take only 12GB VRAM.
* I'm thinking really simply using bare bore ssh for remote access to machines (like the router) but open to suggestions if they are part of the agents / LLM toolkit.

first project draft idea
* end to end RAG-based agent to configure my router
* router is VyOS rolling release 
* approximate router doc with most recent tag in their doc: 1.4.3
* ability to inspect full router config via logging in the VyOS box
    * for example if I ask the AI to set up a wireguard interface, it can look at existing interfaces to name it something new.
* ability to run commands -- humans in the loop at first --
    * for example the chat box will stop and say "I want to run `configure x y z` should I proceed (y/n)" and only proceed if I say yes
    * I want the agent to issue commands itself via SSH
* example task: "read (an example wireguard config file, say ./testwf.conf) and create a wireguard interface in my VyOS box. provide a way to validate the interface is up by accessing a host on it"
* at first it does not need to be perfect. I want the full pipeline up and running before I start tweaking the individual pieces. When a step is good enough to start integration I will halt efforts on that, move on, revisit later.