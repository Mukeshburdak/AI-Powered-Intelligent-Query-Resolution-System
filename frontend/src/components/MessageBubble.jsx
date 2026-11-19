import React from "react";

export default function MessageBubble({ role = "assistant", children }) {
  return <div className={`message-bubble ${role}`}>{children}</div>;
}
