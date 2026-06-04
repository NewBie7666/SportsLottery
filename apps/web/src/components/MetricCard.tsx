type Props = {
  label: string;
  value: string;
  wide?: boolean;
};

export default function MetricCard({ label, value, wide = false }: Props) {
  return (
    <div className={wide ? "metric metric-wide" : "metric"}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
