import { getToken } from "./auth";
import type { SSEEvent, SSEEventType } from "../types";

const BASE_URL = "/api/v1";

export async function sendChatMessage(
  message: string,
  sessionId: string,
  onEvent: (event: SSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Inner controller is the safety-net timeout. The optional caller-supplied
  // signal is chained in via `addEventListener` so a `sendMessage` in the
  // store can cancel an in-flight request when the user starts a new turn.
  const controller = new AbortController();
  const timeoutMs = 300_000; // 5 minutes frontend timeout
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  // Propagate caller aborts to the inner controller.
  const onCallerAbort = () => controller.abort();
  if (signal) {
    if (signal.aborted) {
      controller.abort();
    } else {
      signal.addEventListener("abort", onCallerAbort, { once: true });
    }
  }

  try {
    const response = await fetch(`${BASE_URL}/agent/chat`, {
      method: "POST",
      headers,
      body: JSON.stringify({ message, session_id: sessionId }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let detail: unknown;
      try {
        detail = await response.json();
      } catch {
        // ignore parse error
      }
      const errMsg =
        detail && typeof detail === "object" && "detail" in detail
          ? String((detail as { detail: unknown }).detail)
          : `Chat request failed with status ${response.status}`;
      onEvent({ type: "error", data: { status: response.status, message: errMsg } });
      return;
    }

    if (!response.body) {
      onEvent({ type: "error", data: { message: "Response body is null" } });
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          const event = parseSSEEvent(part);
          if (event) {
            onEvent(event);
          }
        }
      }

      // Flush any remaining bytes in the decoder's buffer (B-H2 fix).
      buffer += decoder.decode();
      if (buffer.trim()) {
        const event = parseSSEEvent(buffer);
        if (event) {
          onEvent(event);
        }
      }
    } finally {
      // Release the reader on early exit so the underlying socket is freed
      // (otherwise a cancelled stream can hold a connection open for ~5 min).
      try {
        await reader.cancel();
      } catch {
        // best-effort
      }
    }
  } catch (err: unknown) {
    clearTimeout(timeoutId);
    if (err instanceof DOMException && err.name === "AbortError") {
      // Differentiate caller abort from timeout. Caller-initiated abort
      // (e.g. user started a new conversation) is silent — the store has
      // already cleared its own state. Emitting an error event here would
      // race with the new turn and briefly flash "已取消" in the UI.
      if (!signal?.aborted) {
        onEvent({ type: "error", data: { message: "请求超时，请稍后重试" } });
      }
    } else {
      const message = err instanceof Error ? err.message : "网络请求失败";
      onEvent({ type: "error", data: { message } });
    }
  } finally {
    if (signal) signal.removeEventListener("abort", onCallerAbort);
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
    "progress",
    "done",
    // Pipeline events (previously dropped — see B-4 audit fix)
    "intent_detected",
    "searching",
    "candidates_ready",
    "scoring",
    "clustering",
    "day_routing",
    // Critic / validation events (previously dropped)
    "critic_review",
    "critic_result",
    "routing",
    "day_routed",
    "validating",
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
