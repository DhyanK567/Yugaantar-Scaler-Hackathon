import Sidebar from "./Sidebar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "#F2F2F2" }}>
      <Sidebar />
      <main style={{ flex: 1, minWidth: 0, overflowX: "hidden" }}>
        {children}
      </main>
    </div>
  );
}
