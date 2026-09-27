/**
 * CGV CINEMAS AI ASSISTANT - CLIENT APPLICATION
 * BTL Môn Trí Tuệ Nhân Tạo (AI / NLP Project)
 */

const API_BASE = "";

// App State
const state = {
    currentTab: "chat",
    geminiKey: localStorage.getItem("cgv_gemini_key") || "",
    movies: [],
    cinemas: [],
    showtimes: [],
    pricesData: null,
    
    // Booking flow state
    bookingMovie: null,
    bookingCinemaId: null,
    bookingShowtime: null,
    bookingFormat: "2D",
    selectedSeats: new Set(),
    seatPrices: {
        standard: 110000,
        vip: 125000,
        sweetbox: 230000
    }
};

// Initialize Application
document.addEventListener("DOMContentLoaded", async () => {
    initSettings();
    
    // Gắn sự kiện click trực tiếp cho các nút chuyển tab
    document.getElementById("tabChatBtn")?.addEventListener("click", () => switchTab("chat"));
    document.getElementById("tabMoviesBtn")?.addEventListener("click", () => switchTab("movies"));
    document.getElementById("tabPricesBtn")?.addEventListener("click", () => switchTab("prices"));

    await fetchInitialData();
    initSeatMap();
});

// Settings & API Key
function initSettings() {
    const keyInput = document.getElementById("inputGeminiKey");
    if (state.geminiKey && keyInput) {
        keyInput.value = state.geminiKey;
        updateEngineBadge(true);
    }
    
    document.getElementById("openSettingsBtn").addEventListener("click", () => {
        document.getElementById("settingsModal").classList.add("active");
    });
}

function closeSettingsModal() {
    document.getElementById("settingsModal").classList.remove("active");
}

async function saveApiKey() {
    const key = document.getElementById("inputGeminiKey").value.trim();
    state.geminiKey = key;
    localStorage.setItem("cgv_gemini_key", key);
    
    try {
        await fetch(`${API_BASE}/api/config/key`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ api_key: key })
        });
        updateEngineBadge(Boolean(key));
        closeSettingsModal();
        appendBotMessage(`✨ Đã lưu cấu hình! Hệ thống hiện đang hoạt động ở chế độ: **${key ? "Cloud Gemini LLM (RAG)" : "Local AI Engine"}**.`);
    } catch (e) {
        console.error("Lỗi cập nhật key:", e);
    }
}

function updateEngineBadge(hasKey) {
    const badgeText = document.getElementById("engineStatusText");
    if (badgeText) {
        badgeText.textContent = hasKey ? "Gemini LLM (RAG)" : "Local AI Engine";
    }
}

// Fetch Initial Movie, Cinema, and Price data
async function fetchInitialData() {
    try {
        const [moviesRes, cinemasRes, pricesRes] = await Promise.all([
            fetch(`${API_BASE}/api/movies`),
            fetch(`${API_BASE}/api/cinemas`),
            fetch(`${API_BASE}/api/prices`)
        ]);

        state.movies = await moviesRes.json();
        state.cinemas = await cinemasRes.json();
        state.pricesData = await pricesRes.json();

        renderMoviesCatalog(state.movies);
        renderPricesAndCombos(state.pricesData);
        populateBookingCinemaDropdown();
        await checkSyncStatus();
    } catch (err) {
        console.error("Lỗi nạp dữ liệu rạp:", err);
    }
}

// Toast notification helper
function showToast(message, type = "info") {
    let container = document.getElementById("toastContainer");
    if (!container) {
        container = document.createElement("div");
        container.id = "toastContainer";
        container.className = "toast-container";
        document.body.appendChild(container);
    }
    const toast = document.createElement("div");
    toast.className = `toast-item toast-${type}`;
    const icon = type === "success" ? "fa-circle-check" : (type === "error" ? "fa-circle-exclamation" : "fa-circle-info");
    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add("fade-out");
        setTimeout(() => toast.remove(), 400);
    }, 4500);
}

