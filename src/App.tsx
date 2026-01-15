import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import axios from 'axios'
import './App.css'

function App() {
  const [file, setFile] = useState<File | null>(null)
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [resultUrl, setResultUrl] = useState<string | null>(null)
  const [isProcessing, setIsProcessing] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const acceptedFile = acceptedFiles[0]
    setFile(acceptedFile)
    setImageUrl(URL.createObjectURL(acceptedFile))
    setResultUrl(null)
    setError(null)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': []
    },
    maxFiles: 1
  })

  const handleRemoveWatermark = async () => {
    if (!file) return

    setIsProcessing(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('image', file)

      // 根据环境配置API地址
      const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
      const apiUrl = isLocal ? 'http://localhost:5000/api/remove-watermark' : '/api/remove-watermark'
      const response = await axios.post(apiUrl, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      if (response.data.result) {
        const resultImageUrl = `data:image/png;base64,${response.data.result}`
        setResultUrl(resultImageUrl)
      } else if (response.data.error) {
        setError(response.data.error)
      }
    } catch (err) {
      console.error('Error:', err)
      const errorMessage = err instanceof Error ? err.message : JSON.stringify(err)
      setError(`处理图像时出错: ${errorMessage}`)
    } finally {
      setIsProcessing(false)
    }
  }

  const handleDownload = () => {
    if (!resultUrl) return

    const link = document.createElement('a')
    link.href = resultUrl
    link.download = `processed_${file?.name || 'image'}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const handleReset = () => {
    setFile(null)
    setImageUrl(null)
    setResultUrl(null)
    setError(null)
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4" style={{ backgroundColor: '#e0f2fe', minHeight: '100vh' }}>
      <div className="w-full max-w-6xl bg-white dark:bg-gray-800 rounded-2xl p-6 md:p-8">
        {/* 顶部标题区域 */}
        <div className="text-center mb-8">
          <div className="inline-block mb-4">
            <div className="bg-gradient-to-r from-blue-500 to-indigo-600 rounded-full p-3">
              <svg className="h-8 w-8 text-white" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                <path
                  d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-cyan-800 dark:text-cyan-400 mb-1">
            水印移除工具
          </h1>
          <h2 className="text-4xl md:text-5xl font-bold text-cyan-800 dark:text-cyan-400 mb-4">
            Watermark Remover
          </h2>
          <p className="text-cyan-700 dark:text-cyan-500 max-w-2xl mx-auto">
            智能检测并移除图像中的水印 | Intelligently detect and remove watermarks from images
          </p>
        </div>

        <div className="mb-8">
          <div className="flex flex-row justify-between gap-6 w-full">
            {/* 左侧：输入图像 */}
            <div className="flex-1 min-w-[250px] flex flex-col">
              <h2 className="text-2xl font-semibold text-cyan-800 dark:text-cyan-400 mb-4 text-center">
                输入图像
                <span className="block text-lg text-cyan-700 dark:text-cyan-500">Input Image</span>
              </h2>
              <div
                {...getRootProps()}
                className={`
                  border-2 border-blue-200 dark:border-blue-700 rounded-lg p-4 flex items-center justify-center h-[350px]
                  ${isDragActive ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/20' : ''}
                  ${imageUrl ? 'border-green-400 bg-green-50 dark:bg-green-900/20' : ''}
                  transition-colors duration-200
                `}
              >
                <input {...getInputProps()} />
                {!imageUrl ? (
                  <div className="text-center p-4">
                    <svg
                      className="mx-auto h-10 w-10 text-cyan-500"
                      stroke="currentColor"
                      fill="none"
                      viewBox="0 0 48 48"
                    >
                      <path
                        d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                        strokeWidth={2}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                    <p className="mt-2 text-sm text-cyan-700 dark:text-cyan-500">
                      <span className="font-medium text-cyan-600 dark:text-cyan-400">
                        点击或拖拽图片到此处
                      </span>
                    </p>
                    <p className="text-xs text-cyan-600 dark:text-cyan-500 mt-1">
                      支持 JPG、PNG、WEBP 等格式
                    </p>
                  </div>
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <img
                      src={imageUrl}
                      alt="Uploaded"
                      className="max-h-full max-w-full object-contain rounded-lg"
                    />
                  </div>
                )}
              </div>
              {file && (
                <p className="mt-2 text-sm text-cyan-700 dark:text-cyan-500 text-center">
                  已上传: {file.name}
                </p>
              )}
            </div>

            {/* 右侧：处理结果 */}
            <div className="flex-1 min-w-[250px] flex flex-col">
              <h2 className="text-2xl font-semibold text-cyan-800 dark:text-cyan-400 mb-4 text-center">
                处理结果
                <span className="block text-lg text-cyan-700 dark:text-cyan-500">Result</span>
              </h2>
              <div className="border-2 border-blue-200 dark:border-blue-700 rounded-lg p-4 flex items-center justify-center h-[350px] bg-blue-50 dark:bg-blue-900/20">
                {resultUrl ? (
                  <div className="relative w-full h-full flex items-center justify-center">
                    <img
                      src={resultUrl}
                      alt="Processed"
                      className="max-h-full max-w-full object-contain rounded-lg"
                    />
                  </div>
                ) : (
                  <div className="text-center text-cyan-500 dark:text-cyan-400 p-4">
                    <svg
                      className="mx-auto h-10 w-10 mb-2"
                      stroke="currentColor"
                      fill="none"
                      viewBox="0 0 48 48"
                    >
                      <path
                        d="M12 6.253v13m0 0l-2.243 2.244m2.243-2.244l2.243 2.244M30 18.747v13m0 0l2.243-2.243m-2.243 2.243l-2.243-2.243M12 25.753V42m18-16.247v13m0 0l2.243-2.243m-2.243 2.243l-2.243-2.243M12 12.753V29m18-16.247v13m0 0l2.243-2.243m-2.243 2.243l-2.243-2.243"
                        strokeWidth={2}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                    <p>处理结果将显示在这里</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* 错误信息 */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-red-600 dark:text-red-400">{error}</p>
          </div>
        )}

        {/* 操作按钮 */}
        <div className="flex flex-wrap justify-center gap-4 mb-6">
          {imageUrl && (
            <button
              onClick={handleRemoveWatermark}
              disabled={isProcessing}
              style={{ height: '40px' }}
              className="
                px-8 bg-gradient-to-r from-cyan-400 to-teal-500 text-white rounded-full font-semibold
                hover:from-cyan-500 hover:to-teal-600 disabled:from-cyan-300 disabled:to-teal-400 disabled:cursor-not-allowed
                transition-colors duration-300
                flex items-center gap-2 min-w-[180px] justify-center text-base
              "
            >
              {isProcessing ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  处理中... | Processing...
                </>
              ) : (
                '移除水印 | Remove Watermark'
              )}
            </button>
          )}
          {resultUrl && (
            <button
              onClick={handleDownload}
              style={{ height: '40px' }}
              className="
                px-8 bg-gradient-to-r from-cyan-400 to-teal-500 text-white rounded-full font-semibold
                hover:from-cyan-500 hover:to-teal-600 transition-colors duration-300
                flex items-center gap-2 min-w-[180px] justify-center text-base
              "
            >
                下载结果 | Download
              </button>
          )}
          {(imageUrl || resultUrl) && (
            <button
              onClick={handleReset}
              style={{ height: '40px' }}
              className="
                px-8 bg-gradient-to-r from-cyan-400 to-teal-500 text-white rounded-full font-semibold
                hover:from-cyan-500 hover:to-teal-600 transition-colors duration-300
                flex items-center gap-2 min-w-[180px] justify-center text-base
              "
            >
                上传新图片 | Upload New
              </button>
          )}
        </div>

        <div className="mt-8 pt-6 border-t border-blue-200 dark:border-blue-700">
          <div className="text-center text-sm text-blue-600 dark:text-blue-400">
            <p>© 2026 水印移除工具 | Watermark Remover</p>
            <p className="mt-1">基于 EasyOCR 和 Inpaint 模型 | Powered by EasyOCR and Inpaint Model</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App