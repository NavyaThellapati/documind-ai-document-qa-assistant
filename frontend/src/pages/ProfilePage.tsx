import { useAuth } from "../contexts/AuthContext";

export function ProfilePage() {
  const { user } = useAuth();
  return (
    <section className="page">
      <h1>Profile</h1>
      <div className="detail-grid">
        <div><span>Name</span><strong>{user?.full_name || "Not set"}</strong></div>
        <div><span>Email</span><strong>{user?.email}</strong></div>
        <div><span>User ID</span><strong>{user?.id}</strong></div>
        <div><span>Joined</span><strong>{user ? new Date(user.created_at).toLocaleDateString() : ""}</strong></div>
      </div>
    </section>
  );
}
