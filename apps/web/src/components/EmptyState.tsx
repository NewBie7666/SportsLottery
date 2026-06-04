import type { DataResult } from "../lib/loadData";

type Props = {
  result: DataResult<unknown>;
};

export default function EmptyState({ result }: Props) {
  if (result.status === "loading") {
    return <p className="empty">正在读取数据...</p>;
  }
  if (result.status === "empty") {
    return <p className="empty">{result.message}</p>;
  }
  return null;
}
