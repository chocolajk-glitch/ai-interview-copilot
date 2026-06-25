import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'

declare module 'axios' {
  export interface AxiosRequestConfig {
    /** 设为 true 时不弹错误 toast（用于静默探测） */
    silent?: boolean
  }
}

const baseURL = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export const http: AxiosInstance = axios.create({
  baseURL,
  timeout: 60_000,
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.response.use(
  (resp) => resp,
  (err) => {
    // 静默标记：health 检查不弹 toast
    const silent = err?.config?.silent
    if (silent) return Promise.reject(err)

    const status = err?.response?.status
    const detail =
      err?.response?.data?.detail || err?.message || '请求失败'
    if (status && status >= 400) {
      ElMessage.error(typeof detail === 'string' ? detail : JSON.stringify(detail))
    } else if (err?.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请检查后端服务是否启动')
    } else if (!status) {
      ElMessage.error(`网络异常: ${detail}`)
    }
    return Promise.reject(err)
  },
)

export async function get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const r = await http.get<T>(url, config)
  return r.data
}

export async function post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  const r = await http.post<T>(url, data, config)
  return r.data
}

export async function del<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const r = await http.delete<T>(url, config)
  return r.data
}
