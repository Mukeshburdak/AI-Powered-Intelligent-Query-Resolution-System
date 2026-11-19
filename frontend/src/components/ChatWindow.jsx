
import React, { useRef, useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import AgentMonitor from "../components/AgentMonitor";
import { askQuestion } from "../services/api";

const INITIAL_AGENTS = {
  query_understanding: {
    name: "Query Understanding Agent",
    status: "not_started",
    description: "Analyzes and classifies the user query.",
  },
  retrieval: {
    name: "Retrieval Agent",
    status: "not_started",
    description: "Searches relevant document chunks using FAISS.",
  },
  response_generation: {
    name: "Response Generation Agent",
    status: "not_started",
    description: "Generates grounded answers using Gemini.",
  },
  clarification: {
    name: "Clarification Agent",
    status: "not_started",
    description: "Checks whether the query needs clarification.",
  },
  conversation_memory: {
    name: "Conversation Memory Agent",
    status: "not_started",
    description: "Retrieves and stores conversation history.",
  },
  structured_data: {
    name: "Structured Data Agent",
    status: "not_started",
    description: "Performs exact calculations and analytics on CSV datasets.",
  },
};

export default function ChatWindow({ selectedDocument }) {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [conversationId, setConversationId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [agents, setAgents] = useState(INITIAL_AGENTS);

  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  function resetAgents() {
    return Object.fromEntries(
      Object.entries(INITIAL_AGENTS).map(([key, agent]) => [
        key,
        { ...agent, status: "not_started" },
      ])
    );
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const text = question.trim();

    if (!text || loading) return;

    // Capture the selected document at submission time.
    const documentAtSubmission = selectedDocument
      ? { ...selectedDocument }
      : null;

    const documentId =
      documentAtSubmission?.document_id || null;

    setQuestion("");
    setError("");

    setMessages((previous) => [
      ...previous,
      {
        role: "user",
        content: text,
        selectedDocument:
          documentAtSubmission?.original_filename || null,
      },
    ]);

    setAgents(resetAgents());
    setLoading(true);

    try {
      const result = await askQuestion(
        text,
        conversationId,
        documentId
      );

      if (result.conversation_id) {
        setConversationId(result.conversation_id);
      }

      // Update all six agent statuses returned by FastAPI.
      if (result.agents) {
        setAgents((previous) => {
          const updated = { ...previous };

          Object.entries(result.agents).forEach(([key, agent]) => {
            if (updated[key]) {
              updated[key] = {
                ...updated[key],
                ...agent,
              };
            }
          });

          return updated;
        });
      }

      const questionType = result.question_type || "document";

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: result.answer || "No answer was returned.",
          sources: result.sources || [],
          confidence: result.confidence,
          questionType,
          datasetFilename: result.dataset_filename || null,
          rowsAnalyzed: result.rows_analyzed ?? null,
          needsClarification: result.needs_clarification || false,
          selectedDocument:
            documentAtSubmission?.original_filename || null,
        },
      ]);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to contact the query service."
      );

      setAgents((previous) => ({
        ...previous,
        response_generation: {
          ...previous.response_generation,
          status: "error",
        },
      }));
    } finally {
      setLoading(false);
    }
  }

  function startNewChat() {
    setMessages([]);
    setConversationId(null);
    setQuestion("");
    setError("");
    setAgents(resetAgents());
  }

  return (
    <section className="chat-window" aria-label="Chat window">
      <header className="chat-header">
        <div>
          <h2>Ask your documents</h2>

          <p>
            Get answers from your documents and structured datasets.
          </p>

          <p className="chat-welcome">
            {selectedDocument
              ? `Searching: ${selectedDocument.original_filename}`
              : "Searching across all your documents"}
          </p>
        </div>

        <button type="button" onClick={startNewChat}>
          New chat
        </button>
      </header>

      {/* Six-agent execution monitor */}
      <AgentMonitor agents={agents} />

      <div className="chat-messages" aria-live="polite">
        {messages.length === 0 && (
          <div className="chat-empty">
            <h3>How can I help you?</h3>

            <p>
              Ask questions about your uploaded documents or CSV datasets.
            </p>
          </div>
        )}

        {messages.map((message, index) => (
          <article
            className={`chat-message ${message.role}`}
            key={`${index}-${message.role}`}
          >
            <div className="message-role">
              {message.role === "user" ? "You" : "AI Assistant"}
            </div>

            {message.selectedDocument && (
              <p className="message-analysis-detail">
                <strong>Document:</strong> {message.selectedDocument}
              </p>
            )}

            {/* Markdown-rendered message content */}
            <div className="message-content">
              {message.role === "assistant" ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.content || ""}
                </ReactMarkdown>
              ) : (
                message.content
              )}
            </div>

            {/* Structured Data Analysis Information */}
            {message.role === "assistant" &&
              message.questionType === "structured_data" && (
                <div className="message-analysis">
                  <p className="message-analysis-status">
                    <span className="status-indicator" />
                    Analysis completed
                  </p>

                  {message.datasetFilename && (
                    <p className="message-analysis-detail">
                      <strong>Dataset:</strong> {message.datasetFilename}
                    </p>
                  )}

                  {typeof message.rowsAnalyzed === "number" && (
                    <p className="message-analysis-detail">
                      <strong>Rows analyzed:</strong>{" "}
                      {message.rowsAnalyzed.toLocaleString("en-IN")}
                    </p>
                  )}
                </div>
              )}

            {/* Retrieval Score: Only for normal RAG responses */}
            {message.role === "assistant" &&
              message.questionType !== "structured_data" &&
              typeof message.confidence === "number" && (
                <p className="message-confidence">
                  Retrieval score: {(message.confidence * 100).toFixed(1)}%
                </p>
              )}

            {/* Sources: Only when available */}
            {message.role === "assistant" &&
              message.sources?.length > 0 && (
                <details className="message-sources">
                  <summary>
                    Sources ({message.sources.length})
                  </summary>

                  <ul>
                    {message.sources.map((source, sourceIndex) => (
                      <li
                        key={
                          source.citation ||
                          `${source.source}-${source.chunk_id}-${sourceIndex}`
                        }
                      >
                        <strong>
                          [{source.citation || `S${sourceIndex + 1}`}]
                        </strong>{" "}
                        {source.source || "Unknown document"}

                        {source.chunk_id && (
                          <span> — {source.chunk_id}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
          </article>
        ))}

        {loading && (
          <div className="chat-loading" role="status">
            Assistant is thinking…
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {error && (
        <p className="chat-error" role="alert">
          {error}
        </p>
      )}

      <form className="chat-input-form" onSubmit={handleSubmit}>
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
          placeholder="Ask about your documents or datasets..."
          aria-label="Your question"
          rows={2}
          disabled={loading}
        />

        <button type="submit" disabled={loading || !question.trim()}>
          {loading ? "Generating..." : "Send"}
        </button>
      </form>

      <p className="chat-disclaimer">
        Answers are generated using document retrieval or structured data
        analysis, depending on your question.
      </p>
    </section>
  );
}
