import axios from 'axios'

function getCsrfToken(): string {
  const match = document.cookie.match(/csrftoken=([^;]+)/)
  return match ? match[1] : ''
}

const client = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

client.interceptors.request.use((config) => {
  const method = config.method?.toLowerCase() ?? ''
  if (['post', 'put', 'patch', 'delete'].includes(method)) {
    config.headers['X-CSRFToken'] = getCsrfToken()
  }
  return config
})

export default client
