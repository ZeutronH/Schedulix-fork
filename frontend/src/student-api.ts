import axios from "axios";

const studentApi = axios.create({
  baseURL: "/api",
  timeout: 30000,
});

studentApi.interceptors.request.use((config) => {
  const token = localStorage.getItem("schedulix_student_token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

studentApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("schedulix_student_token");
    }
    return Promise.reject(error);
  }
);

export default studentApi;
