
import React, { useState } from "react";
import ChatWindow from "../components/ChatWindow";
import FileUploader from "../components/FileUploader";

export default function ChatPage({ user, onLogout }) {
  const [selectedDocument, setSelectedDocument] = useState(null);

  return (
    <main className="chat-page">
      <header className="chat-header">
        <div>
          <p className="auth-eyebrow">
            INTELLIGENT QUERY RESOLUTION
          </p>

          <h1>AI Query Resolution</h1>

          <p className="chat-welcome">
            Welcome, {user?.name || user?.email}
          </p>
        </div>

        <button className="logout-button" onClick={onLogout}>
          Sign out
        </button>
      </header>

      <FileUploader
        selectedDocument={selectedDocument}
        onSelectDocument={setSelectedDocument}
      />

      <ChatWindow selectedDocument={selectedDocument} />
    </main>
  );
}
