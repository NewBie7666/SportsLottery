from __future__ import annotations


def calibration_buckets(rows: list[dict], buckets: int = 5) -> list[dict]:
    output = []
    for index in range(buckets):
        low = index / buckets
        high = (index + 1) / buckets
        bucket_rows = [row for row in rows if low <= max(row["probs"].values()) < high or (index == buckets - 1 and max(row["probs"].values()) == 1)]
        if not bucket_rows:
            continue
        output.append({
            "bucket": f"{low:.1f}-{high:.1f}",
            "count": len(bucket_rows),
            "avg_confidence": sum(max(row["probs"].values()) for row in bucket_rows) / len(bucket_rows),
            "accuracy": sum(row["predicted"] == row["actual"] for row in bucket_rows) / len(bucket_rows),
        })
    return output
