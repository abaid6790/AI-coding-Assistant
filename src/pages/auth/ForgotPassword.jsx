import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../services/api.js";
import { AuthShell, inputClass, primaryButtonClass } from "../../components/auth/AuthShell.jsx";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.forgotPassword(email);
    } finally {
      setSubmitting(false);
      setSent(true);
    }
  };

  return (
    <AuthShell title="Reset your password">
      {sent ? (
        <p className="text-sm text-gray-300">
          If an account exists for that email, a reset link is on its way.{" "}
          <Link to="/login" className="text-accent-500 hover:underline">
            Back to sign in
          </Link>
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-400">Email</label>
            <input
              type="email"
              required
              className={inputClass}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <button type="submit" disabled={submitting} className={primaryButtonClass}>
            {submitting ? "Sending…" : "Send reset link"}
          </button>
        </form>
      )}
    </AuthShell>
  );
}
