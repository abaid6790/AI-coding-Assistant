import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../../services/api.js";
import { AuthShell, Banner, FieldError, inputClass, primaryButtonClass } from "../../components/auth/AuthShell.jsx";

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "", display_name: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [passwordErrors, setPasswordErrors] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setPasswordErrors([]);
    setSubmitting(true);
    try {
      await api.register(form);
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
      <AuthShell title="Check your email">
        <p className="text-sm text-gray-300">
          We sent a verification link to <span className="font-medium">{form.email}</span>. Click it to
          activate your account, then{" "}
          <button onClick={() => navigate("/login")} className="text-accent-500 hover:underline">
            sign in
          </button>
          .
        </p>
      </AuthShell>
    );
  }

  return (
    <AuthShell title="Create your account" subtitle="Start building with AI-assisted code review.">
      <Banner>{error}</Banner>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-400">Name (optional)</label>
          <input className={inputClass} value={form.display_name} onChange={set("display_name")} />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-400">Email</label>
          <input
            type="email"
            required
            className={inputClass}
            value={form.email}
            onChange={set("email")}
            autoComplete="email"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-400">Password</label>
          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              required
              className={inputClass}
              value={form.password}
              onChange={set("password")}
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
          <p className="mt-1 text-xs text-gray-500">At least 8 characters, with a letter and a number.</p>
        </div>
        <button type="submit" disabled={submitting} className={primaryButtonClass}>
          {submitting ? "Creating account…" : "Create account"}
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-gray-400">
        Already have an account?{" "}
        <Link to="/login" className="text-accent-500 hover:underline">
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
