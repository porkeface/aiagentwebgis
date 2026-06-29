import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { ChatMessage, POI, SSEEvent } from "@/types";
import { sendChatMessage } from "@/api/agent";
import { useMapStore } from "./map";

function generateSessionId(): string {
  return crypto.randomUUID();
}

export const useChatStore = defineStore("chat", () => {
  // ── State ──────────────────────────────────────────────────────────────────
  const messages = ref<ChatMessage[]>([]);
  const sessionId = ref<string>(generateSessionId());
  const loading = ref(false);
  const error = ref<string | null>(null);

  // ── Getters ────────────────────────────────────────────────────────────────
  const lastMessage = computed(() =>
    messages.value.length > 0 ? messages.value[messages.value.length - 1] : null,
  );
  const messageCount = computed(() => messages.value.length);

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
          // event.data should be POI[] or a single POI
          if (Array.isArray(event.data)) {
            mapStore.setPOIs(event.data as POI[]);
          } else if (event.data && typeof event.data === "object") {
            mapStore.setPOIs([event.data as POI]);
          }
          break;
        }

        case "route_result": {
          if (Array.isArray(event.data)) {
            mapStore.setRoutes(event.data);
          } else if (event.data && typeof event.data === "object") {
            mapStore.setRoutes([event.data]);
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
            : "An error occurred";
          error.value = errMsg;
          break;
        }

        case "thinking":
        case "tool_calling":
        case "plan_summary":
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
      const message = err instanceof Error ? err.message : "Failed to send message";
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
  }

  function clearError(): void {
    error.value = null;
  }

  return {
    // state
    messages,
    sessionId,
    loading,
    error,
    // getters
    lastMessage,
    messageCount,
    // actions
    sendMessage,
    clearMessages,
    resetSession,
    clearError,
  };
});
