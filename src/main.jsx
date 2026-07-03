import React from "react";
import { createRoot } from "react-dom/client";
import { RouterApp } from "./router/index.jsx";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <RouterApp />
  </React.StrictMode>,
);
