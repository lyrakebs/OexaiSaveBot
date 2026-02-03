import os
import requests

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def expand_url(url):
    """
    Расширяем редирект-ссылку.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.head(url, allow_redirects=True, headers=headers, timeout=10)
        return r.url
    except Exception:
        return url

def download_from_tikwm(url, return_data=False):
    """
    Скачиваем TikTok фото через TikWM API.
    Если return_data=True, возвращаем JSON без скачивания.
    """
    url = expand_url(url)
    api_url = "https://tikwm.com/api"
    params = {"url": url}
    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(api_url, params=params, headers=headers, timeout=15)
    data = r.json()

    if data.get("code") != 0:
        raise Exception(f"TikWM API вернул ошибку: {data.get('message')}")

    if return_data:
        return data["data"]

    files = []
    images = data["data"].get("images")
    if images:
        for i, img_url in enumerate(images):
            resp = requests.get(img_url, headers=headers, timeout=20)
            filename = f"{DOWNLOAD_DIR}/tikwm_photo_{i}.jpg"
            with open(filename, "wb") as f:
                f.write(resp.content)
            files.append(filename)

    return files
