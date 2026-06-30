import { request, authHeaders } from "./http";
import type { POI } from "../types";

export interface POISearchParams {
  city: string;
  category?: string;
  keyword?: string;
  page?: number;
  size?: number;
}

interface POISearchResponse {
  success: boolean;
  data: {
    total: number;
    items: POI[];
  };
}

export async function searchPOIs(params: POISearchParams): Promise<POI[]> {
  const query = new URLSearchParams();
  query.set("city", params.city);
  if (params.category) query.set("category", params.category);
  if (params.keyword) query.set("keyword", params.keyword);
  if (params.page !== undefined) query.set("page", String(params.page));
  if (params.size !== undefined) query.set("size", String(params.size));

  const res = await request<POISearchResponse>(
    `/poi/search?${query.toString()}`,
    { method: "GET", headers: authHeaders() },
  );
  return res.data.items;
}
