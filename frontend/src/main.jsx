import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// --- PWA ACTIVATION ---
import { registerSW } from 'virtual:pwa-register'
registerSW({ immediate: true })
// ----------------------

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)