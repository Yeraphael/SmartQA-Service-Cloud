import { request } from "@utils";

const API_PATH = "/system/dict";

const DictAPI = {
  getInitDict(dict_type: string) {
    return request<ApiResponse<DictDataTable[]>>({
      url: `${API_PATH}/data/info/${dict_type}`,
      method: "get",
    });
  },
};

export default DictAPI;

export interface DictDataTable extends BaseType {
  dict_sort?: number;
  dict_label?: string;
  dict_value?: string;
  dict_type_id?: number;
  dict_type?: string;
  css_class?: string;
  list_class?: string;
  is_default?: boolean;
  status?: number;
  description?: string;
}
