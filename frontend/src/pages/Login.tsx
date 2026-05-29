import { useState, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { Label } from '@/components/ui/Label'
import { Icon } from '@/components/ui/Icon'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login({ username, password })
      navigate('/')
    } catch {
      setError('Invalid username or password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#091a0d] flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Brand */}
        <div className="flex flex-col items-center gap-3 mb-8">
          <div className="w-14 h-14 rounded-2xl bg-green-600 flex items-center justify-center shadow-lg shadow-green-900/40">
            <Icon name="bolt" size={28} className="text-white" />
          </div>
          <div className="text-center">
            <h1 className="text-2xl font-bold text-slate-100">Webhook Relay</h1>
            <p className="text-sm text-green-400/70 mt-0.5">Universal Event Gateway</p>
          </div>
        </div>

        <div className="rounded-xl bg-[#0f2314] border border-[#1e3d24] p-8">
          <h2 className="text-sm font-semibold text-slate-100 mb-6">Sign in to continue</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="username">Username</Label>
              <Input id="username" type="text" autoComplete="username"
                value={username} onChange={e => setUsername(e.target.value)} required />
            </div>
            <div>
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" autoComplete="current-password"
                value={password} onChange={e => setPassword(e.target.value)} required />
            </div>
            {error && (
              <div className="flex items-center gap-2 text-sm text-red-400 bg-red-900/20 border border-red-800 rounded-md px-3 py-2">
                <Icon name="error_outline" size={16} />
                {error}
              </div>
            )}
            <Button type="submit" className="w-full mt-2" disabled={loading}>
              {loading ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>
        </div>
        <p className="text-center text-xs text-slate-600 mt-4">Use your Django superuser credentials</p>
      </div>
    </div>
  )
}
