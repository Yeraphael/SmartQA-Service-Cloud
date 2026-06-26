import { request } from "@utils";

const API_PATH = "/system/auth";

const AuthAPI = {
  login(body: LoginFormData) {
    return request<ApiResponse<LoginResult>>({
      url: `${API_PATH}/login`,
      method: "post",
      headers: {
        "Content-Type": "multipart/form-data",
      },
      data: body,
    });
  },

  refreshToken(body: RefreshToekenBody) {
    return request<ApiResponse<JWTOut>>({
      url: `${API_PATH}/token/refresh`,
      method: "post",
      data: body,
    });
  },

  getCaptcha() {
    return request<ApiResponse<CaptchaInfo>>({
      url: `${API_PATH}/captcha/get`,
      method: "get",
    });
  },

  logout(body: LogoutBody) {
    return request<ApiResponse>({
      url: `${API_PATH}/logout`,
      method: "post",
      data: body,
    });
  },
};

export default AuthAPI;

export interface LoginFormData {
  username: string;
  password: string;
  captcha?: string;
  captcha_key?: string;
  remember?: boolean;
  login_type?: string;
}

export interface JWTOut {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginResult extends JWTOut {
  user_info?: Record<string, unknown>;
}

export interface RefreshToekenBody {
  refresh_token: string;
}

export interface LogoutBody {
  token: string;
}

export interface CaptchaInfo {
  enable: boolean;
  key: string;
  img_base: string;
}
