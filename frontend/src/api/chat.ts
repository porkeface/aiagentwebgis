import { request } from "./http";
import { getToken } from "./auth";

export interface ChatSessionSummary {
  id: number;
  thread_id: string;
  title: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChatSessionDetail {
  id: number;
  thread_id: string;
  title: string | null;
  messages: Array<{ role: string; content: string; timestamp: string }>;
  agent_state_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

interface Envelope<T> {
  success: boolean;
  data: T;
}

interface PagedEnvelope<T> {
  success: boolean;
  data: {
    total: number;
    items: T[];
  };
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

export async function listChatSessions(
  page = 1,
  size = 20,
): Promise<{ total: number; items: ChatSessionSummary[] }> {
  const query = new URLSearchParams({
    page: String(page),
    size: String(size),
  });
  const res = await request<PagedEnvelope<ChatSessionSummary>>(
    `/chat-sessions?${query.toString()}`,
    { headers: authHeaders() },
  );
  return res.data;
}

export async function getChatSession(
  threadId: string,
): Promise<ChatSessionDetail> {
  const res = await request<Envelope<ChatSessionDetail>>(
    `/chat-sessions/${encodeURIComponent(threadId)}`,
    { headers: authHeaders() },
  );
  return res.data;
}

export async function deleteChatSession(threadId: string): Promise<void> {
  await request<Envelope<{ deleted: boolean }>>(
    `/chat-sessions/${encodeURIComponent(threadId)}`,
    { method: "DELETE", headers: authHeaders() },
  );
}
