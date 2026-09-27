import re
import unicodedata

def normalize_text(text: str) -> str:
    if not text:
        return ""
    return text.lower().strip()

def remove_accents(input_str: str) -> str:
    if not input_str:
        return ""
    s1 = unicodedata.normalize('NFD', input_str)
    s2 = ''.join(c for c in s1 if unicodedata.category(c) != 'Mn')
    return s2.replace('đ', 'd').replace('Đ', 'D').lower()

def word_boundary_search(pattern: str, text: str) -> bool:
    """Kiểm tra pattern có xuất hiện như một cụm từ độc lập (không bị lẫn trong từ khác)"""
    escaped = re.escape(pattern.strip())
    # Cho phép so khớp nguyên cụm
    regex = r'(?<!\w)' + escaped + r'(?!\w)'
    return bool(re.search(regex, text))

class EntityExtractor:
    def __init__(self, movies: list, cinemas: list):
        self.movies = movies
        self.cinemas = cinemas
        
        self.genre_keywords = {
            "Hành động": ["hanh dong", "action", "danh nhau", "ban sung", "vo thuat", "chien dau"],
            "Kinh dị": ["kinh di", "horror", "phim ma", "ma da", "quy", "tam linh", "rung ron", "so hai", "am anh"],
            "Hài hước": ["hai", "hai huoc", "comedy", "vui ve", "cuoi vo bung", "giai tri"],
            "Hoạt hình": ["hoat hinh", "anime", "animation", "cartoon", "disney", "pixar", "conan", "doraemon", "minion"],
            "Tình cảm": ["tinh cam", "romance", "lang man", "yeu duong", "hen ho", "tam ly tinh cam", "ngot ngao"],
            "Khoa học viễn tưởng": ["vien tuong", "khoa hoc vien tuong", "sci-fi", "scifi", "vu tru", "ngoai hanh tinh"],
            "Tâm lý": ["tam ly", "drama", "chinh kich", "sau lang", "cam dong", "nuoc mat"],
            "Gia đình": ["gia dinh", "family", "tre em", "con nit", "thieu nhi", "cho be"],
            "Phiêu lưu": ["phieu luu", "adventure", "kham pha"]
        }
        
        self.format_keywords = {
            "IMAX": ["imax", "imax laser"],
            "4DX": ["4dx", "ghe rung", "hieu ung"],
            "3D": ["3d"],
            "2D": ["2d"],
            "Gold Class": ["gold class", "vip", "ghe sofa vip"],
            "Sweetbox": ["sweetbox", "ghe doi", "couple", "cap doi"]
        }
        
        self.city_keywords = {
            "Hà Nội": ["ha noi", "hn", "thu do"],
            "TP. Hồ Chí Minh": ["ho chi minh", "hcm", "sai gon", "tp hcm", "tphcm"],
            "Đà Nẵng": ["da nang", "dn"]
        }
        
        self.time_keywords = {
            "hôm nay": ["hom nay", "ngay nay", "chieu nay", "sang nay"],
            "tối nay": ["toi nay", "dem nay", "buoi toi", "suat toi", "gio muon"],
            "ngày mai": ["ngay mai", "mai"],
            "cuối tuần": ["cuoi tuan", "thu 7", "chu nhat", "t7", "cn"]
        }

        self.duration_patterns = [
    # Dưới X phút
            (r"(?:duoi|ngan hon|khong qua)\s+(\d+)\s*(?:phut|p)", "max"),

    # X phút trở xuống
            (r"(\d+)\s*(?:phut|p)\s*(?:tro xuong|do|toi da)", "max"),

    # Trên X phút
            (r"(?:tren|hon|dai hon)\s+(\d+)\s*(?:phut|p)", "min"),

    # X phút trở lên
            (r"(\d+)\s*(?:phut|p)\s*(?:tro len|trở lên)", "min"),

    # Khoảng X-Y phút
            (r"(?:tu|khoang)\s*(\d+)\s*(?:den|-)\s*(\d+)\s*(?:phut|p)", "range"),

    # X-Y phút
            (r"(\d+)\s*[-–]\s*(\d+)\s*(?:phut|p)", "range"),

    # Dưới X tiếng / giờ
            (r"(?:duoi|ngan hon|khong qua)\s+(\d+(?:[.,]\d+)?)\s*(?:tieng|gio)", "max_hour"),

    # Trên X tiếng / giờ
            (r"(?:tren|hon|dai hon)\s+(\d+(?:[.,]\d+)?)\s*(?:tieng|gio)", "min_hour"),

    # Khoảng X-Y tiếng
            (r"(\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?)\s*(?:tieng|gio)", "range_hour"),
        ]
        self.audience_keywords = {
            "trẻ em": ["tre em", "be", "con nho", "hoc sinh tieu hoc", "con nit", "thieu nhi", "tre con", "cho con"],
            "gia đình": ["gia dinh", "bo me", "ca nha", "nha minh"],
            "cặp đôi": ["nguoi yeu", "ban gai", "ban trai", "cap doi", "hen ho", "2 nguoi", "di 2 nguoi"],
            "bạn bè": ["ban be", "nhom ban", "hoi ban"],
            "một mình": ["1 minh", "mot minh", "di mot minh"]
        }

    def extract_movie(self, text: str):
        """Tìm kiếm tên phim được nhắc tới trong câu"""
        norm_text = remove_accents(text)
        best_match = None
        longest_match_len = 0
        
        # Danh sách alias / tên gọi ngắn đặc trưng cho từng phim
        movie_aliases = {
            "mov_01": ["deadpool", "wolverine", "deadpool 3"],
            "mov_02": ["inside out", "inside out 2", "nhung manh ghep cam xuc"],
            "mov_03": ["conan", "kaito kid", "heiji", "ngoi sao 5 canh"],
            "mov_04": ["ma da", "phim ma da"],
            "mov_05": ["ke trom mat trang", "despicable me", "minion", "gru"],
            "mov_06": ["exhuma", "quat mo trung ma"],
            "mov_07": ["dune", "dune 2", "hanh tinh cat"],
            "mov_08": ["phim mai", "mai tran thanh"],
            "mov_09": ["phim cam", "tam cam"],
            "mov_10": ["joker", "joker 2", "folie a deux"],
            "mov_11": ["quiet place", "vung dat cam lang"],
            "mov_12": ["godzilla", "godzilla x kong", "de che moi"]
        }

        for m in self.movies:
            title_norm = remove_accents(m["title"])
            orig_title_norm = remove_accents(m.get("original_title", ""))
            
            if len(title_norm) >= 4 and word_boundary_search(title_norm, norm_text):
                if len(title_norm) > longest_match_len:
                    best_match = m
                    longest_match_len = len(title_norm)
            elif orig_title_norm and len(orig_title_norm) >= 4 and word_boundary_search(orig_title_norm, norm_text):
                if len(orig_title_norm) > longest_match_len:
                    best_match = m
                    longest_match_len = len(orig_title_norm)
                    
            # So khớp qua aliases độc quyền
            m_id = m.get("id")
            if m_id in movie_aliases:
                for alias in movie_aliases[m_id]:
                    if word_boundary_search(alias, norm_text):
                        if len(alias) > longest_match_len:
                            best_match = m
                            longest_match_len = len(alias)
                        
        return best_match

    def extract_cinema(self, text: str):
        """Tìm rạp CGV được nhắc tới"""
        norm_text = remove_accents(text)
        for c in self.cinemas:
            c_name_norm = remove_accents(c["name"]).replace("cgv ", "")
            # So khớp cụm tên đặc trưng (ví dụ: 'ba trieu', 'landmark 81', 'su van hanh', 'lieu giai', 'metropolis', 'aeon ha dong', 'hung vuong', 'trang tien')
            distinct_names = []
            if "ba trieu" in c_name_norm: distinct_names.append("ba trieu")
            if "landmark 81" in c_name_norm: distinct_names.append("landmark 81")
            if "metropolis" in c_name_norm or "lieu giai" in c_name_norm: 
                distinct_names.extend(["metropolis", "lieu giai"])
            if "aeon ha dong" in c_name_norm: distinct_names.extend(["aeon ha dong", "ha dong"])
            if "su van hanh" in c_name_norm: distinct_names.append("su van hanh")
            if "hung vuong" in c_name_norm: distinct_names.append("hung vuong")
            if "crescent mall" in c_name_norm: distinct_names.append("crescent mall")
            if "trang tien" in c_name_norm: distinct_names.append("trang tien")
            if "da nang" in c_name_norm: distinct_names.append("da nang")

            for dn in distinct_names:
                if word_boundary_search(dn, norm_text):
                    return c
                    
        return None
    
    def extract_duration(self, text: str):
       norm_text = remove_accents(text)

    for pattern, mode in self.duration_patterns:
           match = re.search(pattern, norm_text)

           if not match:
               continue

           if mode == "max":
               return {
                   "min": None,
                   "max": int(match.group(1))
               }

           elif mode == "min":
               return {
                   "min": int(match.group(1)),
                   "max": None
               }

           elif mode == "range":
               return {
                   "min": int(match.group(1)),
                   "max": int(match.group(2))
               }

           elif mode == "max_hour":
               value = float(match.group(1).replace(",", "."))
               return {
                   "min": None,
                   "max": round(value * 60)
               }

           elif mode == "min_hour":
               value = float(match.group(1).replace(",", "."))
               return {
                   "min": round(value * 60),
                   "max": None
               }

           elif mode == "range_hour":
               min_value = float(match.group(1).replace(",", "."))
               max_value = float(match.group(2).replace(",", "."))

             return {
                   "min": round(min_value * 60),
                   "max": round(max_value * 60)
               }

             return None



    def extract_genres(self, text: str) -> list:
        norm_text = remove_accents(text)
        found = []
        for genre, keys in self.genre_keywords.items():
            for k in keys:
                if word_boundary_search(k, norm_text):
                    if genre not in found:
                        found.append(genre)
                    break
        return found

    def extract_formats(self, text: str) -> list:
        norm_text = remove_accents(text)
        found = []
        for fmt, keys in self.format_keywords.items():
            for k in keys:
                if word_boundary_search(k, norm_text):
                    if fmt not in found:
                        found.append(fmt)
                    break
        return found

    def extract_city(self, text: str):
        norm_text = remove_accents(text)
        for city, keys in self.city_keywords.items():
            for k in keys:
                if word_boundary_search(k, norm_text):
                    return city
        return None

    def extract_time(self, text: str):
        norm_text = remove_accents(text)
        for t, keys in self.time_keywords.items():
            for k in keys:
                if word_boundary_search(k, norm_text):
                    return t
        return None

    def extract_audience(self, text: str):
        norm_text = remove_accents(text)
        for aud, keys in self.audience_keywords.items():
            for k in keys:
                if word_boundary_search(k, norm_text):
                    return aud
        return None

    def extract_all(self, text: str) -> dict:
        return {
            "movie": self.extract_movie(text),
            "cinema": self.extract_cinema(text),
            "genres": self.extract_genres(text),
            "formats": self.extract_formats(text),
            "city": self.extract_city(text),
            "time": self.extract_time(text),
            "audience": self.extract_audience(text)
        }
