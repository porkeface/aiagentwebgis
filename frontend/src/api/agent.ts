import { getToken } from "./auth";
import type { SSEEvent } from "../types";

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

  // Process any remaining buffer
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

  const validTypes = [
    "thinking",
    "tool_calling",
    "poi_result",
    "route_result",
    "plan_summary",
    "text",
    "error",
  ] as const;

  const type = validTypes.includes(eventType as (typeof validTypes)[number])
    ? (eventType as (typeof validTypes)[number])
    : "text";

  return {
    type,
    data: parsedData,
    content: typeof parsedData === "string" ? parsedData : undefined,
  };
}
