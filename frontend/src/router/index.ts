import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { getToken } from "@/api/auth";

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "home",
    component: () => import("@/views/HomeView.vue"),
  },
  {
    path: "/trips/:id",
    name: "trip-detail",
    component: () => import("@/views/TripDetailView.vue"),
    props: (route) => {
      const raw = route.params.id;
      const id = typeof raw === "string" ? Number(raw) : NaN;
      return { id: Number.isFinite(id) ? id : null };
    },
    beforeEnter: () => {
      // Trip detail requires auth — bounce unauthenticated users back to home
      // with a friendly prompt instead of landing on a dead 401 page.
      if (!getToken()) {
        return {
          name: "home",
          query: { auth: "required", redirect: typeof window !== "undefined" ? window.location.pathname : undefined },
        };
      }
      return true;
    },
  },
  {
    path: "/admin",
    component: () => import("@/views/admin/AdminLayout.vue"),
    beforeEnter: async () => {
      const token = getToken();
      if (!token) return { name: "home", query: { auth: "required" } };
      try {
        const res = await fetch("/api/v1/admin/check", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error();
      } catch {
        return { name: "home" };
      }
      return true;
    },
    children: [
      { path: "", redirect: "/admin/models" },
      { path: "models", component: () => import("@/views/admin/ModelConfigView.vue") },
      { path: "users", component: () => import("@/views/admin/UserManagementView.vue") },
      { path: "data", component: () => import("@/views/admin/DataManagementView.vue") },
      { path: "database", component: () => import("@/views/admin/DatabaseConfigView.vue") },
    ],
  },
  {
    path: "/:pathMatch(.*)*",
    name: "not-found",
    component: () => import("@/views/NotFoundView.vue"),
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: (_to, _from, savedPosition) => savedPosition ?? { top: 0 },
});

export default router;
