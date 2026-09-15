export default function Spinner({ label, size = "sm" }) {
  const dims = size === "sm" ? "h-3.5 w-3.5" : "h-6 w-6";
  return (
    <span className="inline-flex items-center gap-2 text-xs text-gray-500">
      <span className={`${dims} animate-spin rounded-full border-2 border-gray-600 border-t-accent-500`} />
      {label && <span>{label}</span>}
    </span>
  );
}