// Check CGV Sync Status
async function checkSyncStatus() {
    try {
        const res = await fetch(`${API_BASE}/api/movies/sync-status`);
        const data = await res.json();
        
        const catalogBadge = document.getElementById("catalogSyncText");
        const syncBtnText = document.getElementById("syncBtnText");

        if (data && data.last_sync) {
            const dateParts = data.last_sync.split(" ")[0];
            const timeParts = data.last_sync.split(" ")[1]?.substring(0, 5) || "";
            const todayStr = new Date().toISOString().split("T")[0];
            const timeDisplay = (dateParts === todayStr) ? `Hôm nay ${timeParts}` : dateParts;
            const total = data.total_movies || state.movies.length;
            
            if (catalogBadge) {
                catalogBadge.textContent = `Đồng bộ CGV: ${timeDisplay} (${total} phim)`;
            }
            if (syncBtnText) {
                syncBtnText.textContent = `CGV (${total} phim)`;
            }
        }
    } catch (err) {
        console.warn("Không thể lấy trạng thái đồng bộ CGV:", err);
    }
}

// Trigger manual CGV Sync
let isSyncing = false;
async function triggerCgvSync() {
    if (isSyncing) return;
    isSyncing = true;

    const syncBtn = document.getElementById("syncCgvBtn");
    const syncIcon = document.getElementById("syncIcon");
    const syncBtnText = document.getElementById("syncBtnText");
    const catalogBadge = document.getElementById("catalogSyncText");

    if (syncIcon) syncIcon.classList.add("spinning");
    if (syncBtnText) syncBtnText.textContent = "Đang cào CGV...";
    if (catalogBadge) catalogBadge.textContent = "Đang cào dữ liệu phim từ CGV Việt Nam...";

    showToast("🔄 Đang kết nối tới CGV Việt Nam để cập nhật danh sách phim...", "info");

    try {
        const res = await fetch(`${API_BASE}/api/movies/sync-cgv?force=true`, {
            method: "POST"
        });
        const data = await res.json();

        // Tải lại danh sách phim mới nhất
        const moviesRes = await fetch(`${API_BASE}/api/movies`);
        state.movies = await moviesRes.json();
        renderMoviesCatalog(state.movies);

        const newCount = data.new_movies_added || 0;
        const total = data.total_movies || state.movies.length;

        if (syncBtnText) syncBtnText.textContent = `CGV (${total} phim)`;
        if (catalogBadge) catalogBadge.textContent = `Đồng bộ CGV: Vừa xong (${total} phim)`;

        showToast(`🎉 Đồng bộ thành công! Hiện có ${total} bộ phim (${newCount > 0 ? `+${newCount} phim mới` : "dữ liệu đã cập nhật"}).`, "success");

        // Gửi thông điệp cập nhật trong chatbot
        appendBotMessage(`🍿 **Đã cập nhật dữ liệu phim mới từ CGV Việt Nam!**\n\nTổng cộng hiện có **${total} bộ phim** chiếu rạp toàn quốc (${newCount > 0 ? `vừa thêm **${newCount} phim mới**` : "dữ liệu mới nhất"}).\n\nBạn có thể hỏi Cimi: *"Hôm nay có phim gì mới?"*, hoặc tra cứu chi tiết bất kỳ phim nào bạn quan tâm nhé!`);
    } catch (err) {
        console.error("Lỗi khi đồng bộ CGV:", err);
        showToast("⚠️ Không thể đồng bộ từ CGV lúc này. Vui lòng thử lại sau.", "error");
        if (syncBtnText) syncBtnText.textContent = "Đồng bộ CGV";
    } finally {
        if (syncIcon) syncIcon.classList.remove("spinning");
        isSyncing = false;
    }
}

