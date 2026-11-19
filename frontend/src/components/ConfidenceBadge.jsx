import React from "react";

export default function ConfidenceBadge({ confidence = 0 }) {
  return <span>Confidence: {Math.round(confidence * 100)}%</span>;
}
