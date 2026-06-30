import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";
import { getToken } from "@/api/auth";

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "home",
    component: () => import("@/views/HomeView.vue"),
  },
  {
    path: "/trip/:id",
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
