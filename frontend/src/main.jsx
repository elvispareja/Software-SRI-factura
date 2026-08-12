import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { TemaProvider } from './tema/TemaProvider.jsx'
import { SesionProvider } from './auth/SesionProvider.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <TemaProvider>
      <SesionProvider>
        <App />
      </SesionProvider>
    </TemaProvider>
  </StrictMode>,
)