// Navigation Tab Switching
function switchTab(tabName) {
    state.currentTab = tabName;
    
    // Update Tab Buttons
    document.querySelectorAll(".nav-tab").forEach(btn => btn.classList.remove("active"));
    if (tabName === "chat") document.getElementById("tabChatBtn")?.classList.add("active");
    if (tabName === "movies") document.getElementById("tabMoviesBtn")?.classList.add("active");
    if (tabName === "prices") document.getElementById("tabPricesBtn")?.classList.add("active");

    // Update Views
    const chatView = document.getElementById("viewChat");
    const moviesView = document.getElementById("viewMovies");
    const pricesView = document.getElementById("viewPrices");

    const allViews = [chatView, moviesView, pricesView];
    allViews.forEach(v => {
        if (v) {
            v.classList.remove("active-view");
            v.style.setProperty("display", "none", "important");
        }
    });

    if (tabName === "chat" && chatView) {
        chatView.classList.add("active-view");
        chatView.style.setProperty("display", "flex", "important");
    } else if (tabName === "movies" && moviesView) {
        moviesView.classList.add("active-view");
        moviesView.style.setProperty("display", "flex", "important");
    } else if (tabName === "prices" && pricesView) {
        pricesView.classList.add("active-view");
        pricesView.style.setProperty("display", "flex", "important");
    }
}
window.switchTab = switchTab;

// Markdown formatting helper
function formatMarkdown(text) {
    if (!text) return "";
    let html = text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/_(.*?)_/g, '<em>$1</em>')
        .replace(/\n\n/g, '<br><br>')
        .replace(/\n• /g, '<br>• ')
        .replace(/\n/g, '<br>');
    return html;
}

