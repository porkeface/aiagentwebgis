import { defineStore } from "pinia";
import { ref } from "vue";
import * as adminApi from "@/api/admin";
import type { ConfigData, ConfigUpdateResult, AdminUser, AdminTrip, AdminSession, AdminPOI, AdminStats } from "@/api/admin";

export const useAdminStore = defineStore("admin", () => {
  const loading = ref(false);
  const config = ref<ConfigData | null>(null);
  const stats = ref<AdminStats | null>(null);
  const users = ref<AdminUser[]>([]);
  const trips = ref<AdminTrip[]>([]);
  const pois = ref<AdminPOI[]>([]);
  const sessions = ref<AdminSession[]>([]);

  async function fetchConfig(): Promise<void> {
    loading.value = true;
    try {
      config.value = await adminApi.getConfig();
    } finally {
      loading.value = false;
    }
  }

  async function saveConfig(updates: Record<string, string>): Promise<ConfigUpdateResult> {
    loading.value = true;
    try {
      const result = await adminApi.updateConfig(updates);
      await fetchConfig();
      return result;
    } finally {
      loading.value = false;
    }
  }

  async function fetchStats(): Promise<void> {
    loading.value = true;
    try {
      stats.value = await adminApi.getStats();
    } finally {
      loading.value = false;
    }
  }

  async function fetchUsers(page = 1): Promise<void> {
    loading.value = true;
    try {
      const data = await adminApi.listUsers(page, 50);
      users.value = data.items;
    } finally {
      loading.value = false;
    }
  }

  async function updateUser(id: number, fields: { is_admin?: boolean; password?: string }): Promise<void> {
    await adminApi.patchUser(id, fields);
    await fetchUsers();
  }

  async function removeUser(id: number): Promise<void> {
    await adminApi.deleteUser(id);
    users.value = users.value.filter((u) => u.id !== id);
  }

  async function fetchTrips(page = 1): Promise<void> {
    loading.value = true;
    try {
      const data = await adminApi.listAllTrips(page, 50);
      trips.value = data.items;
    } finally {
      loading.value = false;
    }
  }

  async function removeTrip(id: number): Promise<void> {
    await adminApi.deleteAnyTrip(id);
    trips.value = trips.value.filter((t) => t.id !== id);
  }

  async function fetchSessions(page = 1): Promise<void> {
    loading.value = true;
    try {
      const data = await adminApi.listAllSessions(page, 50);
      sessions.value = data.items;
    } finally {
      loading.value = false;
    }
  }

  async function fetchPois(page = 1): Promise<void> {
    loading.value = true;
    try {
      const data = await adminApi.listAllPois(page, 50);
      pois.value = data.items;
    } finally {
      loading.value = false;
    }
  }

  async function removeSession(id: number): Promise<void> {
    await adminApi.deleteAnySession(id);
    sessions.value = sessions.value.filter((s) => s.id !== id);
  }

  return {
    loading, config, stats, users, trips, pois, sessions,
    fetchConfig, saveConfig, fetchStats,
    fetchUsers, updateUser, removeUser,
    fetchTrips, removeTrip,
    fetchSessions, removeSession,
    fetchPois,
  };
});
