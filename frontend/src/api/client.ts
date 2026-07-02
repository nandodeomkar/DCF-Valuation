import type {
  CompanyPayload,
  DcfInputs,
  DcfResult,
  MarketData,
  SavedValuation,
} from "./types";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) {
        detail = body.detail
          .map((e: { loc?: unknown[]; msg?: string }) => {
            const field = e.loc?.slice(1).join(".") ?? "";
            return field ? `${field}: ${e.msg}` : e.msg;
          })
          .join("; ");
      }
    } catch {
      // keep statusText
    }
    throw new ApiError(response.status, detail);
  }
  return response.json();
}

export const api = {
  company: (ticker: string, refresh = false) =>
    request<CompanyPayload>(`/api/company/${encodeURIComponent(ticker)}${refresh ? "?refresh=true" : ""}`),
  market: (ticker: string) => request<MarketData>(`/api/market/${encodeURIComponent(ticker)}`),
  runDcf: (inputs: DcfInputs) =>
    request<DcfResult>("/api/dcf", { method: "POST", body: JSON.stringify(inputs) }),
  listValuations: () => request<SavedValuation[]>("/api/valuations"),
  saveValuation: (valuation: SavedValuation) =>
    request<SavedValuation>("/api/valuations", { method: "POST", body: JSON.stringify(valuation) }),
  deleteValuation: (id: number) => request<{ deleted: number }>(`/api/valuations/${id}`, { method: "DELETE" }),
};
