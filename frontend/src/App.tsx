import { BrowserRouter, Routes, Route, Navigate } from "react-router";
import AdminPage from "./pages/AdminPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/admin" replace />} />

        <Route path="/admin" element={<AdminPage />} />

        <Route path="*" element={<div>Страница не найдена</div>} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
