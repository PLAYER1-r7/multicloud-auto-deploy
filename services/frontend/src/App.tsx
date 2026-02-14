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
  const [selectedImage, setSelectedImage] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')
  const [editAuthor, setEditAuthor] = useState('')

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

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      // ファイルサイズチェック (10MB)
      if (file.size > 10 * 1024 * 1024) {
        alert('ファイルサイズが大きすぎます（最大10MB）')
        return
      }

      // 画像タイプチェック
      if (!file.type.startsWith('image/')) {
        alert('画像ファイルを選択してください')
        return
      }

      setSelectedImage(file)
      
      // プレビュー用のURLを生成
      const reader = new FileReader()
      reader.onloadend = () => {
        setImagePreview(reader.result as string)
      }
      reader.readAsDataURL(file)
    }
  }

  const handleRemoveImage = () => {
    setSelectedImage(null)
    setImagePreview(null)
  }

  const uploadImage = async (file: File): Promise<string | null> => {
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await axios.post(`${API_URL}/api/uploads/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      return response.data.url
    } catch (error) {
      console.error('Failed to upload image:', error)
      alert('画像のアップロードに失敗しました')
      return null
    } finally {
      setUploading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newMessage.trim() || !author.trim()) return

    setLoading(true)
    try {
      let imageUrl: string | null = null

      // 画像がある場合はアップロード
      if (selectedImage) {
        imageUrl = await uploadImage(selectedImage)
        if (!imageUrl) {
          setLoading(false)
          return
        }
      }

      await axios.post(`${API_URL}/api/messages/`, {
        content: newMessage,
        author: author,
        image_url: imageUrl,
      })
      
      setNewMessage('')
      setSelectedImage(null)
      setImagePreview(null)
      fetchMessages()
    } catch (error) {
      console.error('Failed to send message:', error)
      alert('メッセージの送信に失敗しました')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteMessage = async (messageId: string, messageContent: string) => {
    // 確認ダイアログを表示
    const confirmDelete = window.confirm(
      `このメッセージを削除しますか？\n\n「${messageContent.substring(0, 50)}${messageContent.length > 50 ? '...' : ''}」`
    )

    if (!confirmDelete) return

    try {
      await axios.delete(`${API_URL}/api/messages/${messageId}`)
      // 削除成功後、メッセージリストを更新
      fetchMessages()
    } catch (error) {
      console.error('Failed to delete message:', error)
      alert('メッセージの削除に失敗しました')
    }
  }

  const startEdit = (message: Message) => {
    setEditingId(message.id)
    setEditContent(message.content)
    setEditAuthor(message.author)
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditContent('')
    setEditAuthor('')
  }

  const saveEdit = async (messageId: string) => {
    if (!editContent.trim() || !editAuthor.trim()) {
      alert('内容と名前を入力してください')
      return
    }

    try {
      await axios.put(`${API_URL}/api/messages/${messageId}`, {
        content: editContent,
        author: editAuthor,
      })
      setEditingId(null)
      setEditContent('')
      setEditAuthor('')
      fetchMessages()
    } catch (error) {
      console.error('Failed to update message:', error)
      alert('メッセージの更新に失敗しました')
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
                  disabled={loading || uploading}
                  className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-400 transition-colors"
                >
                  {uploading ? 'アップロード中...' : loading ? '送信中...' : '送信'}
                </button>
              </div>

              {/* 画像アップロードセクション */}
              <div className="border-t pt-3">
                <label className="flex items-center gap-2 cursor-pointer text-gray-600 hover:text-blue-500">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 0 0 1.5-1.5V6a1.5 1.5 0 0 0-1.5-1.5H3.75A1.5 1.5 0 0 0 2.25 6v12a1.5 1.5 0 0 0 1.5 1.5Zm10.5-11.25h.008v.008h-.008V8.25Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z" />
                  </svg>
                  <span className="text-sm">画像を選択</span>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImageSelect}
                    className="hidden"
                    disabled={loading}
                  />
                </label>

                {imagePreview && (
                  <div className="mt-3 relative inline-block">
                    <img
                      src={imagePreview}
                      alt="Preview"
                      className="max-w-xs max-h-48 rounded-lg border border-gray-300"
                    />
                    <button
                      type="button"
                      onClick={handleRemoveImage}
                      className="absolute top-1 right-1 bg-red-500 text-white rounded-full p-1 hover:bg-red-600"
                      disabled={loading}
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                )}
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
                    {editingId === message.id ? (
                      // 編集モード
                      <div>
                        <div className="flex justify-between items-start mb-3">
                          <div className="flex-1">
                            <input
                              type="text"
                              value={editAuthor}
                              onChange={(e) => setEditAuthor(e.target.value)}
                              className="font-semibold text-gray-700 border border-gray-300 rounded px-2 py-1 w-48"
                              placeholder="名前"
                            />
                            <span className="text-gray-400 text-sm ml-2">
                              {new Date(message.created_at).toLocaleString('ja-JP')}
                            </span>
                          </div>
                          <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                            {getCloudIcon(cloudProvider)} {cloudProvider}
                          </span>
                        </div>
                        <textarea
                          value={editContent}
                          onChange={(e) => setEditContent(e.target.value)}
                          className="w-full border border-gray-300 rounded-lg p-3 mb-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          rows={4}
                          placeholder="メッセージ内容"
                        />
                        <div className="flex gap-2">
                          <button
                            onClick={() => saveEdit(message.id)}
                            className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg transition-colors"
                          >
                            保存
                          </button>
                          <button
                            onClick={cancelEdit}
                            className="bg-gray-300 hover:bg-gray-400 text-gray-700 px-4 py-2 rounded-lg transition-colors"
                          >
                            キャンセル
                          </button>
                        </div>
                      </div>
                    ) : (
                      // 表示モード
                      <>
                        <div className="flex justify-between items-start mb-2">
                          <div className="flex-1">
                            <span className="font-semibold text-gray-700">{message.author}</span>
                            <span className="text-gray-400 text-sm ml-2">
                              {new Date(message.created_at).toLocaleString('ja-JP')}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                              {getCloudIcon(cloudProvider)} {cloudProvider}
                            </span>
                            <button
                              onClick={() => startEdit(message)}
                              className="text-blue-500 hover:text-blue-700 hover:bg-blue-50 rounded p-1 transition-colors"
                              title="編集"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                                <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
                              </svg>
                            </button>
                            <button
                              onClick={() => handleDeleteMessage(message.id, message.content)}
                              className="text-red-500 hover:text-red-700 hover:bg-red-50 rounded p-1 transition-colors"
                              title="削除"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                                <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                              </svg>
                            </button>
                          </div>
                        </div>
                        <p className="text-gray-800 mb-2">{message.content}</p>
                        {message.image_url && (
                          <div className="mt-3">
                            <img
                              src={message.image_url}
                              alt="Attached image"
                              className="max-w-md max-h-96 rounded-lg border border-gray-200 cursor-pointer hover:opacity-90 transition-opacity"
                              onClick={() => window.open(message.image_url!, '_blank')}
                            />
                          </div>
                        )}
                      </>
                    )}
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
