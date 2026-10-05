export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    credentials: "same-origin",
    cache: "no-store",
    headers: { ...(init.body ? { "Content-Type": "application/json" } : {}), ...init.headers },
  });
  if (!response.ok) {
    throw new ApiError(response.status, response.status === 409
      ? "The board changed elsewhere. Review the refreshed board and try again."
      : response.status === 429 ? "AI rate limit reached. Please try again later."
      : response.status === 504 ? "AI request timed out. Please try again."
      : path === "/chat" ? "AI request failed. Review the board before retrying; your message is kept."
      : "Unable to save changes. Please try again.");
  }
  return response.json() as Promise<T>;
}