// Chat Flow
async function handleChatSubmit(e) {
    e.preventDefault();
    const input = document.getElementById("chatInput");
    const msg = input.value.trim();
    if (!msg) return;

    input.value = "";
    appendUserMessage(msg);
    showTypingIndicator();

    try {
        const res = await fetch(`${API_BASE}/api/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: msg,
                gemini_key: state.geminiKey || null
            })
        });

        const data = await res.json();
        removeTypingIndicator();

        // Render Bot response
        appendBotResponse(data);

        // Update AI Inspector Sidebar
        updateInspector(data);

    } catch (err) {
        removeTypingIndicator();
        console.error("Lỗi gọi API chat:", err);
        appendBotMessage("⚠️ Rất tiếc, đã có lỗi kết nối đến máy chủ AI. Bạn hãy thử lại câu hỏi nhé!");
    }
}

function sendQuickMessage(text) {
    document.getElementById("chatInput").value = text;
    document.getElementById("chatForm").dispatchEvent(new Event("submit"));
}

function appendUserMessage(text) {
    const chatMessages = document.getElementById("chatMessages");
    const group = document.createElement("div");
    group.className = "message-group user-group";
    group.innerHTML = `
        <div class="user-avatar"><i class="fa-solid fa-user"></i></div>
        <div class="message-content">
            <div class="user-name">Bạn</div>
            <div class="chat-bubble user-bubble">${escapeHtml(text)}</div>
        </div>
    `;
    chatMessages.appendChild(group);
    scrollToBottom();
}

function appendBotMessage(text) {
    const chatMessages = document.getElementById("chatMessages");
    const group = document.createElement("div");
    group.className = "message-group bot-group";
    group.innerHTML = `
        <div class="bot-avatar"><i class="fa-solid fa-robot"></i></div>
        <div class="message-content">
            <div class="bot-name">Cimi • CGV AI Assistant <span class="badge-verified"><i class="fa-solid fa-circle-check"></i></span></div>
            <div class="chat-bubble bot-bubble">${formatMarkdown(text)}</div>
        </div>
    `;
    chatMessages.appendChild(group);
    scrollToBottom();
}

function appendBotResponse(data) {
    const chatMessages = document.getElementById("chatMessages");
    const group = document.createElement("div");
    group.className = "message-group bot-group";

    let moviesHtml = "";
    if (data.suggested_movies && data.suggested_movies.length > 0) {
        moviesHtml = `
            <div class="chat-movies-carousel">
                ${data.suggested_movies.map(m => renderMovieCardChat(m)).join("")}
            </div>
        `;
    }

    let showtimesHtml = "";
    if (data.showtimes && data.showtimes.length > 0 && (!data.suggested_movies || data.suggested_movies.length === 0)) {
        showtimesHtml = `
            <div class="chat-showtimes-box" style="margin-top:0.75rem; background: rgba(0,0,0,0.3); padding:0.75rem; border-radius:8px; border:1px solid rgba(255,255,255,0.08);">
                <div style="font-weight:700; color:var(--cgv-gold); font-size:0.85rem; margin-bottom:0.4rem;">
                    <i class="fa-regular fa-clock"></i> CÁC SUẤT CHIẾU GỢI Ý HÔM NAY:
                </div>
                ${data.showtimes.map(st => `
                    <div style="font-size:0.82rem; margin-bottom:0.4rem;">
                        <strong>${st.cinema_name}</strong> (${st.format}): 
                        <span style="color:#10b981; font-weight:600;">${st.times.join(", ")}</span>
                    </div>
                `).join("")}
            </div>
        `;
    }

    group.innerHTML = `
        <div class="bot-avatar"><i class="fa-solid fa-robot"></i></div>
        <div class="message-content" style="max-width: 100%;">
            <div class="bot-name">Cimi • CGV AI Assistant <span class="badge-verified"><i class="fa-solid fa-circle-check"></i></span></div>
            <div class="chat-bubble bot-bubble">
                ${formatMarkdown(data.reply)}
                ${showtimesHtml}
            </div>
            ${moviesHtml}
        </div>
    `;

    chatMessages.appendChild(group);

    // Update dynamic chips row
    renderDynamicChips(data.quick_replies);

    scrollToBottom();
}

function renderMovieCardChat(m) {
    const ageClass = `age-${m.age_rating || 'P'}`;
    const reason = m.ai_reason ? `<div class="chat-card-reason"><i class="fa-solid fa-wand-magic-sparkles"></i> ${m.ai_reason}</div>` : '';
    
    return `
        <div class="movie-card-chat">
            <div class="chat-poster-wrapper">
                <img src="${m.poster}" alt="${m.title}" class="chat-poster-img" loading="lazy" onerror="this.src='https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=600'">
                <span class="age-badge ${ageClass}">${m.age_rating}</span>
                <span class="rating-badge"><i class="fa-solid fa-star"></i> ${m.rating}</span>
            </div>
            <div class="chat-card-info">
                <h4 class="chat-card-title" title="${m.title}">${m.title}</h4>
                <div class="chat-card-genres">${(m.genre || []).slice(0, 2).join(", ")} • ${m.duration}p</div>
                ${reason}
                <div class="chat-card-actions">
                    <button class="btn-card-action" onclick="openTrailerModal('${m.trailer_id}', '${escapeHtml(m.title)}')">
                        <i class="fa-solid fa-play"></i> Trailer
                    </button>
                    <button class="btn-card-action btn-primary" onclick="openBookingForMovie('${m.id}')">
                        <i class="fa-solid fa-ticket"></i> Đặt vé
                    </button>
                </div>
            </div>
        </div>
    `;
}

function renderDynamicChips(chips) {
    const row = document.getElementById("dynamicChipsRow");
    if (!row || !chips) return;
    row.innerHTML = chips.map(c => `
        <button type="button" class="quick-chip" onclick="sendQuickMessage('${escapeHtml(c)}')">${c}</button>
    `).join("");
}

function updateInspector(data) {
    const intentEl = document.getElementById("inspectIntent");
    const confEl = document.getElementById("inspectConfidence");
    const confBar = document.getElementById("inspectConfidenceBar");
    const entitiesEl = document.getElementById("inspectEntities");

    if (intentEl) intentEl.textContent = data.intent;
    const confPercent = Math.round((data.confidence || 0.95) * 100);
    if (confEl) confEl.textContent = `${confPercent}%`;
    if (confBar) confBar.style.width = `${confPercent}%`;

    if (entitiesEl) {
        const tags = [];
        const ent = data.entities || {};
        if (ent.movie) tags.push(`Phim: <strong>${ent.movie}</strong>`);
        if (ent.cinema) tags.push(`Rạp: <strong>${ent.cinema}</strong>`);
        if (ent.genres && ent.genres.length) tags.push(`Thể loại: <strong>${ent.genres.join(", ")}</strong>`);
        if (ent.audience) tags.push(`Đối tượng: <strong>${ent.audience}</strong>`);
        if (ent.time) tags.push(`Thời gian: <strong>${ent.time}</strong>`);
        if (ent.formats && ent.formats.length) tags.push(`Định dạng: <strong>${ent.formats.join(", ")}</strong>`);

        if (tags.length > 0) {
            entitiesEl.innerHTML = tags.map(t => `<span class="ner-badge">${t}</span>`).join("");
        } else {
            entitiesEl.innerHTML = `<span class="ner-badge tag-empty">Không phát hiện thực thể riêng</span>`;
        }
    }
}

function showTypingIndicator() {
    const chatMessages = document.getElementById("chatMessages");
    const ind = document.createElement("div");
    ind.id = "typingIndicator";
    ind.className = "message-group bot-group";
    ind.innerHTML = `
        <div class="bot-avatar"><i class="fa-solid fa-robot"></i></div>
        <div class="message-content">
            <div class="typing-indicator">
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
            </div>
        </div>
    `;
    chatMessages.appendChild(ind);
    scrollToBottom();
}

function removeTypingIndicator() {
    const ind = document.getElementById("typingIndicator");
    if (ind) ind.remove();
}

function scrollToBottom() {
    const chat = document.getElementById("chatMessages");
    if (chat) {
        chat.scrollTop = chat.scrollHeight;
    }
}

// Voice Input (Web Speech API)
let speechRecognizer = null;
function toggleVoiceInput() {
    const micBtn = document.getElementById("btnVoiceInput");
    if (!("webkitSpeechRecognition" in window) && !("SpeechRecognition" in window)) {
        alert("Trình duyệt của bạn chưa hỗ trợ Web Speech API. Hãy sử dụng Google Chrome để trải nghiệm tính năng này!");
        return;
    }

    if (speechRecognizer) {
        speechRecognizer.stop();
        speechRecognizer = null;
        micBtn.classList.remove("recording");
        return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    speechRecognizer = new SpeechRecognition();
    speechRecognizer.lang = "vi-VN";
    speechRecognizer.interimResults = false;
    speechRecognizer.maxAlternatives = 1;

    speechRecognizer.onstart = () => {
        micBtn.classList.add("recording");
    };

    speechRecognizer.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        document.getElementById("chatInput").value = transcript;
        sendQuickMessage(transcript);
    };

    speechRecognizer.onerror = (e) => {
        console.error("Voice input error:", e);
        micBtn.classList.remove("recording");
        speechRecognizer = null;
    };

    speechRecognizer.onend = () => {
        micBtn.classList.remove("recording");
        speechRecognizer = null;
    };

    speechRecognizer.start();
}

// TAB 2: RENDER MOVIES CATALOG
function renderMoviesCatalog(movies) {
    const grid = document.getElementById("moviesGrid");
    if (!grid) return;

    grid.innerHTML = movies.map(m => {
        const ageClass = `age-${m.age_rating || 'P'}`;
        const formatsHtml = (m.formats || []).map(f => `<span class="format-pill">${f}</span>`).join("");

        return `
            <div class="catalog-movie-card">
                <div class="catalog-poster-box">
                    <img src="${m.poster}" alt="${m.title}" class="catalog-poster-img" loading="lazy" onerror="this.src='https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=600'">
                    <span class="age-badge ${ageClass}">${m.age_rating}</span>
                    <span class="rating-badge"><i class="fa-solid fa-star"></i> ${m.rating}</span>
                </div>
                <div class="catalog-card-body">
                    <h3 class="catalog-card-title">${m.title}</h3>
                    <div class="catalog-card-orig">${m.original_title || ''}</div>
                    <div class="catalog-card-meta">
                        <div><i class="fa-regular fa-clock"></i> ${m.duration} phút</div>
                        <div><i class="fa-solid fa-masks-theater"></i> ${(m.genre || []).join(", ")}</div>
                        <div><i class="fa-solid fa-user-tie"></i> ĐD: ${m.director}</div>
                    </div>
                    <div class="catalog-card-formats">${formatsHtml}</div>
                    <div class="catalog-actions">
                        <button class="btn-card-action" onclick="openTrailerModal('${m.trailer_id}', '${escapeHtml(m.title)}')">
                            <i class="fa-solid fa-play"></i> Trailer
                        </button>
                        <button class="btn-card-action btn-primary" onclick="openBookingForMovie('${m.id}')">
                            <i class="fa-solid fa-ticket"></i> Đặt vé
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join("");
}

function filterCatalog(category, btn) {
    document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");

    let filtered = state.movies;
    if (category === "now_showing") {
        filtered = state.movies.filter(m => m.status === "now_showing");
    } else if (category === "coming_soon") {
        filtered = state.movies.filter(m => m.status === "coming_soon");
    } else if (category === "IMAX") {
        filtered = state.movies.filter(m => m.formats && m.formats.includes("IMAX"));
    }
    renderMoviesCatalog(filtered);
}

// TAB 3: RENDER PRICES & COMBOS
function renderPricesAndCombos(data) {
    if (!data) return;

    // 1. Ticket Prices
    const ticketBox = document.getElementById("ticketPricesContainer");
    if (ticketBox && data.ticket_prices) {
        ticketBox.innerHTML = `
            <div class="pricing-item-row">
                <span>Vé 2D Chuẩn (Thứ 2 - Thứ 5):</span>
                <strong>85.000đ - 110.000đ</strong>
            </div>
            <div class="pricing-item-row">
                <span>Ưu đãi học sinh, sinh viên & U22:</span>
                <strong style="color:#10b981;">55.000đ - 75.000đ</strong>
            </div>
            <div class="pricing-item-row">
                <span>Vé 2D Cuối tuần (T6, T7, CN):</span>
                <strong>110.000đ - 135.000đ</strong>
            </div>
            <div class="pricing-item-row">
                <span>Ghế VIP phụ thu:</span>
                <strong>+10.000đ - 15.000đ</strong>
            </div>
            <div class="pricing-item-row">
                <span>Ghế đôi Sweetbox (2 người):</span>
                <strong>180.000đ - 260.000đ</strong>
            </div>
            <div class="pricing-item-row">
                <span>Vé IMAX Laser:</span>
                <strong>150.000đ - 230.000đ</strong>
            </div>
            <div class="pricing-item-row">
                <span>Vé 4DX (Ghế rung, hiệu ứng):</span>
                <strong>140.000đ - 210.000đ</strong>
            </div>
            <div class="pricing-item-row">
                <span>Gold Class VIP (Sofa ngả 180°, trà/cà phê):</span>
                <strong>300.000đ / vé</strong>
            </div>
        `;
    }

    // 2. Promotions
    const promoBox = document.getElementById("promotionsContainer");
    if (promoBox && data.promotions) {
        promoBox.innerHTML = data.promotions.map(p => `
            <div class="promo-item">
                <div class="promo-item-title"><i class="fa-solid fa-gift"></i> ${p.name}</div>
                <div class="promo-item-desc">${p.desc}</div>
            </div>
        `).join("");
    }

    // 3. Combos
    const combosBox = document.getElementById("combosContainer");
    if (combosBox && data.combos) {
        combosBox.innerHTML = data.combos.map(cb => `
            <div class="combo-card">
                <div>
                    <h4 class="combo-card-name"><i class="fa-solid fa-popcorn"></i> ${cb.name}</h4>
                    <p class="combo-card-desc">${cb.desc}</p>
                </div>
                <div class="combo-card-price">${cb.price}</div>
            </div>
        `).join("");
    }
}

// TRAILER MODAL
function openTrailerModal(trailerId, title) {
    const modal = document.getElementById("trailerModal");
    const container = document.getElementById("videoContainer");
    document.getElementById("trailerTitle").textContent = `Trailer: ${title}`;

    container.innerHTML = `
        <iframe src="https://www.youtube-nocookie.com/embed/${trailerId}?autoplay=1" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
    `;
    modal.classList.add("active");
}

function closeTrailerModal() {
    const modal = document.getElementById("trailerModal");
    modal.classList.remove("active");
    document.getElementById("videoContainer").innerHTML = "";
}

// BOOKING FLOW & SEAT MAP
function populateBookingCinemaDropdown() {
    const select = document.getElementById("bookingCinemaSelect");
    if (!select) return;
    select.innerHTML = state.cinemas.map(c => `
        <option value="${c.id}">${c.name} (${c.city})</option>
    `).join("");
}

function openBookingForMovie(movieId) {
    const movie = state.movies.find(m => m.id === movieId);
    if (!movie) return;

    state.bookingMovie = movie;
    state.selectedSeats.clear();
    updateBookingSummary();

    document.getElementById("bookingMovieTitle").textContent = `Đặt vé: ${movie.title}`;
    document.getElementById("bookingMovieSub").textContent = `${(movie.genre || []).join(", ")} • ${movie.duration} phút • Độ tuổi: ${movie.age_rating}`;

    onBookingCinemaChange();
    document.getElementById("bookingModal").classList.add("active");
}

function closeBookingModal() {
    document.getElementById("bookingModal").classList.remove("active");
}

function onBookingCinemaChange() {
    const cinemaId = document.getElementById("bookingCinemaSelect").value;
    state.bookingCinemaId = cinemaId;

    // Render sample showtimes
    const chipsBox = document.getElementById("bookingShowtimeChips");
    const times = ["10:30", "13:45", "16:15", "19:00", "21:30", "23:15"];
    
    chipsBox.innerHTML = times.map((t, idx) => `
        <button type="button" class="time-chip ${idx === 3 ? 'active' : ''}" onclick="selectBookingShowtime('${t}', this)">${t}</button>
    `).join("");

    state.bookingShowtime = "19:00";
    initSeatMap();
}

function selectBookingShowtime(time, chip) {
    document.querySelectorAll(".time-chip").forEach(c => c.classList.remove("active"));
    chip.classList.add("active");
    state.bookingShowtime = time;
}

function initSeatMap() {
    const grid = document.getElementById("cinemaSeatsGrid");
    if (!grid) return;

    grid.innerHTML = "";
    const rows = ["A", "B", "C", "D", "E", "F"];
    
    // Seeded pseudo-booked seats
    const bookedSeats = ["B4", "B5", "D5", "D6", "E3"];

    rows.forEach(row => {
        const rowDiv = document.createElement("div");
        rowDiv.className = "seat-row";

        const label = document.createElement("span");
        label.className = "row-label";
        label.textContent = row;
        rowDiv.appendChild(label);

        if (row === "F") {
            // Sweetbox couple seats row (5 pairs)
            for (let p = 1; p <= 5; p++) {
                const seatId = `F${p*2-1},F${p*2}`;
                const btn = document.createElement("button");
                btn.className = "seat-btn sweetbox";
                btn.textContent = `SW${p}`;
                btn.onclick = () => toggleSeat(seatId, "sweetbox", btn);
                rowDiv.appendChild(btn);
            }
        } else {
            // Standard and VIP rows (10 seats per row)
            for (let num = 1; num <= 10; num++) {
                const seatId = `${row}${num}`;
                const isVip = (row === "C" || row === "D") && (num >= 3 && num <= 8);
                const isBooked = bookedSeats.includes(seatId);

                const btn = document.createElement("button");
                btn.className = `seat-btn ${isVip ? 'vip' : 'standard'} ${isBooked ? 'booked' : ''}`;
                btn.textContent = num;
                btn.disabled = isBooked;
                btn.onclick = () => toggleSeat(seatId, isVip ? 'vip' : 'standard', btn);
                rowDiv.appendChild(btn);
            }
        }

        const labelEnd = document.createElement("span");
        labelEnd.className = "row-label";
        labelEnd.textContent = row;
        rowDiv.appendChild(labelEnd);

        grid.appendChild(rowDiv);
    });
}

function toggleSeat(seatId, type, btn) {
    if (state.selectedSeats.has(seatId)) {
        state.selectedSeats.delete(seatId);
        btn.classList.remove("selected");
    } else {
        if (state.selectedSeats.size >= 8) {
            alert("Mỗi lần đặt vé chỉ chọn tối đa 8 ghế!");
            return;
        }
        state.selectedSeats.add(seatId);
        btn.classList.add("selected");
    }
    updateBookingSummary();
}

function updateBookingSummary() {
    const seatsArr = Array.from(state.selectedSeats);
    const selectedText = document.getElementById("selectedSeatsText");
    const totalText = document.getElementById("totalPriceText");
    const confirmBtn = document.getElementById("btnConfirmBooking");

    if (seatsArr.length === 0) {
        selectedText.textContent = "Chưa chọn ghế";
        totalText.textContent = "0 VNĐ";
        confirmBtn.disabled = true;
        return;
    }

    let total = 0;
    seatsArr.forEach(seat => {
        if (seat.startsWith("F")) {
            total += state.seatPrices.sweetbox;
        } else if (seat.startsWith("C") || seat.startsWith("D")) {
            total += state.seatPrices.vip;
        } else {
            total += state.seatPrices.standard;
        }
    });

    selectedText.textContent = seatsArr.join(", ");
    totalText.textContent = `${total.toLocaleString("vi-VN")} VNĐ`;
    confirmBtn.disabled = false;
}

async function submitBooking() {
    if (!state.bookingMovie || state.selectedSeats.size === 0) return;

    const payload = {
        movie_id: state.bookingMovie.id,
        cinema_id: state.bookingCinemaId,
        showtime: state.bookingShowtime || "19:00",
        format: "2D",
        seats: Array.from(state.selectedSeats)
    };

    try {
        const res = await fetch(`${API_BASE}/api/book-seat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        closeBookingModal();
        showTicketPass(data);
    } catch (e) {
        console.error("Lỗi đặt vé:", e);
        alert("Có lỗi khi tạo vé. Vui lòng thử lại!");
    }
}

function showTicketPass(ticket) {
    document.getElementById("tMovieTitle").textContent = ticket.movie_title;
    document.getElementById("tCinema").textContent = ticket.cinema_name;
    document.getElementById("tTime").textContent = `${ticket.showtime} (${ticket.booking_time})`;
    document.getElementById("tFormat").textContent = ticket.format;
    document.getElementById("tSeats").textContent = ticket.seats.join(", ");
    document.getElementById("tCode").textContent = ticket.ticket_code;
    document.getElementById("tPrice").textContent = ticket.total_price;

    document.getElementById("ticketModal").classList.add("active");

    // Also send an automated bot confirmation in chat
    appendBotMessage(
        `🎉 **Chúc mừng bạn đã đặt vé thành công!**\n\n` +
        `• **Phim**: ${ticket.movie_title}\n` +
        `• **Rạp**: ${ticket.cinema_name}\n` +
        `• **Suất chiếu**: ${ticket.showtime} (${ticket.booking_time})\n` +
        `• **Ghế ngồi**: ${ticket.seats.join(", ")}\n` +
        `• **Mã vé CGV**: \`${ticket.ticket_code}\`\n\n` +
        `Bạn hãy lưu lại mã vé để nhận vé tại quầy CGV trước giờ chiếu 15 phút nhé. Chúc bạn có những phút giây xem phim tuyệt vời! 🍿🥤`
    );
}

function closeTicketModal() {
    document.getElementById("ticketModal").classList.remove("active");
    switchTab("chat");
}

function escapeHtml(str) {
    if (!str) return "";
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
