export type AccountKey = "boss" | "staff";

export interface Account {
  key: AccountKey;
  label: string;
  username: string;
  password: string;
  roles: string[];
}
