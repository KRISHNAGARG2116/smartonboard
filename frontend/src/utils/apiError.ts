import axios from 'axios'

export interface HealthStatus {
  status: string
  service: string
  version: string
  database_connected?: boolean
  groq_api_key_configured: boolean
}

export function formatApiError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    if (err.code === 'ERR_NETWORK' || err.message.includes('Network Error')) {
      return 'Cannot reach the backend. Start the API server: python -m uvicorn backend.server:app --reload --port 8000'
    }
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') {
      if (/api.?key|authentication|unauthorized|401|403/i.test(detail)) {
        return `Groq API key issue: ${detail}. Add GROQ_API_KEY to a .env file in the project root.`
      }
      return detail
    }
    if (err.response?.status === 502 || err.response?.status === 503) {
      return 'Backend unavailable. Make sure the API server is running on port 8000.'
    }
  }
  return 'Request failed. Check that the backend is running and GROQ_API_KEY is set.'
}

export async function checkHealth(): Promise<HealthStatus | null> {
  try {
    const { data } = await axios.get<HealthStatus>('/api/health')
    return data
  } catch {
    return null
  }
}
