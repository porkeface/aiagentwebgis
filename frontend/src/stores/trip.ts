import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { Trip, TripDetail } from "@/types";
import {
  listTrips,
  getTrip,
  createTrip as apiCreateTrip,
  updateTrip as apiUpdateTrip,
  deleteTrip as apiDeleteTrip,
} from "@/api/trip";
import type { TripCreateData, TripUpdateData } from "@/api/trip";

export const useTripStore = defineStore("trip", () => {
  // ── State ──────────────────────────────────────────────────────────────────
  const trips = ref<Trip[]>([]);
  const currentTrip = ref<TripDetail | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // ── Getters ────────────────────────────────────────────────────────────────
  const tripCount = computed(() => trips.value.length);

  // ── Actions ────────────────────────────────────────────────────────────────
  async function fetchTrips(page = 1, size = 20): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      trips.value = await listTrips(page, size);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to fetch trips";
      error.value = message;
    } finally {
      loading.value = false;
    }
  }

  async function fetchTrip(id: number): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      currentTrip.value = await getTrip(id);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to fetch trip";
      error.value = message;
    } finally {
      loading.value = false;
    }
  }

  async function createTrip(data: TripCreateData): Promise<Trip | null> {
    loading.value = true;
    error.value = null;
    try {
      const trip = await apiCreateTrip(data);
      trips.value = [...trips.value, trip];
      return trip;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to create trip";
      error.value = message;
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function updateTrip(id: number, data: TripUpdateData): Promise<Trip | null> {
    loading.value = true;
    error.value = null;
    try {
      const updated = await apiUpdateTrip(id, data);
      trips.value = trips.value.map((t) => (t.id === id ? updated : t));
      return updated;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to update trip";
      error.value = message;
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function deleteTrip(id: number): Promise<boolean> {
    loading.value = true;
    error.value = null;
    try {
      await apiDeleteTrip(id);
      trips.value = trips.value.filter((t) => t.id !== id);
      if (currentTrip.value?.id === id) {
        currentTrip.value = null;
      }
      return true;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to delete trip";
      error.value = message;
      return false;
    } finally {
      loading.value = false;
    }
  }

  function clearError(): void {
    error.value = null;
  }

  function clearCurrentTrip(): void {
    currentTrip.value = null;
  }

  return {
    // state
    trips,
    currentTrip,
    loading,
    error,
    // getters
    tripCount,
    // actions
    fetchTrips,
    fetchTrip,
    createTrip,
    updateTrip,
    deleteTrip,
    clearError,
    clearCurrentTrip,
  };
});
