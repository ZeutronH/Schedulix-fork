import axios from "axios";

const baseURL = "/api";

const facultyApi = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
});

facultyApi.interceptors.request.use((config) => {
  const token = localStorage.getItem("schedulix_faculty_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

facultyApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("schedulix_faculty_token");
    }
    return Promise.reject(error);
  }
);

export default facultyApi;
