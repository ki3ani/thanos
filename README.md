# GKE-Powered AI Agent Team for E-Commerce

**An autonomous, multi-agent AI system built for the GKE Turns 10 Hackathon that supercharges the Online Boutique microservices app with real-time marketing, recommendations, and support.**

---

## 🏛️ System Architecture

Our project is an external "AI brain" for the Online Boutique. It uses a team of specialized agents that work together to monitor the application, find insights, and take autonomous action without touching the original code.

`[User Traffic] -> [Online Boutique] -> [MCP Server] -> [Analyst Agent] --(A2A)--> [Marketing Agent] -> [Database]`

---

## 🤖 Components & Technologies Showcase

| Component | Role in System | Key Technologies Demonstrated |
| :--- | :--- | :--- |
| **MCP Toolbox Server** | Provides a clean API for real-time user activity context. | GKE, **MCP Server** |
| **Business Analyst Agent**| Senses trends using the MCP Server and delegates tasks. | GKE, Gemini, **MCP Client**, **A2A (Sender)** |
| **Marketing Agent** | Receives goals, generates ad copy with Gemini, and publishes it. | GKE, Gemini, **A2A (Receiver)**, Cloud SQL |
| **Recommendation Agent** | Replaces the original service with an AI-powered gRPC server. | GKE, Gemini, gRPC, **MCP (Client)**, A2A (Receiver) |
| **Customer Support Agent**| Acts as a user-facing chatbot grounded in the app's data. | GKE, Gemini, gRPC, **MCP (Client)** |
| **Mission Control Dashboard** | A live UI that visualizes the entire system's activity. | GKE, Flask |

---

## ✨ Key Innovations

* **Fully Autonomous Closed Loop:** Our system autonomously **senses** real-time events, **thinks** about their strategic importance, and **acts** to create a business outcome without human intervention.
* **Diverse Agent Patterns:** We demonstrate multiple agent archetypes: a scheduled analyst, a reactive marketing service, an intelligent gRPC replacement, and an interactive user-facing chatbot.
* **Responsible AI (Grounding):** Our Customer Support Agent is explicitly "grounded" in the application's real-time data to provide trustworthy answers and prevent AI hallucination.
