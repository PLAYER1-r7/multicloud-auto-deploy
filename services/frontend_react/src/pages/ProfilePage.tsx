import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { profileApi } from "../api/profile";
import type { Profile } from "../types/message";
import { useAuth } from "../contexts/AuthContext";
import Alert from "../components/Alert";

export default function ProfilePage() {
  const { isLoggedIn } = useAuth();
  const navigate = useNavigate();

  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [nickname, setNickname] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!isLoggedIn) {
      setLoading(false);
      return;
    }
    profileApi
      .getProfile()
      .then((p) => {
        setProfile(p);
        setNickname(p.nickname ?? "");
      })
      .catch((e: unknown) =>
        setError((e as Error).message ?? "Failed to load profile"),
      )
      .finally(() => setLoading(false));
  }, [isLoggedIn]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nickname.trim()) {
      setError("ニックネームを入力してください");
      return;
    }
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const updated = await profileApi.updateProfile({
        nickname: nickname.trim(),
      });
      setProfile(updated);
      setSuccess("プロフィールを更新しました");
    } catch (e: unknown) {
      setError((e as Error).message ?? "Failed to update profile");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="panel">
      <h1>Profile</h1>
      <Alert type="success" message={success} />
      <Alert type="error" message={error} />

      {loading ? (
        <p className="muted">読み込み中...</p>
      ) : !isLoggedIn ? (
        <>
          <p>サインインするとプロフィールを確認・編集できます。</p>
          <div className="actions">
            <button
              className="button"
              type="button"
              onClick={() => navigate("/login")}
            >
              Sign in
            </button>
          </div>
        </>
      ) : profile ? (
        <>
          <div className="profile-grid">
            <div>
              <div className="label">User ID</div>
              <div className="value">{profile.userId}</div>
            </div>
            <div>
              <div className="label">Nickname</div>
              <div className="value">{profile.nickname ?? "-"}</div>
            </div>
          </div>

          <form className="form" onSubmit={handleSave}>
            <div className="field">
              <label className="label" htmlFor="nickname">
                Nickname
              </label>
              <input
                className="input"
                id="nickname"
                type="text"
                maxLength={40}
                required
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
              />
            </div>
            <div className="actions">
              <button className="button" type="submit" disabled={saving}>
                {saving ? "保存中..." : "Save"}
              </button>
            </div>
          </form>
        </>
      ) : (
        <p className="muted">プロフィールを読み込めませんでした。</p>
      )}
    </section>
  );
}
