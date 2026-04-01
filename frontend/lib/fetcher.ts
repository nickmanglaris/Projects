import { api } from "./api";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const fetcher = <T = any>(url: string): Promise<T> => api.get<T>(url);
