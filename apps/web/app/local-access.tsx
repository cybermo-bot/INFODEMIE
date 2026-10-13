"use client";
import { useState } from "react";
import { post } from "./api";

export function LocalSetup({ onComplete }: { onComplete: () => void }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <div className="login local-login">
      <div className="login-form">
        <div className="login-card">
          <span className="eyebrow teal">PNSI · INSTALLATION LOCALE</span>
          <h1>Créer ton espace</h1>
          <p>
            Cette base démarre vide. Le compte créé ici administrera ton
            organisation.
          </p>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              setError("");
              const data = Object.fromEntries(new FormData(e.currentTarget));
              try {
                await post("/auth/setup", { ...data, role: "administrator" });
                onComplete();
              } catch (err) {
                setError(err instanceof Error ? err.message : String(err));
              } finally {
                setBusy(false);
              }
            }}
          >
            <label>
              Organisation
              <input name="organization" required maxLength={150} />
            </label>
            <label>
              Ton nom
              <input name="name" required maxLength={120} />
            </label>
            <label>
              Adresse e-mail
              <input
                name="email"
                type="email"
                autoComplete="username"
                required
              />
            </label>
            <label>
              Mot de passe personnel
              <input
                name="password"
                type="password"
                autoComplete="new-password"
                minLength={12}
                maxLength={200}
                required
              />
            </label>
            <label>
              Code d’installation
              <input name="setup_code" autoComplete="off" required />
            </label>
            <p className="muted">
              Le code est affiché par le lanceur et conservé dans
              data/local-setup-code.txt sur ce PC. Choisis un mot de passe
              unique d’au moins 12 caractères.
            </p>
            {error && (
              <div className="error" role="alert">
                {error}
              </div>
            )}
            <button className="btn primary full" disabled={busy}>
              Créer mon espace
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export function PasswordChange({
  onComplete,
  required = false,
}: {
  onComplete: () => void;
  required?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return (
    <section className="panel pad profile-panel">
      <h2>
        {required
          ? "Remplacer le mot de passe temporaire"
          : "Changer mon mot de passe"}
      </h2>
      <p>
        Après le changement, toutes tes sessions seront fermées. Connecte-toi
        avec le nouveau mot de passe.
      </p>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          const data = Object.fromEntries(new FormData(e.currentTarget));
          if (data.new_password !== data.confirm_password) {
            setError("Les deux nouveaux mots de passe doivent correspondre.");
            setBusy(false);
            return;
          }
          try {
            await post("/auth/password", {
              current_password: data.current_password,
              new_password: data.new_password,
            });
            onComplete();
          } catch (err) {
            setError(err instanceof Error ? err.message : String(err));
          } finally {
            setBusy(false);
          }
        }}
      >
        <label>
          Mot de passe actuel
          <input
            type="password"
            name="current_password"
            autoComplete="current-password"
            required
          />
        </label>
        <label>
          Nouveau mot de passe
          <input
            type="password"
            name="new_password"
            autoComplete="new-password"
            minLength={12}
            maxLength={200}
            required
          />
        </label>
        <label>
          Confirmer le nouveau mot de passe
          <input
            type="password"
            name="confirm_password"
            autoComplete="new-password"
            minLength={12}
            maxLength={200}
            required
          />
        </label>
        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}
        <button className="btn primary" disabled={busy}>
          Enregistrer le mot de passe
        </button>
      </form>
    </section>
  );
}
