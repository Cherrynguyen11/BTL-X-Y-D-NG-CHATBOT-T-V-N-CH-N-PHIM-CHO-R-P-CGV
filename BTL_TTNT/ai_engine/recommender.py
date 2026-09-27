import math
import re
from .entity_extractor import remove_accents

class MovieRecommender:
    """
    Hệ thống Gợi ý Phim (Recommendation System) cho CGV
    Sử dụng giải thuật:
    1. Content-Based Filtering: Tính toán Vector Đặc trưng TF-IDF và Cosine Similarity
    2. Constraint & Filter: Lọc theo độ tuổi (P, K, T13, T16, T18), định dạng (IMAX, 4DX, 2D)
    3. Rating & Popularity Weighting: Kết hợp điểm đánh giá phim và độ tương thích người dùng
    """

    def __init__(self, movies: list):
        self.movies = movies
        self.corpus = []
        self.vocab = set()
        self.idf = {}
        self.movie_vectors = []
        
        self._build_content_model()

    def _tokenize(self, text: str) -> list[str]:
        text_clean = remove_accents(text)
        words = re.findall(r'\b[a-z0-9_]{2,}\b', text_clean)
        # Bỏ qua một số stopwords phổ biến
        stopwords = {"la", "va", "cua", "cac", "nhung", "co", "duoc", "trong", "mot", "khi", "cho", "voi", "den"}
        return [w for w in words if w not in stopwords]

    def _build_content_model(self):
        """Xây dựng ma trận TF-IDF cho toàn bộ kho phim"""
        num_docs = len(self.movies)
        if num_docs == 0:
            return

        doc_tokens_list = []
        doc_freq = {}

        for m in self.movies:
            # Ghép toàn bộ nội dung ngữ nghĩa của bộ phim
            content = f"{m.get('title', '')} {' '.join(m.get('genre', []))} " \
                      f"{m.get('synopsis', '')} {' '.join(m.get('tags', []))} " \
                      f"{m.get('director', '')} {' '.join(m.get('cast', []))} " \
                      f"{' '.join(m.get('formats', []))}"
            
            tokens = self._tokenize(content)
            doc_tokens_list.append(tokens)
            
            # Đếm Document Frequency (DF)
            unique_tokens = set(tokens)
            for t in unique_tokens:
                self.vocab.add(t)
                doc_freq[t] = doc_freq.get(t, 0) + 1

        # Tính IDF: log(1 + N / DF)
        for term, df in doc_freq.items():
            self.idf[term] = math.log((num_docs + 1) / (df + 1)) + 1.0

        # Vector hóa từng phim thành vector TF-IDF
        self.movie_vectors = []
        for tokens in doc_tokens_list:
            vec = self._compute_tfidf_vector(tokens)
            self.movie_vectors.append(vec)

    def _compute_tfidf_vector(self, tokens: list[str]) -> dict:
        tf = {}
        total = len(tokens) if tokens else 1
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
            
        vec = {}
        for t, count in tf.items():
            if t in self.idf:
                vec[t] = (count / total) * self.idf[t]
        return vec

    def _cosine_similarity(self, vec1: dict, vec2: dict) -> float:
        """Tính Cosine Similarity giữa 2 vector TF-IDF thưa (sparse dict)"""
        dot_product = 0.0
        for k, v in vec1.items():
            if k in vec2:
                dot_product += v * vec2[k]
                
        norm1 = math.sqrt(sum(v * v for v in vec1.values()))
        norm2 = math.sqrt(sum(v * v for v in vec2.values()))
        
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return dot_product / (norm1 * norm2)

    def recommend(self, query_text: str, entities: dict = None, top_k: int = 3) -> list[dict]:
        """
        Gợi ý phim dựa trên truy vấn người dùng kết hợp bộ lọc thực thể
        """
        if not entities:
            entities = {}
            
        audience = entities.get("audience")
        target_genres = entities.get("genres", [])
        target_formats = entities.get("formats", [])
        
        # Tạo vector TF-IDF cho câu truy vấn của người dùng
        query_tokens = self._tokenize(query_text)
        # Tăng trọng số nếu câu có thể loại
        for g in target_genres:
            query_tokens.extend(self._tokenize(g) * 3)
            
        query_vec = self._compute_tfidf_vector(query_tokens)
        
        results = []
        
        for idx, movie in enumerate(self.movies):
            # Bộ lọc ràng buộc cứng (Hard constraints)
            # 1. Ràng buộc độ tuổi khi đi cùng trẻ em / gia đình có bé nhỏ
            if audience == "trẻ em" and movie.get("age_rating") in ["T16", "T18"]:
                continue
                
            # 2. Bộ lọc định dạng đặc biệt (IMAX, 4DX) nếu người dùng yêu cầu
            if target_formats:
                movie_formats = movie.get("formats", [])
                if not any(f in movie_formats for f in target_formats):
                    continue

            # Tính độ tương đồng ngữ nghĩa TF-IDF Cosine
            movie_vec = self.movie_vectors[idx] if idx < len(self.movie_vectors) else {}
            sim_score = self._cosine_similarity(query_vec, movie_vec)
            
            # Thưởng điểm nếu phim khớp chính xác thể loại mong muốn
            genre_bonus = 0.0
            if target_genres:
                matched_genres = set(target_genres).intersection(set(movie.get("genre", [])))
                genre_bonus = len(matched_genres) * 0.25
                
            # Điểm chất lượng phim (Rating score chuẩn hóa 0 -> 0.2)
            rating_score = (movie.get("rating", 7.0) / 10.0) * 0.2
            
            # Điểm phim đang chiếu ưu tiên hơn phim sắp chiếu
            status_bonus = 0.15 if movie.get("status") == "now_showing" else 0.0
            
            # Tổng hợp điểm gợi ý
            total_score = (sim_score * 0.45) + genre_bonus + rating_score + status_bonus
            
            # Lý do gợi ý
            reasons = []
            if genre_bonus > 0:
                reasons.append(f"Thuộc thể loại bạn thích: {', '.join(target_genres)}")
            if movie.get("rating", 0) >= 8.5:
                reasons.append(f"Điểm đánh giá cực cao ({movie['rating']}/10)")
            if audience and audience in ["trẻ em", "gia đình"] and movie.get("age_rating") in ["P", "K"]:
                reasons.append(f"Phù hợp cho lứa tuổi gia đình ({movie['age_rating']})")
            if not reasons:
                reasons.append("Phim đang rất được khán giả yêu thích tại CGV")
                
            results.append({
                "movie": movie,
                "score": round(total_score, 3),
                "sim_score": round(sim_score, 3),
                "reason": " • ".join(reasons)
            })

        # Sắp xếp theo điểm tổng hợp giảm dần
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
