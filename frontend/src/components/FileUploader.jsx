
import React, { useEffect, useRef, useState } from "react";

import {
  uploadDocument,
  getUploadedDocuments,
} from "../services/api";

export default function FileUploader({
  selectedDocument,
  onSelectDocument,
}) {
  const inputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [loadingDocuments, setLoadingDocuments] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [uploadedFiles, setUploadedFiles] = useState([]);

  async function loadDocuments() {
    try {
      const result = await getUploadedDocuments();
      const documents = result.documents || [];

      setUploadedFiles(documents);

      // Clear the selection if the selected document no longer exists.
      if (
        selectedDocument &&
        !documents.some(
          (item) =>
            item.document_id === selectedDocument.document_id
        )
      ) {
        onSelectDocument(null);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load uploaded documents."
      );
    } finally {
      setLoadingDocuments(false);
    }
  }

  useEffect(() => {
    loadDocuments();
  }, []);

  async function handleUpload(event) {
    event.preventDefault();

    if (!file || uploading) return;

    setUploading(true);
    setMessage("");
    setError("");

    try {
      const result = await uploadDocument(file);

      const newDocument = {
        document_id: result.document_id,
        original_filename: result.original_filename || file.name,
        file_type: file.name.split(".").pop()?.toLowerCase() || "",
      };

      if (!newDocument.document_id) {
        throw new Error(
          "Upload succeeded, but the document identifier was not returned."
        );
      }

      await loadDocuments();

      // Automatically select the newly uploaded document.
      onSelectDocument(newDocument);

      setMessage(
        result.message || `${file.name} uploaded successfully.`
      );

      setFile(null);

      if (inputRef.current) {
        inputRef.current.value = "";
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to upload the document."
      );
    } finally {
      setUploading(false);
    }
  }

  function handleDocumentSelection(event) {
    const documentId = event.target.value;

    if (!documentId) {
      onSelectDocument(null);
      return;
    }

    const document = uploadedFiles.find(
      (item) => item.document_id === documentId
    );

    onSelectDocument(document || null);
  }

  return (
    <section className="document-uploader">
      <div className="upload-icon" aria-hidden="true">
        ↑
      </div>

      <h3>Upload documents and datasets</h3>

      <p className="upload-description">
        Upload PDF, DOCX, TXT, Markdown, or CSV files.
        Ask questions about your documents and structured datasets.
      </p>

      <form onSubmit={handleUpload}>
        <label className="file-drop-area">
          <span className="file-drop-title">
            {file ? file.name : "Choose a document"}
          </span>

          <span className="file-drop-hint">
            Select a file from your computer
          </span>

          <input
            ref={inputRef}
            type="file"
            accept=".txt,.pdf,.docx,.md,.csv"
            onChange={(event) => {
              setFile(event.target.files?.[0] || null);
              setMessage("");
              setError("");
            }}
          />
        </label>

        <button
          className="upload-button"
          type="submit"
          disabled={!file || uploading}
        >
          {uploading ? "Uploading..." : "Upload document"}
        </button>
      </form>

      {message && (
        <p className="upload-success" role="status">
          {message}
        </p>
      )}

      {error && (
        <p className="upload-error" role="alert">
          {error}
        </p>
      )}

      <div className="uploaded-files">
        <h4>Select a document for your questions</h4>

        {loadingDocuments ? (
          <p>Loading your documents...</p>
        ) : uploadedFiles.length > 0 ? (
          <>
            <select
              className="document-selector"
              value={selectedDocument?.document_id || ""}
              onChange={handleDocumentSelection}
            >
              <option value="">Search all my documents</option>

              {uploadedFiles.map((item) => (
                <option
                  key={item.document_id}
                  value={item.document_id}
                >
                  {item.original_filename}
                </option>
              ))}
            </select>

            <p className="upload-description">
              {selectedDocument
                ? `Selected: ${selectedDocument.original_filename}`
                : "No specific document selected. All your documents can be searched."}
            </p>
          </>
        ) : (
          <p>No uploaded documents found. Upload one to get started.</p>
        )}
      </div>
    </section>
  );
}
