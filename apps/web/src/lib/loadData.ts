export type DataResult<T> =
  | { status: "loading" }
  | { status: "ready"; data: T }
  | { status: "empty"; message: string };

export async function loadJson<T>(path: string, hint: string): Promise<DataResult<T>> {
  try {
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) {
      return { status: "empty", message: `暂无数据，${hint}` };
    }
    return { status: "ready", data: (await response.json()) as T };
  } catch {
    return { status: "empty", message: `暂无数据，${hint}` };
  }
}
