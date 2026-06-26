declare global {
  /**
   * 绯荤粺璁剧疆
   */
  interface AppSettings {
    /** 绯荤粺鍚嶇О */
    name: string;
    /** 绯荤粺鏍囬 */
    title: string;
    /** 绯荤粺鐗堟湰 */
    version: string;
    /** 鏄惁鏄剧ず璁剧疆鎸夐挳 */
    showSettings: boolean;
    /** 鏄惁鏄剧ず鑿滃崟鎼滅储 */
    showMenuSearch: boolean;
    /** 鏄惁鏄剧ず鍏ㄥ睆鍒囨崲 */
    showFullscreen: boolean;
    /** 鏄惁鏄剧ず甯冨眬澶у皬 */
    showSizeSelect: boolean;
    /** 鏄惁鏄剧ず璇█閫夋嫨 */
    showLangSelect: boolean;
    /** 鏄惁鏄剧ず閫氱煡 */
    /** 鏄惁鏄剧ず澶氭爣绛惧鑸?*/
    showTagsView: boolean;
    /** 鏄惁鏄剧ず搴旂敤Logo */
    showAppLogo: boolean;
    /** 瀵艰埅鏍忓竷灞€(left|top|mix) */
    layout: "left" | "top" | "mix";
    /** 涓婚棰滆壊 */
    themeColor: string;
    /** 涓婚妯″紡(dark|light) */
    theme: import("@/enums/settings/theme.enum").ThemeMode;
    /** 甯冨眬澶у皬(default |large |small) */
    size: string;
    /** 璇█( zh-cn| en) */
    language: string;
    /** 鏄惁鏄剧ず姘村嵃 */
    /** 姘村嵃鍐呭 */
    /** 渚ц竟鏍忛厤鑹叉柟妗?*/
    sidebarColorScheme: "classic-blue" | "minimal-white";
    /** 椤圭洰寮曞 */
    guideVisible: boolean;
    /** 鏄惁鍚姩寮曞 */
    showGuide: boolean;
    /** 鏄惁寮€鍚疉I鍔╂墜 */
    /** 鏄惁寮€鍚伆鑹叉ā寮?*/
    grayMode: boolean;
    /** 椤甸潰鍒囨崲鍔ㄧ敾 */
    pageSwitchingAnimation: string;
  }

  /**
   * 涓嬫媺閫夐」鏁版嵁绫诲瀷
   */
  interface OptionType {
    /** 鍊?*/
    value: string | number;
    /** 鏂囨湰 */
    label: string;
    /** 瀛愬垪琛? */
    children?: OptionType[];
  }

  /**
   * 瀵煎叆缁撴灉
   */
  interface ExcelResult {
    /** 鐘舵€佺爜 */
    code: string;
    /** 鏃犳晥鏁版嵁鏉℃暟 */
    invalidCount: number;
    /** 鏈夋晥鏁版嵁鏉℃暟 */
    validCount: number;
    /** 閿欒淇℃伅 */
    messageList: Array<string>;
  }

  /**
   * 鍩虹鍝嶅簲缁撴瀯
   */
  interface ApiResponse<T = any> {
    code: number;
    data: T;
    msg: string;
    status_code: number;
    success: boolean;
  }

  /**
   * 鍏煎 web 宸ョ▼閬楃暀鐨?`Api.*` 鍛藉悕绌洪棿绫诲瀷寮曠敤
   * web 鐩墠浠ョ湡瀹炴帴鍙ｆā鍧楀鍑虹殑绫诲瀷涓哄噯锛岃繖閲屽厛鎻愪緵鏈€灏忓０鏄庨伩鍏?vue-tsc 闃绘柇銆?   */
  namespace Api {
    namespace Auth {
      interface UserInfo {
        [key: string]: unknown;
      }
    }
  }

  /**
   * 鍩虹鏌ヨ鍙傛暟锛堝熀纭€灞傦細鐘舵€?+ 鏃堕棿鑼冨洿锛?   */
  interface BaseQueryParams {
    created_time?: string[];
    updated_time?: string[];
  }

  /**
   * 瀹¤浜烘煡璇㈠弬鏁帮紙缁ф壙鍩虹鏌ヨ + 鍒涘缓浜?鏇存柊浜猴級
   */
  interface UserByQueryParams extends BaseQueryParams {
    created_id?: number;
    updated_id?: number;
  }

  /**
   * 鍒嗛〉鏌ヨ鍙傛暟锛堢户鎵垮熀纭€鏌ヨ + 鍒嗛〉瀛楁锛?   */
  interface PageQuery extends BaseQueryParams {
    page_no: number;
    page_size: number;
  }

  /**
   * 鍒嗛〉鍝嶅簲瀵硅薄锛堝垪琛ㄦ帴鍙?`data` 缁熶竴涓鸿缁撴瀯锛?   * 鍓嶇 `useTable` 浠呴€氳繃 `@utils/table` 鐨?`defaultResponseAdapter` 瑙ｆ瀽璇ュ舰鐘讹紙鍙?ApiResponse 鍖呰锛?   */
  interface PageResult<T = any> {
    items: T[];
    total: number;
    page_no: number;
    page_size: number;
    has_next: boolean;
  }

  /**
   * 鍒涘缓浜?   */
  interface CommonType {
    id?: number;
    name?: string;
  }

  /**
   * 鍩虹琛ㄥ崟绫诲瀷锛堝熀纭€灞傦細浠呭寘鍚?id锛?   */
  interface BaseFormType {
    id?: number;
  }

  /**
   * 鍩虹绫诲瀷锛堝熀纭€灞傦細鍖呭惈閫氱敤瀛楁锛?   */
  interface BaseType extends BaseFormType {
    index?: number;
    uuid?: string;
    is_deleted?: boolean;
    created_time?: string;
    updated_time?: string;
    deleted_time?: string;
    created_by?: CommonType;
    updated_by?: CommonType;
    deleted_by?: CommonType;
  }

  /**
   * 鎵归噺鎿嶄綔绫诲瀷
   */
  interface BatchType {
    ids: number[];
    status: number;
  }

  /**
   * 涓婁紶鏂囦欢璺緞
   */
  interface UploadFilePath {
    file_path: string;
    file_name: string;
    origin_name: string;
    file_url: string;
  }

  /**
   * 閫氱敤鎼滅储鍙傛暟
   */
  type CommonSearchParams = Pick<PageQuery, "page_no" | "page_size">;

  /**
   * 鍚敤鐘舵€?   */
  type EnableStatus = "0" | "1";

  /**
   * 鐧诲綍鍙傛暟
   */
  interface LoginParams {
    username: string;
    password: string;
    captcha_key?: string;
    captcha?: string;
    remember?: boolean;
    login_type?: string;
  }

  /**
   * 鐧诲綍鍝嶅簲
   */
  interface LoginResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
    expires_in: number;
  }

  /**
   * 鐢ㄦ埛淇℃伅
   */
  interface UserInfo {
    user_id: number;
    username: string;
    nickname?: string;
    email?: string;
    avatar?: string;
    phone?: string;
    roles?: RoleInfo[];
    permissions?: string[];
    menus?: MenuTable[];
    created_at?: string;
    updated_at?: string;
  }

  /**
   * 瑙掕壊淇℃伅
   */
  interface RoleInfo {
    id?: number;
    name?: string;
    code?: string;
    menus?: any[];
  }

  /**
   * 鐢ㄦ埛鍒楄〃
   */
  type UserList = PageResult<UserListItem>;

  /**
   * 鐢ㄦ埛鍒楄〃椤?   */
  interface UserListItem {
    id: number;
    avatar: string;
    status: number;
    userName: string;
    userGender: string;
    nickName: string;
    userPhone: string;
    userEmail: string;
    userRoles: string[];
    createBy: string;
    createTime: string;
    updateBy: string;
    updateTime: string;
  }

  /**
   * 鐢ㄦ埛鎼滅储鍙傛暟
   */
  type UserSearchParams = Partial<
    Pick<UserListItem, "id" | "userName" | "userGender" | "userPhone" | "userEmail" | "status"> &
      CommonSearchParams
  >;

  /**
   * 瑙掕壊鍒楄〃
   */
  type RoleList = PaginatedResponse<RoleListItem>;

  /**
   * 瑙掕壊鍒楄〃椤?   */
  interface RoleListItem {
    roleId: number;
    roleName: string;
    roleCode: string;
    description: string;
    enabled: boolean;
    createTime: string;
  }

  /**
   * 瑙掕壊鎼滅储鍙傛暟
   */
  type RoleSearchParams = Partial<
    Pick<RoleListItem, "roleId" | "roleName" | "roleCode" | "description" | "enabled"> &
      CommonSearchParams & {
        startTime: string | null;
        endTime: string | null;
      }
  >;
}

export {};
