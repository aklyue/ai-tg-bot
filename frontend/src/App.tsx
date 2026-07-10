import { BrowserRouter, Routes, Route, Navigate } from "react-router";
import AdminPage from "./pages/AdminPage";
import BestsellerAI from "./pages/BestsellerAI";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/admin" replace />} />

        <Route path="/admin" element={<AdminPage />} />
        <Route path="/bestseller" element={<BestsellerAI />} />

        <Route path="*" element={<div>Страница не найдена</div>} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
