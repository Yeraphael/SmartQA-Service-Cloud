from app.config.path_conf import BANNER_FILE


def worship(env: str) -> str:
    """
    读取启动 Banner（优先 `banner.txt`，并附带当前环境名）。
    参数:
    - env (str): 当前运行环境标识。

    返回:
    - str: banner 文本。
    """
    if BANNER_FILE.exists():
        banner = BANNER_FILE.read_text(encoding="utf-8")
        return f"🚀 当前运行环境: {env}\n{banner}"
    return ""
