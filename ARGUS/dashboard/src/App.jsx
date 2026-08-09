import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthorityView } from "./pages/AuthorityView";
import { ResidentView } from "./pages/ResidentView";
import "./App.css";

// Reads VITE_BACKEND_URL at build time (set this in Vercel's project
// settings once the backend has a public URL). Falls back to localhost
// for local development, where nothing needs to be set.
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AuthorityView backendUrl={BACKEND_URL} />} />
        <Route path="/resident" element={<ResidentView backendUrl={BACKEND_URL} />} />
      </Routes>
    </BrowserRouter>
  );
}
