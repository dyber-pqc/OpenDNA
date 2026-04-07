import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import 'molstar/lib/mol-plugin-ui/skin/dark.scss'
import App from './App.tsx'
import ErrorBoundary from './components/ErrorBoundary/ErrorBoundary'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
