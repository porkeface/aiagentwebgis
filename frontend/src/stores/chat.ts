import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { ChatMessage, POI, SSEEvent } from "@/types";
import { sendChatMessage } from "@/api/agent";
import {
  listChatSessions,
  getChatSession,
  deleteChatSession,
  type ChatSessionSummary,
} from "@/api/chat";
import { useMapStore, type RouteData, type DailyPlan } from "./map";

function generateSessionId(): string {
  return crypto.randomUUID();
}

export const useChatStore = defineStore("chat", () => {
  // ── State ──────────────────────────────────────────────────────────────────
  const messages = ref<ChatMessage[]>([]);
  const sessionId = ref<string>(generateSessionId());
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastUserMessage = ref<string>("");

  // ── Chat history state ────────────────────────────────────────────────────
  const historySessions = ref<ChatSessionSummary[]>([]);
  const historyLoading = ref(false);

  // ── Tool status for UI feedback ────────────────────────────────────────────
  const toolStatus = ref<string | null>(null);

  // ── Getters ────────────────────────────────────────────────────────────────
  const lastMessage = computed(() =>
    messages.value.length > 0 ? messages.value[messages.value.length - 1] : null,
  );
  const messageCount = computed(() => messages.value.length);
  const hasError = computed(() => error.value !== null);

  // ── Helpers ────────────────────────────────────────────────────────────────
  function addMessage(role: ChatMessage["role"], content: string): void {
    const msg: ChatMessage = {
      role,
      content,
      timestamp: new Date().toISOString(),
    };
    messages.value = [...messages.value, msg];
  }

  // ── Actions ────────────────────────────────────────────────────────────────
  async function sendMessage(content: string): Promise<void> {
    if (!content.trim() || loading.value) return;

    // Store for retry
    lastUserMessage.value = content.trim();

    // Add user message
    addMessage("user", content.trim());
    loading.value = true;
    error.value = null;

    // Stream the assistant response token by token.
    // Text chunks arrive in a burst from the SSE reader; we queue them and
    // drain one chunk per animation frame so Vue re-renders between each,
    // producing a visible typewriter effect.
    let assistantAdded = false;
    const textQueue: string[] = [];
    let drainScheduled = false;

    function drainQueue(): void {
      if (textQueue.length === 0) {
        drainScheduled = false;
        return;
      }
      drainScheduled = true;
      requestAnimationFrame(() => {
        const chunk = textQueue.shift();
        if (chunk === undefined) {
          drainScheduled = false;
          return;
        }
        const msgs = messages.value;
        if (msgs.length > 0 && msgs[msgs.length - 1].role === "assistant") {
          const last = msgs[msgs.length - 1];
          messages.value = [
            ...msgs.slice(0, -1),
            { ...last, content: last.content + chunk },
          ];
        }
        drainQueue();
      });
    }
    const mapStore = useMapStore();

    const handleEvent = (event: SSEEvent): void => {

      switch (event.type) {
        case "poi_result": {
          // event.data = { pois, center, zoom } — direct from FormatterNode
          const data = event.data as Record<string, unknown> | null;
          if (!data || typeof data !== "object") break;

          const pois = data.pois as POI[] | undefined;
          const center = data.center as { lng: number; lat: number } | undefined;
          const zoom = data.zoom as number | undefined;

          // Filter out POIs with invalid coordinates rather than rejecting the whole batch.
          // Even an empty valid list should clear stale markers via setPOIs([]).
          const validPois = Array.isArray(pois)
            ? pois.filter(
                (p) =>
                  p &&
                  typeof p.lat === "number" &&
                  typeof p.lng === "number" &&
                  Number.isFinite(p.lat) &&
                  Number.isFinite(p.lng),
              )
            : [];

          if (Array.isArray(pois)) {
            mapStore.setPOIs(validPois);
          }
          if (center && typeof center.lng === "number" && typeof center.lat === "number") {
            mapStore.setCenter(center);
          }
          if (typeof zoom === "number" && Number.isFinite(zoom)) {
            mapStore.setZoom(zoom);
          }
          break;
        }

        case "route_result": {
          // event.data = { daily_plans, polylines } — direct from FormatterNode
          const data = event.data as Record<string, unknown> | null;
          if (!data || typeof data !== "object") break;

          const dailyPlans = data.daily_plans as unknown[] | undefined;
          if (Array.isArray(dailyPlans)) {
            mapStore.setPOIs([]);
            mapStore.setRoutes(dailyPlans as RouteData[]);
            mapStore.clearSelection();
            mapStore.setActiveDay(0);
          }
          break;
        }

        case "plan_summary": {
          // event.data = { city, days } — direct from FormatterNode
          const data = event.data as Record<string, unknown> | null;
          if (!data || typeof data !== "object") break;

          const city = typeof data.city === "string" ? data.city : undefined;
          const days = typeof data.days === "number" ? data.days : undefined;

          if (city !== undefined && days !== undefined) {
            mapStore.setPlanSummary({ city, days });
          }
          break;
        }

        case "text": {
          // Clear tool status on first text token
          toolStatus.value = null;
          // event.data = { content: "actual text" }
          const data = event.data as Record<string, unknown> | null;
          const text = typeof data === "object" && data !== null && typeof data.content === "string"
            ? data.content
            : typeof event.data === "string"
              ? event.data
              : "";
          if (text) {
            if (!assistantAdded) {
              addMessage("assistant", "");
              assistantAdded = true;
            }
            textQueue.push(text);
            if (!drainScheduled) drainQueue();
          }
          break;
        }

        case "error": {
          const errData = event.data as Record<string, unknown> | undefined;
          const errMsg = errData && typeof errData === "object" && "message" in errData
            ? String(errData.message)
            : "抱歉，处理请求时出现错误，请稍后重试。";
          error.value = errMsg;
          break;
        }

        case "thinking":
          toolStatus.value = "AI 正在思考...";
          break;

        case "tool_calling": {
          const data = event.data as Record<string, unknown> | null;
          const content = typeof data === "object" && data !== null && typeof data.content === "string"
            ? data.content
            : "";
          toolStatus.value = content || null;
          break;
        }
      }
    };

    try {
      await sendChatMessage(content.trim(), sessionId.value, handleEvent);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "发送消息失败，请稍后重试。";
      error.value = message;
    } finally {
      loading.value = false;
    }
  }

  function clearMessages(): void {
    messages.value = [];
  }

  function resetSession(): void {
    sessionId.value = generateSessionId();
    messages.value = [];
    error.value = null;
    lastUserMessage.value = "";
  }

  function clearError(): void {
    error.value = null;
  }

  async function retryLastMessage(): Promise<void> {
    const content = lastUserMessage.value?.trim()
    if (!content || loading.value) return
    error.value = null;

    // Find the most recent user message and drop everything from that point
    // forward. This preserves the conversation history before the failed
    // attempt instead of nuking every prior assistant turn.
    const msgs = messages.value;
    const lastUserIdx = (() => {
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i]?.role === "user") return i;
      }
      return -1;
    })();
    if (lastUserIdx >= 0) {
      messages.value = msgs.slice(0, lastUserIdx);
    }

    await sendMessage(content);
  }

  // ── Chat history actions ──────────────────────────────────────────────────
  async function fetchHistory(): Promise<void> {
    historyLoading.value = true;
    try {
      const result = await listChatSessions(1, 50);
      historySessions.value = result.items;
    } catch {
      // silently ignore — user sees empty state
    } finally {
      historyLoading.value = false;
    }
  }

  async function loadSession(threadId: string): Promise<void> {
    const session = await getChatSession(threadId);
    const mapStore = useMapStore();

    // Restore messages
    messages.value = (session.messages || []).map((m) => ({
      role: m.role as ChatMessage["role"],
      content: m.content,
      timestamp: m.timestamp || new Date().toISOString(),
    }));

    // Resume from this thread so new messages continue the conversation
    sessionId.value = threadId;

    // Restore map state from snapshot
    const agentState = session.agent_state_json;
    if (agentState && typeof agentState === "object") {
      const snapshot = (agentState as Record<string, unknown>).map_snapshot as Record<string, unknown> | undefined;
      if (snapshot) {
        const pois = Array.isArray(snapshot.pois) ? snapshot.pois as POI[] : [];
        const routes = Array.isArray(snapshot.routes)
          ? (snapshot.routes as DailyPlan[])
          : [];
        const planSummary = snapshot.plan_summary as { city: string; days: number } | undefined;

        if (pois.length > 0) mapStore.setPOIs(pois);
        if (routes.length > 0) {
          mapStore.setRoutes(routes);
          mapStore.setActiveDay(0);
        }
        if (planSummary) mapStore.setPlanSummary(planSummary);
      }
    }
  }

  async function removeHistorySession(threadId: string): Promise<void> {
    await deleteChatSession(threadId);
    historySessions.value = historySessions.value.filter(
      (s) => s.thread_id !== threadId,
    );
  }

  function startNewSession(): void {
    const mapStore = useMapStore();
    resetSession();
    mapStore.clearMap();
  }

  return {
    // state
    messages,
    sessionId,
    loading,
    error,
    lastUserMessage,
    historySessions,
    historyLoading,
    toolStatus,
    // getters
    lastMessage,
    messageCount,
    hasError,
    // actions
    sendMessage,
    clearMessages,
    resetSession,
    clearError,
    retryLastMessage,
    fetchHistory,
    loadSession,
    removeHistorySession,
    startNewSession,
  };
});
