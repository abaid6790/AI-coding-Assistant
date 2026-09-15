import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../../services/api.js";
import { AuthShell, Banner, FieldError, inputClass, primaryButtonClass } from "../../components/auth/AuthShell.jsx";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const navigate = useNavigate();

  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [passwordErrors, setPasswordErrors] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setPasswordErrors([]);
    setSubmitting(true);
    try {
      await api.resetPassword(token, password);
      setDone(true);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        if (err.fieldErrors?.password) setPasswordErrors(err.fieldErrors.password);
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (done) {
    return (
      <AuthShell title="Password reset">
        <p className="text-sm text-gray-300">
          Your password has been changed.{" "}
          <button onClick={() => navigate("/login")} className="text-accent-500 hover:underline">
            Sign in
          </button>
        </p>
      </AuthShell>
    );
  }

  return (
    <AuthShell title="Choose a new password">
      <Banner>{error}</Banner>
      {!token && <p className="mb-4 text-sm text-red-400">Missing reset token — use the link from your email.</p>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-400">New password</label>
          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              required
              className={inputClass}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
            />
            <button
              type="button"
              onClick={() => setShowPassword((s) => !s)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-gray-400 hover:text-gray-200"
            >
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>
          {passwordErrors.map((msg) => (
            <FieldError key={msg} message={msg} />
          ))}
        </div>
        <button type="submit" disabled={submitting || !token} className={primaryButtonClass}>
          {submitting ? "Saving…" : "Reset password"}
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-gray-400">
        <Link to="/login" className="text-accent-500 hover:underline">
          Back to sign in
        </Link>
      </p>
    </AuthShell>
  );
}
