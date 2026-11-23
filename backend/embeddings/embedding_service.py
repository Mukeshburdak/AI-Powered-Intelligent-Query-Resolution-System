
import os
import time
import random
import threading

import numpy as np
from google import genai
from google.genai import types


MODEL_NAME = os.getenv(
    "GEMINI_EMBEDDING_MODEL",
    "gemini-embedding-001",
)

EMBEDDING_DIMENSION = 768

# Smaller batches reduce sudden token consumption.
BATCH_SIZE = 10

# Stay below the Gemini free-tier 30,000 TPM limit.
MAX_TOKENS_PER_MINUTE = 25000

# Approximate token count when an official tokenizer is unavailable.
CHARS_PER_TOKEN = 3

MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 2
MAX_RETRY_DELAY = 60

_client = None
_client_lock = threading.Lock()
_rate_lock = threading.Lock()

_token_usage = []
_last_request_time = 0.0


def get_embedding_client():
    """Create and reuse the Gemini API client."""
    global _client

    with _client_lock:
        if _client is None:
            api_key = os.getenv("GEMINI_API_KEY")

            if not api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY is missing from environment."
                )

            _client = genai.Client(api_key=api_key)

    return _client


def _normalize(vectors) -> np.ndarray:
    """Convert vectors to normalized float32 arrays."""
    vectors = np.asarray(vectors, dtype=np.float32)

    if vectors.size == 0:
        return np.empty(
            (0, EMBEDDING_DIMENSION),
            dtype=np.float32,
        )

    norms = np.linalg.norm(vectors, axis=1, keepdims=True)

    return vectors / np.maximum(norms, 1e-12)


def _estimate_tokens(texts: list[str]) -> int:
    """Conservatively estimate tokens from input characters."""
    return max(
        1,
        sum(len(text) for text in texts) // CHARS_PER_TOKEN,
    )


def _wait_for_rate_limit(token_count: int):
    """Pace requests using a rolling 60-second token window."""
    global _token_usage, _last_request_time

    with _rate_lock:
        while True:
            now = time.monotonic()

            _token_usage = [
                (timestamp, tokens)
                for timestamp, tokens in _token_usage
                if now - timestamp < 60
            ]

            used_tokens = sum(
                tokens for _, tokens in _token_usage
            )

            if token_count > MAX_TOKENS_PER_MINUTE:
                raise ValueError(
                    "A single embedding request exceeds the configured "
                    "token budget. Reduce the document chunk size."
                )

            remaining = MAX_TOKENS_PER_MINUTE - used_tokens

            if remaining >= token_count:
                # Also avoid sending requests too close together.
                elapsed = now - _last_request_time

                if elapsed < 1:
                    time.sleep(1 - elapsed)

                now = time.monotonic()
                _token_usage.append((now, token_count))
                _last_request_time = now
                return

            oldest_timestamp = min(
                timestamp for timestamp, _ in _token_usage
            )

            wait_time = max(
                1,
                60 - (now - oldest_timestamp) + 0.5,
            )

            time.sleep(wait_time)


def _is_rate_limit_error(error: Exception) -> bool:
    """Identify Gemini quota and rate-limit errors."""
    error_text = str(error).lower()

    return (
        "429" in error_text
        or "resource_exhausted" in error_text
        or "rate limit" in error_text
    )


def _embed_batch(client, batch, task_type):
    """Send one embedding batch with retry handling."""
    token_count = _estimate_tokens(batch)

    for attempt in range(MAX_RETRIES + 1):
        _wait_for_rate_limit(token_count)

        try:
            return client.models.embed_content(
                model=MODEL_NAME,
                contents=batch,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=EMBEDDING_DIMENSION,
                ),
            )

        except Exception as error:
            if not _is_rate_limit_error(error):
                raise

            if attempt >= MAX_RETRIES:
                raise RuntimeError(
                    "Gemini embedding quota remains exhausted after "
                    f"{MAX_RETRIES} retries. Please retry later or "
                    "check your Gemini API quota."
                ) from error

            delay = min(
                INITIAL_RETRY_DELAY * (2 ** attempt),
                MAX_RETRY_DELAY,
            )

            delay += random.uniform(0, 1)

            print(
                f"Gemini rate limit reached. "
                f"Retrying in {delay:.1f} seconds "
                f"({attempt + 1}/{MAX_RETRIES})."
            )

            time.sleep(delay)


def embed_texts(texts: list[str]) -> np.ndarray:
    """Generate normalized document embeddings in paced batches."""
    if not texts:
        return np.empty(
            (0, EMBEDDING_DIMENSION),
            dtype=np.float32,
        )

    client = get_embedding_client()
    all_vectors = []

    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start:start + BATCH_SIZE]

        response = _embed_batch(
            client,
            batch,
            "RETRIEVAL_DOCUMENT",
        )

        if (
            not response.embeddings
            or len(response.embeddings) != len(batch)
        ):
            raise RuntimeError(
                "Gemini returned an unexpected number "
                "of document embeddings."
            )

        all_vectors.extend(
            embedding.values
            for embedding in response.embeddings
        )

    return _normalize(all_vectors)


def embed_query(query: str) -> np.ndarray:
    """Generate one normalized query embedding."""
    if not query or not query.strip():
        raise ValueError("Query must not be empty.")

    client = get_embedding_client()

    response = _embed_batch(
        client,
        [query.strip()],
        "RETRIEVAL_QUERY",
    )

    if not response.embeddings:
        raise RuntimeError(
            "Gemini did not return a query embedding."
        )

    return _normalize([
        response.embeddings[0].values
    ])


class EmbeddingService:
    """Class-based interface used by the existing application."""

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        return embed_texts(texts)

    def embed_query(self, query: str) -> np.ndarray:
        return embed_query(query)
