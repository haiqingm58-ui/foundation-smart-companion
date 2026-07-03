const appBase = (import.meta.env.BASE_URL || "/").replace(/\/$/, "");
const apiBase = import.meta.env.DEV ? "/api" : `${appBase}/api`;


export function apiUrl(path) {
  return `${apiBase}${path}`;
}


export class ApiError extends Error {
  constructor(message, { status, code, requestId } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}


export function readCookie(name) {
  const prefix = `${encodeURIComponent(name)}=`;
  return document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith(prefix))
    ?.slice(prefix.length) ?? "";
}


export async function request(path, { method = "GET", body, headers = {}, signal } = {}) {
  const requestHeaders = { ...headers };
  const options = { method, credentials: "include", headers: requestHeaders, signal };
  if (!["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase())) {
    const csrf = readCookie("foundation_csrf");
    if (csrf) requestHeaders["X-CSRF-Token"] = decodeURIComponent(csrf);
  }
  if (body instanceof FormData) {
    options.body = body;
  } else if (body !== undefined) {
    requestHeaders["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(`${apiBase}${path}`, options);
  } catch (error) {
    throw new ApiError("网络连接失败，请检查网络后重试", { code: "NETWORK_ERROR" });
  }
  const text = await response.text();
  const payload = text ? JSON.parse(text) : {};
  if (!response.ok || payload.success === false) {
    throw new ApiError(payload.message || `请求失败 (${response.status})`, {
      status: response.status,
      code: payload.code,
      requestId: payload.requestId,
    });
  }
  return payload.success === true ? payload.data : payload;
}
