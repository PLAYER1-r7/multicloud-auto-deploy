import { useState, useEffect } from 'react'
import axios from 'axios'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface Message {
  id: string
  content: string
  author: string
  image_url: string | null
  created_at: string
  updated_at: string | null
}

interface MessageListResponse {
  messages: Message[]
  total: number
  page: number
  page_size: number
}

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [newMessage, setNewMessage] = useState('')
  const [author, setAuthor] = useState('名無しさん')
  const [loading, setLoading] = useState(false)
  const [cloudProvider, setCloudProvider] = useState<string>('unknown')

  useEffect(() => {
    fetchMessages()
    detectCloudProvider()
  }, [])

  const fetchMessages = async () => {
    try {
      const response = await axios.get<MessageListResponse>(`${API_URL}/api/messages/`)
      setMessages(response.data.messages)
    } catch (error) {
      console.error('Failed to fetch messages:', error)
    }
  }

  const detectCloudProvider = async () => {
    try {
      const response = await axios.get(`${API_URL}/health`)
      setCloudProvider(response.data.cloud_provider || 'unknown')
    } catch (error) {
      console.error('Failed to detect cloud provider:', error)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newMessage.trim() || !author.trim()) return

    setLoading(true)
    try {
      await axios.post(`${API_URL}/api/messages/`, {
        content: newMessage,
        author: author
      })
      setNewMessage('')
      fetchMessages()
    } catch (error) {
      console.error('Failed to send message:', error)
      alert('メッセージの送信に失敗しました')
    } finally {
      setLoading(false)
    }
  }

  const getCloudIcon = (cloud: string) => {
    switch (cloud.toLowerCase()) {
      case 'aws':
        return '☁️'
      case 'azure':
        return '☁️'
      case 'gcp':
        return '☁️'
      default:
        return '🌐'
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            Multi-Cloud Auto Deploy Platform
          </h1>
          <p className="text-gray-600 flex items-center justify-center gap-2">
            {getCloudIcon(cloudProvider)}
            Deployed on: <span className="font-semibold">{cloudProvider.toUpperCase()}</span>
          </p>
        </header>

        <div className="max-w-3xl mx-auto">
          <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
            <h2 className="text-2xl font-semibold mb-4">メッセージを送信</h2>
            <form onSubmit={handleSubmit} className="space-y-3">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={author}
                  onChange={(e) => setAuthor(e.target.value)}
                  placeholder="名前..."
                  className="w-32 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={loading}
                />
                <input
                  type="text"
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  placeholder="メッセージを入力..."
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={loading}
                />
                <button
                  type="submit"
                  disabled={loading}
                  className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-400 transition-colors"
                >
                  {loading ? '送信中...' : '送信'}
                </button>
              </div>
            </form>
          </div>

          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-semibold mb-4">メッセージ一覧</h2>
            {messages.length === 0 ? (
              <p className="text-gray-500 text-center py-8">
                まだメッセージがありません
              </p>
            ) : (
              <div className="space-y-4">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <span className="font-semibold text-gray-700">{message.author}</span>
                        <span className="text-gray-400 text-sm ml-2">
                          {new Date(message.created_at).toLocaleString('ja-JP')}
                        </span>
                      </div>
                      <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                        {getCloudIcon(cloudProvider)} {cloudProvider}
                      </span>
                    </div>
                    <p className="text-gray-800">{message.content}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
