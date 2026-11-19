import React, { useState } from "react";
import { login, signup } from "../services/api";

export default function AuthPage({ onLogin }) {
    const [mode, setMode] = useState("login");
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    async function handleSubmit(event) {
        event.preventDefault();
        setError("");
        setLoading(true);

        try {
            const normalizedEmail = email.trim().toLowerCase();

            if (mode === "signup") {
                await signup({
                    name: name.trim(),
                    email: normalizedEmail,
                    password,
                });
            }

            const result = await login(normalizedEmail, password);
            onLogin(result.user);
        } catch (err) {
            setError(err.message || "Authentication failed.");
        } finally {
            setLoading(false);
        }
    }

    function changeMode(nextMode) {
        setMode(nextMode);
        setError("");
        setPassword("");
    }

    return (
        <main className="auth-page">

            {/* Left branding panel */}
            <section className="auth-brand-panel">
                <div className="auth-brand-header">
                    <div className="auth-logo">IQ</div>

                    <span className="auth-brand-name">
                        IntelliQuery
                    </span>
                </div>

                <div className="auth-brand-content">
                    <p className="auth-brand-label">
                        AI-POWERED DOCUMENT INTELLIGENCE
                    </p>

                    <h1>
                        Your documents.
                        <br />
                        Your knowledge.
                        <br />
                        <span>One intelligent assistant.</span>
                    </h1>

                    <p className="auth-brand-description">
                        Upload your documents, ask questions in natural
                        language, and get intelligent answers backed by
                        relevant information from your files.
                    </p>

                    <div className="auth-brand-divider" />

                    <p className="auth-brand-caption">
                        Intelligent Query Resolution System
                    </p>
                </div>

                <div className="auth-brand-bottom">
                    <span>AI-powered information access</span>
                    <span>Secure workspace</span>
                </div>
            </section>

            {/* Right authentication panel */}
            <section className="auth-form-panel">
                <div className="auth-card">

                    <div className="auth-card-heading">
                        <p>
                            Welcome to <span>IntelliQuery</span>
                        </p>

                        <h2>
                            {mode === "login"
                                ? "Sign in"
                                : "Create account"}
                        </h2>

                        <p className="auth-subtitle">
                            {mode === "login"
                                ? "Enter your details to access your workspace."
                                : "Create an account to get started."}
                        </p>
                    </div>

                    <div className="auth-card-accent">
                        IQ
                    </div>

                    <form
                        onSubmit={handleSubmit}
                        className="auth-form"
                    >

                        {mode === "signup" && (
                            <label>
                                Full name

                                <input
                                    type="text"
                                    value={name}
                                    onChange={(event) =>
                                        setName(event.target.value)
                                    }
                                    minLength={2}
                                    maxLength={100}
                                    autoComplete="name"
                                    required
                                    placeholder="Enter your full name"
                                />
                            </label>
                        )}

                        <label>
                            Email address

                            <input
                                type="email"
                                value={email}
                                onChange={(event) =>
                                    setEmail(event.target.value)
                                }
                                autoComplete="email"
                                required
                                placeholder="Enter your email address"
                            />
                        </label>

                        <label>
                            Password

                            <div className="auth-password-wrapper">
                                <input
                                    type={showPassword ? "text" : "password"}
                                    value={password}
                                    onChange={(event) =>
                                        setPassword(event.target.value)
                                    }
                                    minLength={12}
                                    maxLength={128}
                                    autoComplete={
                                        mode === "login"
                                            ? "current-password"
                                            : "new-password"
                                    }
                                    required
                                    placeholder="Enter your password"
                                />

                                <button
                                    type="button"
                                    className="auth-password-toggle"
                                    onClick={() =>
                                        setShowPassword(!showPassword)
                                    }
                                >
                                    {showPassword ? "Hide" : "Show"}
                                </button>
                            </div>
                        </label>

                        {error && (
                            <p className="auth-error" role="alert">
                                {error}
                            </p>
                        )}

                        <button
                            type="submit"
                            className="auth-submit"
                            disabled={loading}
                        >
                            {loading
                                ? "Please wait..."
                                : mode === "login"
                                    ? "Sign in"
                                    : "Create account"}
                        </button>
                    </form>

                    <div className="auth-switch">
                        {mode === "login" ? (
                            <>
                                <span>Don't have an account?</span>

                                <button
                                    type="button"
                                    onClick={() => changeMode("signup")}
                                >
                                    Sign up
                                </button>
                            </>
                        ) : (
                            <>
                                <span>Already have an account?</span>

                                <button
                                    type="button"
                                    onClick={() => changeMode("login")}
                                >
                                    Sign in
                                </button>
                            </>
                        )}
                    </div>

                    <p className="auth-security-note">
                        Your account is verified by the backend before
                        access is granted.
                    </p>

                </div>
            </section>
        </main>
    );
}
