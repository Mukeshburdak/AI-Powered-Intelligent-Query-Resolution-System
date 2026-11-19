import React from "react";

export default function SourcePanel({ sources = [] }) {
  return <aside><h2>Sources</h2>{sources.length ? sources.map((source, i) => <p key={i}>{source.filename}</p>) : <p>No sources yet.</p>}</aside>;
}
