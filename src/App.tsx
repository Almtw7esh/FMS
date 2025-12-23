
import Login from "./pages/Login";
import FMSController from "./pages/FMSController";
import NotFound from "./pages/NotFound";

import FormPage from "./pages/FormPage";
import { BrowserRouter, Routes, Route } from "react-router-dom";

const App = () => (
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<Login />} />
      <Route path="/fms-controller" element={<FMSController />} />
      <Route path="/form/:taskId" element={<FormPage />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  </BrowserRouter>
);

export default App;
