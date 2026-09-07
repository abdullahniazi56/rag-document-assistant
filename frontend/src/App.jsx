import { useState, useEffect } from "react"
import ReactMarkdown from "react-markdown"
import "./index.css"

const API_URL = "http://127.0.0.1:8000"

export default function App() {
  const [file, setFile] = useState(null)
  const [uploadStatus, setUploadStatus] = useState("")
  const [uploading, setUploading] = useState(false)
  const [question, setQuestion] = useState("")
  const [chat, setChat] = useState([])
  const [isAsking, setIsAsking] = useState(false)
  const [documents, setDocuments] = useState([])

  async function fetchDocuments() {
    try {
      const response = await fetch(`${API_URL}/documents`)
      const data = await response.json()
      setDocuments(data)
    } catch {
      setDocuments([])
    }
  }

  useEffect(() => {
    fetchDocuments()
  }, [])

  async function uploadDocument(event) {
    event.preventDefault()

    if (!file) {
      setUploadStatus("Choose a .txt file first.")
      return
    }

    const formData = new FormData()
    formData.append("file", file)

    setUploading(true)
    setUploadStatus("Uploading and indexing document...")

    try {
      const response = await fetch(`${API_URL}/documents`, {
        method: "POST",
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || "Upload failed.")
      }

      setUploadStatus(
        `${data.filename} indexed: ${data.stored_chunks} chunks stored.`
      )
      setFile(null)
      fetchDocuments()
    } catch (error) {
      setUploadStatus(`Error: ${error.message}`)
    } finally {
      setUploading(false)
    }
  }

  async function deleteDocument(filename) {
    try {
      await fetch(`${API_URL}/documents/${encodeURIComponent(filename)}`, {
        method: "DELETE",
      })
      fetchDocuments()
    } catch (error) {
      console.error("Delete failed:", error)
    }
  }

  async function askQuestion(event) {
    event.preventDefault()

    const trimmedQuestion = question.trim()

    if (!trimmedQuestion) return

    setIsAsking(true)

    try {
      const response = await fetch(`${API_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmedQuestion }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || "Question failed.")
      }

      setChat((prev) => [
        ...prev,
        {
          question: trimmedQuestion,
          answer: data.answer,
          sources: data.sources,
        },
      ])

      setQuestion("")
    } catch (error) {
      setChat((prev) => [
        ...prev,
        {
          question: trimmedQuestion,
          answer: `Error: ${error.message}`,
          sources: [],
        },
      ])
    } finally {
      setIsAsking(false)
    }
  }

  return (
    <main className="app">
      <header className="hero">
        <p className="eyebrow">RAG DOCUMENT ASSISTANT</p>
        <h1>Ask your documents.</h1>
        <p className="subtitle">
          Upload a text document, then get answers grounded in its content.
        </p>
      </header>

      <section className="upload-card">
        <div>
          <p className="section-label">01 / KNOWLEDGE BASE</p>
          <h2>Upload a document</h2>
          <p>Text files are chunked, embedded with Gemini, and stored in Qdrant.</p>
        </div>

        <form onSubmit={uploadDocument} className="upload-form">
          <input
            type="file"
            accept=".txt,text/plain"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
          <button type="submit" disabled={uploading}>
            {uploading ? "Indexing..." : "Index document"}
          </button>
        </form>

        {uploadStatus && <p className="status">{uploadStatus}</p>}

        {documents.length > 0 && (
          <div className="doc-list">
            <p className="section-label">UPLOADED DOCUMENTS</p>
            {documents.map((doc) => (
              <div className="doc-item" key={doc.filename}>
                <span>
                  {doc.filename} — {doc.chunk_count} chunks
                </span>
                <button
                  className="delete-btn"
                  onClick={() => deleteDocument(doc.filename)}
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="chat-section">
        <div className="chat-heading">
          <div>
            <p className="section-label">02 / RETRIEVAL CHAT</p>
            <h2>Ask a question</h2>
          </div>
          <span className="live-dot">Gemini + Qdrant</span>
        </div>

        <div className="messages">
          {chat.length === 0 && (
            <p className="empty-state">
              Upload a document, then ask a question about its contents.
            </p>
          )}

          {chat.map((message, index) => (
            <article className="message" key={`${index}`}>
              <p className="question">{message.question}</p>
              <div className="answer">
                <ReactMarkdown>{message.answer}</ReactMarkdown>
              </div>

              {message.sources.length > 0 && (
                <div className="sources">
                  <span>Sources</span>
                  {message.sources.map((source, sourceIndex) => (
                    <div
                      className="source"
                      key={`${source.filename}-${source.chunk_number}-${sourceIndex}`}
                    >
                      <strong>
                        {source.filename} / chunk {source.chunk_number}
                      </strong>
                      {source.snippet && (
                        <p className="snippet">{source.snippet}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </article>
          ))}
        </div>

        <form onSubmit={askQuestion} className="question-form">
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="What does the document say about RAG?"
          />
          <button type="submit" disabled={isAsking}>
            {isAsking ? "Searching..." : "Ask"}
          </button>
        </form>
      </section>
    </main>
  )
}