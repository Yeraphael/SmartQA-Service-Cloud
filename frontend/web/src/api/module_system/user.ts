import { request } from "@utils";
import type { MenuTable, MenuForm } from "@/types/menu";

const API_PATH = "/system/user";

export const UserAPI = {
  getCurrentUserInfo() {
    return request<ApiResponse<UserInfo>>({
      url: `${API_PATH}/current/info`,
      method: "get",
    });
  },

  uploadCurrentUserAvatar(body: any) {
    return request<ApiResponse<UploadFilePath>>({
      url: `/common/file/upload?upload_type=avatar`,
      method: "post",
      data: body,
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  updateCurrentUserInfo(body: InfoFormState) {
    return request<ApiResponse<UserInfo>>({
      url: `${API_PATH}/current/info/update`,
      method: "put",
      data: body,
    });
  },

  changeCurrentUserPassword(body: PasswordFormState) {
    return request<ApiResponse>({
      url: `${API_PATH}/password/change`,
      method: "put",
      data: body,
    });
  },

  forgetPassword(body: ForgetPasswordForm) {
    return request<ApiResponse>({
      url: `${API_PATH}/password/forget`,
      method: "post",
      data: body,
    });
  },
};

export default UserAPI;

export interface ForgetPasswordForm {
  username: string;
  new_password: string;
  mobile?: string;
  confirmPassword: string;
}

export interface UserInfo extends BaseType {
  username?: string;
  name?: string;
  avatar?: string;
  email?: string;
  mobile?: string;
  gender?: string;
  password?: string;
  menus?: MenuTable[];
  roles?: roleSelectorType[];
  role_names?: roleSelectorType["name"][];
  role_ids?: roleSelectorType["id"][];
  is_superuser?: boolean;
  last_login?: string;
  created_by?: CommonType;
  updated_by?: CommonType;
  deleted_by?: CommonType;
  status?: number;
  description?: string;
}

export interface roleSelectorType {
  id?: number;
  name?: string;
  code?: string;
  status?: number;
  description?: string;
  menus?: MenuForm[];
}

export interface InfoFormState {
  id?: number;
  name?: string;
  gender?: number;
  mobile?: string;
  email?: string;
  username?: string;
  roles?: roleSelectorType[];
  avatar?: string;
  created_time?: string;
  updated_time?: string;
  status?: number;
  description?: string;
}

export interface PasswordFormState {
  old_password: string;
  new_password: string;
  confirm_password: string;
}
