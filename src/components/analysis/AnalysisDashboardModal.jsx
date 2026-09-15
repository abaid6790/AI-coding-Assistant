import { useEffect, useState } from "react";
import { api, ApiError } from "../../services/api.js";
import Modal from "../common/Modal.jsx";
import { ScoreBar, FindingsList, SEVERITY_STYLES } from "./CodeAnalysisDisplay.jsx";

function Sparkline({ values }) {
  if (!values || values.length < 2) return null;
  const max = Math.max(...values, 100);
  return (
    <div className="flex h-8 items-end gap-0.5">
      {values.map((v, i) => (
        <div
          key={i}
          className="w-2 rounded-t bg-accent-500/70"
          style={{ height: `${Math.max((v / max) * 100, 4)}%` }}
          title={`${v}/100`}
        />
      ))}
    </div>
  );
}

export default function AnalysisDashboardModal({ projectId, onOpenReview, onClose }) {
  const [data, setData] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedReviewId, setExpandedReviewId] = useState(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const [analysis, reviewsData] = await Promise.all([
          api.getProjectAnalysis(projectId),
          api.listProjectReviews(projectId),
        ]);
        setData(analysis);
        setReviews(reviewsData.reviews);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Could not load analysis.");
      } finally {
        setLoading(false);
      }
    })();
  }, [projectId]);

  return (
    <Modal title="Code Analysis Dashboard" onClose={onClose}>
      <div className="max-h-[65vh] space-y-5 overflow-y-auto pr-1">
        {loading && <p className="text-xs text-gray-500">Loading…</p>}
        {error && <p className="text-xs text-red-400">{error}</p>}

        {data && !data.latest && (
          <p className="rounded-md border border-dashed border-surface-700 p-6 text-center text-xs text-gray-500">
            No reviews yet for this project. Run "Review" from the Analyze menu on a file to populate this dashboard.
          </p>
        )}

        {data && data.latest && (
          <>
            <div>
              <p className="mb-2 text-[11px] uppercase tracking-wide text-gray-500">
                Latest scores <span className="normal-case text-gray-600">(AI-assisted estimate, not an authoritative certification)</span>
              </p>
              <div className="grid grid-cols-2 gap-4 rounded-md border border-surface-700 p-3">
                <ScoreBar label="Quality" value={data.latest.quality_score} />
                <ScoreBar label="Security" value={data.latest.security_score} />
                <ScoreBar label="Performance" value={data.latest.performance_score} />
                <ScoreBar label="Maintainability" value={data.latest.maintainability_score} />
              </div>
              {data.latest.complexity_summary && (
                <p className="mt-2 text-xs text-gray-400">
                  <b className="text-gray-300">Complexity:</b> {data.latest.complexity_summary}
                </p>
              )}
            </div>

            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="rounded-md border border-surface-700 p-3">
                <p className="text-lg font-semibold">{data.issues_found}</p>
                <p className="text-[11px] text-gray-500">Issues found (latest review)</p>
              </div>
              <div className="rounded-md border border-surface-700 p-3">
                <p className="text-lg font-semibold">{data.reviews_count}</p>
                <p className="text-[11px] text-gray-500">Reviews run</p>
              </div>
              <div className="rounded-md border border-surface-700 p-3">
                <p className="text-lg font-semibold">{data.tests_count + data.documents_count}</p>
                <p className="text-[11px] text-gray-500">Tests + docs generated</p>
              </div>
            </div>

            {Object.keys(data.issues_by_severity).length > 0 && (
              <div>
                <p className="mb-1.5 text-[11px] uppercase tracking-wide text-gray-500">Issues by severity</p>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(data.issues_by_severity).map(([severity, count]) => (
                    <span key={severity} className={`rounded-full border px-2.5 py-1 text-[11px] ${SEVERITY_STYLES[severity] || SEVERITY_STYLES.Suggestion}`}>
                      {severity}: {count}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {data.history.length > 1 && (
              <div>
                <p className="mb-1.5 text-[11px] uppercase tracking-wide text-gray-500">Quality trend (oldest → newest)</p>
                <Sparkline values={data.history.map((h) => h.quality_score).filter((v) => v !== null)} />
              </div>
            )}
          </>
        )}

        {reviews.length > 0 && (
          <div>
            <p className="mb-1.5 text-[11px] uppercase tracking-wide text-gray-500">Recent reviews</p>
            <div className="space-y-1.5">
              {reviews.map((r) => (
                <div key={r.id} className="rounded-md border border-surface-700">
                  <button
                    onClick={() => setExpandedReviewId(expandedReviewId === r.id ? null : r.id)}
                    className="flex w-full items-center justify-between px-3 py-2 text-left text-xs text-gray-300 hover:bg-surface-800"
                  >
                    <span>{r.language || "unknown"} · {new Date(r.created_at).toLocaleString()}</span>
                    <span className="text-gray-500">{r.findings.length} issue{r.findings.length === 1 ? "" : "s"}</span>
                  </button>
                  {expandedReviewId === r.id && (
                    <div className="border-t border-surface-800 p-3">
                      <FindingsList findings={r.findings} />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
