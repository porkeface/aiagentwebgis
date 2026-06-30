import { getToken } from "./auth";
import type { SSEEvent, SSEEventType } from "../types";

const BASE_URL = "/api/v1";

export async function sendChatMessage(
  message: string,
  sessionId: string,
  onEvent: (event: SSEEvent) => void,
): Promise<void> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE_URL}/agent/chat`, {
    method: "POST",
    headers,
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  if (!response.ok) {
    let detail: unknown;
    try {
      detail = await response.json();
    } catch {
      // ignore parse error
    }
    const message =
      detail && typeof detail === "object" && "detail" in detail
        ? String((detail as { detail: unknown }).detail)
        : `Chat request failed with status ${response.status}`;
    onEvent({ type: "error", data: { status: response.status, message } });
    return;
  }

  if (!response.body) {
    onEvent({ type: "error", data: { message: "Response body is null" } });
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE events are separated by double newlines
    const parts = buffer.split("\n\n");
    // Keep the last part in buffer (may be incomplete)
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const event = parseSSEEvent(part);
      if (event) {
        onEvent(event);
      }
    }
  }

  // Flush any remaining bytes from the TextDecoder (handles the case where
  // the stream ends mid-UTF-8 sequence — without this, the last Chinese
  // character can be lost or corrupted).
  buffer += decoder.decode();
  if (buffer.trim()) {
    const event = parseSSEEvent(buffer);
    if (event) {
      onEvent(event);
    }
  }
}

function parseSSEEvent(raw: string): SSEEvent | null {
  const lines = raw.split("\n");
  let eventType = "";
  let dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventType = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
    // Lines starting with ":" are comments, ignore
  }

  if (!eventType && dataLines.length === 0) {
    return null;
  }

  const rawData = dataLines.join("\n");
  let parsedData: unknown;
  try {
    parsedData = rawData ? JSON.parse(rawData) : null;
  } catch {
    parsedData = rawData;
  }

  // The backend always sends `event: message` on the SSE wire, wrapping the
  // real event type inside the JSON payload: { type: "<event_type>", data: {...} }.
  // Extract the actual type from the JSON envelope, falling back to the SSE
  // event line for non-message events like "done".
  let type: SSEEventType;
  let innerData: unknown;

  if (
    parsedData &&
    typeof parsedData === "object" &&
    "type" in (parsedData as Record<string, unknown>)
  ) {
    const envelope = parsedData as Record<string, unknown>;
    type = String(envelope.type) as SSEEventType;
    innerData = envelope.data;
  } else {
    // Non-envelope events (e.g. SSE `event: done` with empty data)
    type = eventType as SSEEventType;
    innerData = parsedData;
  }

  const validTypes: SSEEventType[] = [
    "thinking",
    "tool_calling",
    "poi_result",
    "route_result",
    "plan_summary",
    "text",
    "error",
  ];

  if (!validTypes.includes(type)) {
    // Unknown event type — silently ignore (e.g. "done")
    return null;
  }

  return {
    type,
    data: innerData,
    content: typeof innerData === "string" ? innerData : undefined,
  };
}
