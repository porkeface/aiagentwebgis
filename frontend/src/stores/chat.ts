import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { ChatMessage, POI, SSEEvent } from "@/types";
import { sendChatMessage } from "@/api/agent";
import { useMapStore, type RouteData } from "./map";

function generateSessionId(): string {
  return crypto.randomUUID();
}

export const useChatStore = defineStore("chat", () => {
  // ── State ──────────────────────────────────────────────────────────────────
  const messages = ref<ChatMessage[]>([]);
  const sessionId = ref<string>(generateSessionId());
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastUserMessage = ref<string>(""); // Store last message for retry

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

    // Accumulate text for the assistant response
    let assistantText = "";

    const handleEvent = (event: SSEEvent): void => {
      const mapStore = useMapStore();

      switch (event.type) {
        case "poi_result": {
          // Backend sends: { pois: POI[], center: {lng, lat}, zoom?: number }
          const payload = event.data as Record<string, unknown> | null;
          if (!payload || typeof payload !== "object") break;

          const pois = payload.pois as POI[] | undefined;
          const center = payload.center as { lng: number; lat: number } | undefined;
          const zoom = payload.zoom as number | undefined;

          if (Array.isArray(pois) && pois.length > 0) {
            mapStore.setPOIs(pois);
          }
          if (center && typeof center.lng === "number" && typeof center.lat === "number") {
            mapStore.setCenter(center);
          }
          if (typeof zoom === "number") {
            mapStore.setZoom(zoom);
          }
          break;
        }

        case "route_result": {
          // Backend sends: { daily_plans: DayPlan[], polylines: Polyline[] }
          const payload = event.data as Record<string, unknown> | null;
          if (!payload || typeof payload !== "object") break;

          const dailyPlans = payload.daily_plans as unknown[] | undefined;
          if (Array.isArray(dailyPlans)) {
            mapStore.setRoutes(dailyPlans as RouteData[]);
          }
          break;
        }

        case "plan_summary": {
          // Backend sends: { city: string, days: number }
          const payload = event.data as Record<string, unknown> | null;
          if (!payload || typeof payload !== "object") break;

          const city = typeof payload.city === "string" ? payload.city : undefined;
          const days = typeof payload.days === "number" ? payload.days : undefined;

          if (city !== undefined && days !== undefined) {
            mapStore.setPlanSummary({ city, days });
          }
          break;
        }

        case "text": {
          const text = typeof event.content === "string"
            ? event.content
            : typeof event.data === "string"
              ? event.data
              : "";
          if (text) {
            assistantText += text;
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
        case "tool_calling":
          // These events are informational — no state update needed
          break;
      }
    };

    try {
      await sendChatMessage(content.trim(), sessionId.value, handleEvent);

      // Add the accumulated assistant message
      if (assistantText.trim()) {
        addMessage("assistant", assistantText.trim());
      }
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
    if (!lastUserMessage.value || loading.value) return;
    error.value = null;
    // Remove the last user message and any trailing error/assistant messages
    // from the failed attempt before re-sending to avoid duplicates.
    const msgs = messages.value;
    let cutIndex = msgs.length;
    // Walk backwards: remove trailing assistant/error messages, then the user message.
    while (cutIndex > 0 && msgs[cutIndex - 1].role !== "user") {
      cutIndex--;
    }
    if (cutIndex > 0 && msgs[cutIndex - 1].role === "user") {
      // cutIndex now points at the last user message — remove it too.
    }
    messages.value = msgs.slice(0, cutIndex);
    await sendMessage(lastUserMessage.value);
  }

  return {
    // state
    messages,
    sessionId,
    loading,
    error,
    lastUserMessage,
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
  };
});
