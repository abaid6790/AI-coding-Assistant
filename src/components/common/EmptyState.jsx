export default function EmptyState({ icon = "📭", title, subtitle, action }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-surface-700 p-10 text-center">
      <span className="text-2xl opacity-70">{icon}</span>
      <p className="text-sm font-medium text-gray-300">{title}</p>
      {subtitle && <p className="max-w-xs text-xs text-gray-500">{subtitle}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
