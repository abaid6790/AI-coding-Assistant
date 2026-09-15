import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../../services/api.js";
import { AuthShell } from "../../components/auth/AuthShell.jsx";

export default function VerifyEmail() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const [status, setStatus] = useState("verifying"); // verifying | success | error
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("Missing verification token.");
      return;
    }
    api
      .verifyEmail(token)
      .then(() => setStatus("success"))
      .catch((err) => {
        setStatus("error");
        setMessage(err instanceof ApiError ? err.message : "Verification failed.");
      });
  }, [token]);

  return (
    <AuthShell title="Email verification">
      {status === "verifying" && <p className="text-sm text-gray-400">Verifying your email…</p>}
      {status === "success" && (
        <p className="text-sm text-gray-300">
          Your email is verified.{" "}
          <Link to="/login" className="text-accent-500 hover:underline">
            Sign in
          </Link>
        </p>
      )}
      {status === "error" && (
        <div className="text-sm text-gray-300">
          <p className="text-red-400">{message}</p>
          <p className="mt-2">
            <Link to="/resend-verification" className="text-accent-500 hover:underline">
              Request a new link
            </Link>
          </p>
        </div>
      )}
    </AuthShell>
  );
}
