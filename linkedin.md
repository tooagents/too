Highlights (description)

Option A — narrative + bullets (~1,400 chars):

Led the AI engineering team building an enterprise conversational analytics platform — natural-language questions answered with governed SQL, prose, and charts over a Snowflake warehouse.

• Re-architected a monolithic LLM agent into a modular multi-agent system — an orchestration/routing agent, a text-to-SQL retrieval agent, and a visualization agent behind a typed contract on AWS Bedrock AgentCore.
• The redesign unlocked follow-up data reuse (re-render cached results as new charts with zero re-query) and pushed cheap deterministic intent routing to a FastAPI edge, cutting latency and per-turn cost.
• Built the streaming pipeline end-to-end: React 19 + Vite frontend with live SSE and inline chart rendering → FastAPI proxy → agent runtimes → VPC Lambda → Snowflake.
• Led a zero-regression persistence migration from DynamoDB to PostgreSQL behind a feature flag, preserving transactional idempotency (1,600+ tests green).
• Owned deployment on AWS ECS/ECR, CodeBuild, and Bedrock AgentCore runtimes, plus evaluation and observability tooling.

Option B — tighter, all bullets (~750 chars):

• Led AI team building a conversational analytics platform (NL → SQL → charts over Snowflake).
• Re-architected a monolithic LLM agent into modular orchestration / text-to-SQL / visualization agents on AWS Bedrock AgentCore.
• Enabled zero-requery follow-up reuse and low-latency FastAPI edge routing.
• Built React 19 + SSE streaming frontend through a FastAPI proxy to agent runtimes and Snowflake.
• Ran a zero-regression DynamoDB → PostgreSQL migration behind a feature flag.
• Owned ECS/ECR/CodeBuild deployment, evals, and observability.

Skills (LinkedIn supports many; ordered by weight)

Python · FastAPI · React · TypeScript · Amazon Web Services (AWS) · Amazon Bedrock · Multi-Agent Systems · Large Language Models (LLM) · Generative AI · Retrieval-Augmented Generation (RAG) · Text-to-SQL · Snowflake · PostgreSQL · Amazon DynamoDB · Amazon ECS · Software Architecture · Distributed Systems · REST APIs · Server-Sent Events (SSE) · AI/ML Engineering















Here's a project entry, grounded in the real work and kept in the hands-on builder voice.

Project name (≤255)

Pick one:

- Conversational Analytics Platform — Multi-Agent Text-to-SQL on AWS Bedrock (my pick)
- Enterprise Conversational Analytics: NL → SQL → Charts over Snowflake
- Multi-Agent Conversational BI Platform (AWS Bedrock AgentCore)

Description (≤2,000)

An enterprise conversational analytics platform that answers natural-language business questions with governed SQL, prose, and interactive charts over a Snowflake data warehouse.

I worked hands-on across the full stack:

• Rebuilt a monolithic LLM agent into a modular multi-agent system — an orchestration/routing agent, a text-to-SQL retrieval agent, and a visualization agent — coordinated behind a typed contract and deployed as AWS Bedrock AgentCore runtimes.

• Implemented conversational follow-up handling that re-renders cached query results as new chart types with zero re-query, and moved deterministic intent routing (greetings, acknowledgements, out-of-scope) to a FastAPI edge to cut latency and per-turn cost.

• Built the streaming request path end-to-end: a React 19 + Vite frontend with live Server-Sent Events and dependency-free inline SVG chart rendering → a FastAPI proxy → the agent runtimes → a VPC Lambda → Snowflake.

• Engineered the text-to-SQL layer (Amazon Bedrock, Claude) with schema grounding and a NAT-allowlisted execution path into Snowflake.

• Handled deployment and operations on AWS — ECS/ECR, CodeBuild, and AgentCore runtimes — plus evaluation and observability tooling.

Tech: Python, FastAPI, React, TypeScript, AWS (Bedrock AgentCore, ECS, Lambda, S3), Snowflake, PostgreSQL, DynamoDB, Server-Sent Events.

That's ~1,500 chars, leaving you room to add or trim.

Top 5 skills

1. Python
2. FastAPI
3. Amazon Bedrock
4. Multi-Agent Systems
5. Text-to-SQL (swap for Snowflake or React if you'd rather lead with a named tech recruiters filter on)

Dates

- Start: August 2024 (matches the role).
- You told me the project's done, so uncheck "currently working on this project" and set an E's September 2026. If it wrapped earlier, use that month instead.

Two quick judgment calls for you:

- "1,600+ tests passing" is real (the migration merge suite), but it was the combined port su tests. Keep or cut — your call for a public profile.
- Contributors / Media: if you have a non-confidential architecture diagram or a screenshot of the chart UI, media boosts a project entry a lot — but check it's cleared of internal codenames and data first. I left
  both empty since I can't verify what's shareable.

Want a shorter variant, or one tuned to a specific job you're targeting?
