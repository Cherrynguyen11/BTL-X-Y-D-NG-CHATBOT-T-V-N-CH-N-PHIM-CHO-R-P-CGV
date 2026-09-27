import os
import sys
import json
import re
import subprocess
import urllib.parse
from datetime import datetime
import random

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SOLVER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "f5_solver.js")
COOKIES_FILE = os.path.join(DATA_DIR, "cgv_session_cookies.txt")
SYNC_STATUS_FILE = os.path.join(DATA_DIR, "sync_status.json")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

def normalize_title(title: str) -> str:
    """Loại bỏ ký tự đặc biệt để so sánh tên phim"""
    if not title:
        return ""
    t = title.lower().strip()
    t = re.sub(r'[\(\[\{].*?[\)\]\}]', '', t)
    t = re.sub(r'[^\w\s]', '', t)
    return " ".join(t.split())

def fetch_cgv_page(url: str, cookies_path: str = COOKIES_FILE) -> str:
    """Tải nội dung trang CGV và tự động giải bài toán thử thách F5 BIG-IP"""
    cmd1 = [
        "curl.exe", "-k", "-s",
        "-c", cookies_path,
        "-b", cookies_path,
        "-A", USER_AGENT,
        "-m", "20",
        url
    ]
    res1 = subprocess.run(cmd1, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    html = res1.stdout

    # Nếu gặp thử thách JavaScript của F5 ASM
    if "function challenge()" in html:
        # Chạy Node.js solver
        solve_proc = subprocess.run(
            ["node", SOLVER_SCRIPT],
            input=html,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        try:
            solution = json.loads(solve_proc.stdout.strip())
        except Exception:
            solution = None

        if solution and solution.get("success"):
            action_path = urllib.parse.unquote(solution["action"])
            action_url = f"https://www.cgv.vn{action_path}"

            post_args = [
                "curl.exe", "-k", "-s",
                "-b", cookies_path,
                "-c", cookies_path,
                "-A", USER_AGENT,
                "-e", url,
                "-m", "20",
                "-X", "POST",
                action_url
            ]
            for elem in solution.get("elements", []):
                k = urllib.parse.quote(str(elem.get("name", "")))
                v = urllib.parse.quote(str(elem.get("value", "")))
                post_args.extend(["-d", f"{k}={v}"])

            post_res = subprocess.run(post_args, capture_output=True, text=True, encoding="utf-8", errors="ignore")
            # Kết quả POST chính là HTML của trang đích
            html = post_res.stdout
        else:
            return ""

    return html

def parse_movie_detail(detail_url: str, cookies_path: str = COOKIES_FILE) -> dict:
    """Trích xuất thông tin chi tiết một bộ phim từ trang detail"""
    detail = {
        "director": "",
        "cast": [],
        "synopsis": "",
        "trailer_id": "",
        "age_rating": "P",
        "age_desc": "Phim được phép phổ biến đến người xem ở mọi độ tuổi"
    }
    
    try:
        html = fetch_cgv_page(detail_url, cookies_path)
        if not html:
            return detail

        # 1. Đạo diễn
        dir_m = re.search(r'Đạo diễn:.*?<div class="std">([^<]+)</div>', html, re.S)
        if dir_m:
            detail["director"] = dir_m.group(1).replace("&nbsp", "").strip()

        # 2. Diễn viên
        cast_m = re.search(r'Diễn viên:.*?<div class="std">([^<]+)</div>', html, re.S)
        if cast_m:
            raw_cast = cast_m.group(1).replace("&nbsp", "").strip()
            detail["cast"] = [c.strip() for c in raw_cast.split(",") if c.strip()]

        # 3. Giới hạn độ tuổi & Rated
        rated_m = re.search(r'Rated:.*?<div class="std">([^<]+)</div>', html, re.S)
        if rated_m:
            raw_rated = rated_m.group(1).replace("&nbsp", "").strip()
            detail["age_desc"] = raw_rated
            if "T18" in raw_rated or "18+" in raw_rated:
                detail["age_rating"] = "T18"
            elif "T16" in raw_rated or "16+" in raw_rated:
                detail["age_rating"] = "T16"
            elif "T13" in raw_rated or "13+" in raw_rated:
                detail["age_rating"] = "T13"
            elif "K" in raw_rated:
                detail["age_rating"] = "K"
            else:
                detail["age_rating"] = "P"

        # 4. Trailer Youtube
        trailer_m = re.search(r'youtube\.com/embed/([a-zA-Z0-9_-]+)', html)
        if trailer_m:
            detail["trailer_id"] = trailer_m.group(1)

        # 5. Tóm tắt nội dung
        synopsis_m = re.search(r'<h2>Chi tiết</h2>\s*<div class="std">\s*(.*?)\s*</div>', html, re.S)
        if synopsis_m:
            clean_syn = re.sub(r'<[^>]+>', ' ', synopsis_m.group(1))
            detail["synopsis"] = " ".join(clean_syn.split()).strip()

    except Exception as e:
        print(f"Lỗi phân tích trang chi tiết {detail_url}: {e}")

    return detail

def crawl_cgv_movies(limit_details: int = 15) -> list:
    """Cào toàn diện danh sách phim Đang Chiếu và Sắp Chiếu trên website CGV Việt Nam"""
    sources = [
        {"url": "https://www.cgv.vn/default/movies/now-showing.html", "status": "now_showing", "name": "Đang Chiếu"},
        {"url": "https://www.cgv.vn/default/movies/coming-soon-1.html", "status": "coming_soon", "name": "Sắp Chiếu"}
    ]

    all_movies = []
    seen_titles = set()
    details_fetched = 0

    for src in sources:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Đang kết nối tới CGV ({src['name']}): {src['url']}...")
        html = fetch_cgv_page(src["url"])

        if not html or "product-name" not in html:
            print(f"Không thể tải danh sách {src['name']} từ CGV.")
            continue

        # Trích xuất các thẻ phim
        cards = re.findall(r'<div class="product-images">.*?<div class="product-info">.*?</div>\s*</div>', html, re.S)
        if not cards:
            cards = re.findall(r'<li class="item[^"]*">.*?</li>', html, re.S)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Tìm thấy {len(cards)} phim {src['name']} trên CGV.")

        for card in cards:
            try:
                # Tên phim & link
                title_m = re.search(r'<h2 class="product-name">\s*<a href="([^"]+)"[^>]*title="([^"]+)"', card)
                if not title_m:
                    title_m = re.search(r'title="([^"]+)"', card)
                    link_m = re.search(r'href="([^"]+)"', card)
                    if not title_m or not link_m:
                        continue
                    title = title_m.group(1).strip()
                    detail_link = link_m.group(1).strip()
                else:
                    detail_link = title_m.group(1).strip()
                    title = title_m.group(2).strip()

                norm_key = normalize_title(title)
                if norm_key in seen_titles:
                    continue
                seen_titles.add(norm_key)

                # Poster (Giữ nguyên URL ảnh thumbnail 190x260 chuẩn của CGV CDN)
                poster_m = re.search(r'<img[^>]+src="([^"]+)"', card)
                poster_url = poster_m.group(1) if poster_m else ""

                # Thể loại
                genre_m = re.findall(r'Thể loại:.*?<span class="cgv-info-normal">(.*?)</span>', card, re.S)
                genre_str = genre_m[0].strip() if genre_m else "Điện ảnh"
                genres = [g.strip() for g in genre_str.split(",") if g.strip()]

                # Thời lượng
                dur_m = re.findall(r'Thời lượng:.*?<span class="cgv-info-normal">(.*?)</span>', card, re.S)
                dur_text = dur_m[0].strip() if dur_m else ""
                dur_num = 110
                dur_digits = re.findall(r'\d+', dur_text)
                if dur_digits:
                    dur_num = int(dur_digits[0])

                # Khởi chiếu
                rel_m = re.findall(r'Khởi chiếu:.*?<span class="cgv-info-normal">(.*?)</span>', card, re.S)
                rel_text = rel_m[0].strip() if rel_m else datetime.now().strftime("%Y-%m-%d")
                clean_date = rel_text
                try:
                    if "-" in rel_text:
                        parts = rel_text.split("-")
                        if len(parts) == 3 and len(parts[0]) == 2:
                            clean_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
                    elif "/" in rel_text:
                        parts = rel_text.split("/")
                        if len(parts) == 3 and len(parts[0]) == 2:
                            clean_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
                except Exception:
                    pass

                status_desc = "đang chiếu" if src["status"] == "now_showing" else "sắp ra mắt"
                movie_item = {
                    "title": title,
                    "original_title": title,
                    "genre": genres,
                    "duration": dur_num,
                    "release_date": clean_date,
                    "status": src["status"],
                    "formats": ["2D", "3D", "IMAX"],
                    "poster": poster_url,
                    "detail_url": detail_link,
                    "director": "CGV Cinemas",
                    "cast": [],
                    "synopsis": f"Bộ phim hấp dẫn {title} thuộc thể loại {', '.join(genres)}, {status_desc} từ ngày {rel_text} tại hệ thống rạp CGV Cinemas toàn quốc.",
                    "trailer_id": "",
                    "age_rating": "P",
                    "age_desc": "Phim phổ biến cho mọi độ tuổi"
                }

                # Lấy thông tin chi tiết
                if details_fetched < limit_details and detail_link.startswith("http"):
                    det = parse_movie_detail(detail_link)
                    if det["director"]: movie_item["director"] = det["director"]
                    if det["cast"]: movie_item["cast"] = det["cast"]
                    if det["synopsis"]: movie_item["synopsis"] = det["synopsis"]
                    if det["trailer_id"]: movie_item["trailer_id"] = det["trailer_id"]
                    if det["age_rating"]: movie_item["age_rating"] = det["age_rating"]
                    if det["age_desc"]: movie_item["age_desc"] = det["age_desc"]
                    details_fetched += 1

                # Sinh tags cho hệ gợi ý AI
                tags = [title.lower()]
                tags.extend([g.lower() for g in genres])
                tags.extend(["cgv", "chieu rap", "phim hot", "phim moi"])
                if src["status"] == "coming_soon":
                    tags.extend(["sap chieu", "bom tan sap chieu", "trailer"])
                if movie_item["cast"]:
                    tags.extend([c.lower() for c in movie_item["cast"][:3]])
                movie_item["tags"] = list(set(tags))

                all_movies.append(movie_item)

            except Exception as err:
                print(f"Bỏ qua phim lỗi do: {err}")
                continue

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Hoàn tất cào tổng cộng {len(all_movies)} phim từ CGV ({src['name']}).")
    return all_movies

def sync_cgv_movies(force: bool = False) -> dict:
    """
    Đồng bộ phim mới từ CGV vào data/movies.json và cập nhật suất chiếu.
    Nếu force=False và đã cập nhật trong 12 tiếng qua thì giữ nguyên.
    """
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # Kiểm tra trạng thái đồng bộ trước đó
    if not force and os.path.exists(SYNC_STATUS_FILE):
        try:
            with open(SYNC_STATUS_FILE, "r", encoding="utf-8") as f:
                status_info = json.load(f)
            last_sync_time = datetime.strptime(status_info.get("last_sync", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
            diff_hours = (now - last_sync_time).total_seconds() / 3600
            if diff_hours < 12 and status_info.get("status") == "success":
                print(f"Dữ liệu CGV đã được cập nhật cách đây {diff_hours:.1f}h. Bỏ qua bước cào lại.")
                return {
                    "status": "cached",
                    "message": f"Dữ liệu CGV đã được cập nhật hôm nay (cách đây {int(diff_hours)} giờ).",
                    "last_sync": status_info.get("last_sync"),
                    "total_movies": status_info.get("total_movies", 0),
                    "new_movies_added": 0
                }
        except Exception:
            pass

    # Thực hiện cào dữ liệu mới
    cgv_movies = crawl_cgv_movies(limit_details=20)
    if not cgv_movies:
        return {
            "status": "warning",
            "message": "Không thể kết nối hoặc không có dữ liệu mới từ CGV. Giữ nguyên dữ liệu hiện tại.",
            "last_sync": now_str,
            "total_movies": 0,
            "new_movies_added": 0
        }

    # Đọc dữ liệu phim hiện tại
    movies_file = os.path.join(DATA_DIR, "movies.json")
    showtimes_file = os.path.join(DATA_DIR, "showtimes.json")
    cinemas_file = os.path.join(DATA_DIR, "cinemas.json")

    existing_movies = []
    if os.path.exists(movies_file):
        with open(movies_file, "r", encoding="utf-8") as f:
            existing_movies = json.load(f)

    existing_showtimes = []
    if os.path.exists(showtimes_file):
        with open(showtimes_file, "r", encoding="utf-8") as f:
            existing_showtimes = json.load(f)

    cinemas = []
    if os.path.exists(cinemas_file):
        with open(cinemas_file, "r", encoding="utf-8") as f:
            cinemas = json.load(f)
    cinema_ids = [c["id"] for c in cinemas] if cinemas else ["cin_01", "cin_02", "cin_03", "cin_04", "cin_05"]

    # Ánh xạ tên phim đã có để so khớp
    existing_map = {normalize_title(m["title"]): m for m in existing_movies}

    # Tìm max ID hiện tại
    max_id_num = 0
    for m in existing_movies:
        mid = m.get("id", "")
        if mid.startswith("mov_"):
            try:
                num = int(mid.replace("mov_", ""))
                if num > max_id_num:
                    max_id_num = num
            except ValueError:
                pass

    new_added = 0
    new_movies_list = []

    for cgv_m in cgv_movies:
        norm_key = normalize_title(cgv_m["title"])
        if norm_key in existing_map:
            # Cập nhật thông tin nếu có thông tin mới hơn từ CGV
            curr = existing_map[norm_key]
            curr["status"] = "now_showing"
            if cgv_m["poster"] and "unsplash" in curr.get("poster", ""):
                curr["poster"] = cgv_m["poster"]
            if cgv_m["synopsis"] and len(cgv_m["synopsis"]) > len(curr.get("synopsis", "")):
                curr["synopsis"] = cgv_m["synopsis"]
            if cgv_m["trailer_id"]:
                curr["trailer_id"] = cgv_m["trailer_id"]
        else:
            # Thêm phim mới hoàn toàn từ CGV
            max_id_num += 1
            new_id = f"mov_{max_id_num:02d}"
            
            cgv_m["id"] = new_id
            cgv_m["rating"] = round(random.uniform(8.2, 9.4), 1)
            cgv_m["votes"] = random.randint(3000, 15000)

            existing_movies.append(cgv_m)
            existing_map[norm_key] = cgv_m
            new_added += 1
            new_movies_list.append(cgv_m)

            # Tự động sinh suất chiếu giả lập cho phim mới tại các rạp CGV lớn
            selected_cins = random.sample(cinema_ids, min(3, len(cinema_ids)))
            for cin_id in selected_cins:
                existing_showtimes.append({
                    "cinema_id": cin_id,
                    "movie_id": new_id,
                    "date": "Hôm nay",
                    "format": "2D",
                    "screen": f"Cinema {random.randint(1, 6)}",
                    "times": random.choice([
                        ["09:30", "12:15", "15:00", "18:20", "20:50"],
                        ["10:00", "13:30", "16:45", "19:30", "22:15"],
                        ["11:15", "14:20", "17:35", "20:10", "22:45"]
                    ])
                })
                # Thêm suất chiếu IMAX cho phim bom tấn / hành động
                if "Hành động" in cgv_m.get("genre", []) or "Khoa học viễn tưởng" in cgv_m.get("genre", []):
                    existing_showtimes.append({
                        "cinema_id": cin_id,
                        "movie_id": new_id,
                        "date": "Hôm nay",
                        "format": "IMAX",
                        "screen": "IMAX Laser",
                        "times": ["13:00", "16:30", "20:00"]
                    })

    # Ghi lại file movies.json và showtimes.json
    with open(movies_file, "w", encoding="utf-8") as f:
        json.dump(existing_movies, f, ensure_ascii=False, indent=2)

    with open(showtimes_file, "w", encoding="utf-8") as f:
        json.dump(existing_showtimes, f, ensure_ascii=False, indent=2)

    # Ghi trạng thái đồng bộ
    sync_meta = {
        "status": "success",
        "last_sync": now_str,
        "total_movies": len(existing_movies),
        "new_movies_added": new_added,
        "cgv_source_count": len(cgv_movies),
        "message": f"Đồng bộ thành công! Đã cập nhật {new_added} phim mới từ CGV Việt Nam."
    }
    with open(SYNC_STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(sync_meta, f, ensure_ascii=False, indent=2)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] {sync_meta['message']}")
    return sync_meta

if __name__ == "__main__":
    res = sync_cgv_movies(force=True)
    print("Kết quả đồng bộ:", json.dumps(res, ensure_ascii=False, indent=2))
