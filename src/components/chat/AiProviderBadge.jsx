import { useEffect, useState } from "react";
import { api } from "../../services/api.js";

export default function AiProviderBadge() {
  const [providers, setProviders] = useState(null);

  useEffect(() => {
    api.listAiProviders().then((data) => setProviders(data.providers)).catch(() => setProviders([]));
  }, []);

  if (!providers) return null;

  const active = providers.find((p) => p.is_default);
  const configured = active?.configured;

  return (
    <span
      title={
        configured
          ? `${active.name} is configured and set as the default provider`
          : `${active?.name || "Default provider"} has no API key configured yet — add one to .env`
      }
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs ${
        configured
          ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
          : "border-amber-500/30 bg-amber-500/10 text-amber-300"
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${configured ? "bg-emerald-400" : "bg-amber-400"}`} />
      AI: {active?.name || "none"} {configured ? "ready" : "not configured"}
    </span>
  );
}
