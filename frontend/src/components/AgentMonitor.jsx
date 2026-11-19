import React from "react";
import "./AgentMonitor.css";
const agentConfig = [
    {
        key: "query_understanding",
        name: "Query Understanding Agent",
        icon: "🧠",
        description: "Analyzes and classifies the user query.",
    },
    {
        key: "retrieval",
        name: "Retrieval Agent",
        icon: "🔍",
        description: "Searches relevant document chunks using FAISS.",
    },
    {
        key: "clarification",
        name: "Clarification Agent",
        icon: "❓",
        description: "Checks whether the query needs clarification.",
    },
    {
        key: "conversation_memory",
        name: "Conversation Memory Agent",
        icon: "💾",
        description: "Retrieves and stores conversation history.",
    },
    {
        key: "response_generation",
        name: "Response Generation Agent",
        icon: "✨",
        description: "Generates grounded answers using Gemini.",
    },
];

const statusLabels = {
    completed: "Completed",
    completed_no_history: "No previous history",
    running: "Running",
    not_started: "Waiting",
    error: "Error",
};

export default function AgentMonitor({ agents = {} }) {
    const completedCount = agentConfig.filter((agent) =>
        ["completed", "completed_no_history"].includes(
            agents[agent.key]?.status
        )
    ).length;

    const runningCount = agentConfig.filter(
        (agent) => agents[agent.key]?.status === "running"
    ).length;

    const errorCount = agentConfig.filter(
        (agent) => agents[agent.key]?.status === "error"
    ).length;

    return (
        <section className="agent-monitor">
            <div className="agent-monitor-header">
                <div>
                    <h3>AI Agent Execution</h3>
                    <p>Five-agent intelligent processing pipeline</p>
                </div>

                <div className="agent-summary">
                    <strong>{completedCount}/5</strong>
                    <small>Completed</small>
                </div>
            </div>

            <div className="agent-progress">
                <div
                    className="agent-progress-fill"
                    style={{
                        width: `${(completedCount / 5) * 100}%`,
                    }}
                />
            </div>

            <div className="agent-list">
                {agentConfig.map((agent) => {
                    const data = agents[agent.key] || {};
                    const status = data.status || "not_started";

                    return (
                        <div className="agent-item" key={agent.key}>
                            <div className="agent-icon">
                                {agent.icon}
                            </div>

                            <div className="agent-info">
                                <strong>{data.name || agent.name}</strong>

                                <small>
                                    {data.description || agent.description}
                                </small>
                            </div>

                            <span className={`agent-status ${status}`}>
                                <span className="status-dot" />
                                {statusLabels[status] || "Unknown"}
                            </span>
                        </div>
                    );
                })}
            </div>

            <div className="agent-monitor-footer">
                <span>{completedCount} completed</span>
                <span>{runningCount} running</span>
                <span>{errorCount} errors</span>
            </div>
        </section>
    );
}
