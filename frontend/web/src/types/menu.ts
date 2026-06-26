export interface MenuTable extends BaseType {
  name?: string;
  type?: number;
  icon?: string;
  order?: number;
  permission?: string;
  route_name?: string;
  route_path?: string;
  component_path?: string;
  redirect?: string;
  parent_id?: number;
  parent_name?: string;
  keep_alive?: boolean;
  hidden?: boolean;
  always_show?: boolean;
  title?: string;
  params?: MenuKeyValue[];
  affix?: boolean;
  children?: MenuTable[];
  client?: "pc" | "app";
  link?: string;
  is_iframe?: boolean;
  is_hide_tab?: boolean;
  active_path?: string;
  show_badge?: boolean;
  show_text_badge?: string;
  scope?: "platform" | "tenant";
  status?: number;
  description?: string;
}

export interface MenuForm extends BaseFormType {
  name?: string;
  type?: number;
  icon?: string;
  order?: number;
  permission?: string;
  route_name?: string;
  route_path?: string;
  component_path?: string;
  redirect?: string;
  parent_id?: number;
  keep_alive?: boolean;
  hidden?: boolean;
  always_show?: boolean;
  title?: string;
  params?: MenuKeyValue[];
  affix?: boolean;
  client?: "pc" | "app";
  link?: string;
  is_iframe?: boolean;
  is_hide_tab?: boolean;
  active_path?: string;
  show_badge?: boolean;
  show_text_badge?: string;
  scope?: "platform" | "tenant";
  status?: number;
  description?: string;
}

export interface MenuKeyValue {
  key: string;
  value: string;
}
