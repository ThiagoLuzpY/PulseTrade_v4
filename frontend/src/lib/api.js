import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const http = axios.create({ baseURL: API, timeout: 60000 });

export const api = {
  movers: (exchange = "binance", market_type = "futures", top = 12) =>
    http.get("/movers", { params: { exchange, market_type, top } }).then((r) => r.data),
  klines: (params) => http.get("/klines", { params }).then((r) => r.data),
  scan: (payload) => http.post("/scan", payload).then((r) => r.data),
  enrich: (candidate) => http.post("/enrich", { candidate }).then((r) => r.data),
  signals: (limit = 50) => http.get("/signals", { params: { limit } }).then((r) => r.data),
  deleteSignal: (id) => http.delete(`/signals/${id}`).then((r) => r.data),
};

export default api;
