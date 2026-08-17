import "./style.css";

const API = "http://127.0.0.1:8001";


// =========================================================
// STATE
// =========================================================

let token =
    localStorage.getItem("winky_token") || "";

let username =
    localStorage.getItem("winky_username") || "";

let currentConversation = null;
let isGenerating = false;
let abortController = null;

let webSearchEnabled = false;

let selectedFileId = null;
let uploadedFileName = "";

let recognition = null;
let isListening = false;
let autoSendVoice = true;


// =========================================================
// FINAL INTEGRATION STATE
// =========================================================

let currentPlan = "free";

let currentRouterModel = "";

let currentTools = [];

let currentToolStatus = {};

let currentSources = [];

let currentOnline = true;


// =========================================================
// ELEMENTS
// =========================================================

const authScreen =
    document.getElementById("authScreen");

const app =
    document.getElementById("app");

const authUsername =
    document.getElementById("authUsername");

const authPassword =
    document.getElementById("authPassword");

const authError =
    document.getElementById("authError");

const loginButton =
    document.getElementById("loginButton");

const registerButton =
    document.getElementById("registerButton");

const logoutButton =
    document.getElementById("logoutButton");

const usernameDisplay =
    document.getElementById("usernameDisplay");

const messages =
    document.getElementById("messages");

const input =
    document.getElementById("input");

const sendButton =
    document.getElementById("sendButton");

const stopButton =
    document.getElementById("stopButton");

const historyList =
    document.getElementById("historyList");

const newChatButton =
    document.getElementById("newChat");

const memoryButton =
    document.getElementById("memoryButton");

const filesButton =
    document.getElementById("filesButton");

const exportButton =
    document.getElementById("exportButton");

const settingsButton =
    document.getElementById("settingsButton");

const fileInput =
    document.getElementById("fileInput");

const webButton =
    document.getElementById("webButton");

const voiceButton =
    document.getElementById("voiceButton");

const fileStatus =
    document.getElementById("fileStatus");

const memoryPanel =
    document.getElementById("memoryPanel");

const closeMemory =
    document.getElementById("closeMemory");

const memoryList =
    document.getElementById("memoryList");

const memoryKey =
    document.getElementById("memoryKey");

const memoryValue =
    document.getElementById("memoryValue");

const saveMemoryButton =
    document.getElementById("saveMemory");

const filesPanel =
    document.getElementById("filesPanel");

const closeFiles =
    document.getElementById("closeFiles");

const fileList =
    document.getElementById("fileList");

const settingsPanel =
    document.getElementById("settingsPanel");

const closeSettings =
    document.getElementById("closeSettings");

const modelSelect =
    document.getElementById("modelSelect");

const backendStatus =
    document.getElementById("backendStatus");

const ollamaStatus =
    document.getElementById("ollamaStatus");


// =========================================================
// ROBOT ELEMENTS
// =========================================================

const winkyRobot =
    document.getElementById("winkyRobot");

const robotStatus =
    document.getElementById("robotStatus");


// =========================================================
// API
// =========================================================

function authHeaders(json = false) {

    const headers = {};

    if (json) {

        headers["Content-Type"] =
            "application/json";
    }

    if (token) {

        headers["Authorization"] =
            `Bearer ${token}`;
    }

    return headers;
}


async function apiFetch(
    url,
    options = {}
) {

    options.headers = {

        ...authHeaders(
            options.body !== undefined
        ),

        ...(options.headers || {})
    };

    return fetch(
        url,
        options
    );
}


// =========================================================
// AUTH UI
// =========================================================

function showAuth() {

    if (authScreen) {

        authScreen.style.display =
            "flex";
    }

    if (app) {

        app.style.display =
            "none";
    }

    hideRobot();
}


function showApp() {

    if (authScreen) {

        authScreen.style.display =
            "none";
    }

    if (app) {

        app.style.display =
            "flex";
    }

    if (usernameDisplay) {

        usernameDisplay.textContent =
            username;
    }

    document.body.dataset.plan =
        currentPlan || "free";

    showRobot();

    setRobotState(
        "welcome"
    );

    setTimeout(
        () => {

            speakWinky(
                "Halo, saya adalah Winky AI. Selamat datang dan siap membantu Anda hari ini."
            );

        },
        300
    );

    setTimeout(
        () => {

            hideRobot();

        },
        5500
    );
}


function setAuthError(message) {

    if (authError) {

        authError.textContent =
            message || "";
    }
}


// =========================================================
// LOGIN
// =========================================================

async function login() {

    setAuthError("");

    const user =
        authUsername.value.trim();

    const password =
        authPassword.value;

    if (!user || !password) {

        setAuthError(
            "Username dan password harus diisi."
        );

        return;
    }

    try {

        const response =
            await fetch(
                `${API}/api/auth/login`,
                {

                    method:
                        "POST",

                    headers: {

                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({

                            username:
                                user,

                            password
                        })
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Login gagal."
            );
        }

        token =
            data.token;

        username =
            data.username;

        localStorage.setItem(
            "winky_token",
            token
        );

        localStorage.setItem(
            "winky_username",
            username
        );

        authPassword.value =
            "";

        showApp();

        await startApp();

    } catch (error) {

        setAuthError(
            error.message
        );
    }
}


// =========================================================
// REGISTER
// =========================================================

async function register() {

    setAuthError("");

    const user =
        authUsername.value.trim();

    const password =
        authPassword.value;

    if (!user || !password) {

        setAuthError(
            "Username dan password harus diisi."
        );

        return;
    }

    try {

        const response =
            await fetch(
                `${API}/api/auth/register`,
                {

                    method:
                        "POST",

                    headers: {

                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({

                            username:
                                user,

                            password
                        })
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Registrasi gagal."
            );
        }

        token =
            data.token;

        username =
            data.username;

        localStorage.setItem(
            "winky_token",
            token
        );

        localStorage.setItem(
            "winky_username",
            username
        );

        authPassword.value =
            "";

        showApp();

        await startApp();

    } catch (error) {

        setAuthError(
            error.message
        );
    }
}


// =========================================================
// LOGOUT
// =========================================================

async function logout() {

    try {

        await apiFetch(
            `${API}/api/auth/logout`,
            {

                method:
                    "POST"
            }
        );

    } catch {
        // Abaikan error logout
    }

    stopWinkyVoice();

    if (
        recognition &&
        isListening
    ) {

        try {

            recognition.stop();

        } catch {}
    }

    token = "";

    username = "";

    currentConversation =
        null;

    selectedFileId =
        null;

    uploadedFileName =
        "";

    currentPlan =
        "free";

    currentRouterModel =
        "";

    currentTools =
        [];

    currentToolStatus =
        [];

    currentSources =
        [];

    localStorage.removeItem(
        "winky_token"
    );

    localStorage.removeItem(
        "winky_username"
    );

    showAuth();
}


// =========================================================
// HELPERS
// =========================================================

function escapeHtml(text) {

    return String(text ?? "")
        .replace(
            /&/g,
            "&amp;"
        )
        .replace(
            /</g,
            "&lt;"
        )
        .replace(
            />/g,
            "&gt;"
        )
        .replace(
            /"/g,
            "&quot;"
        )
        .replace(
            /'/g,
            "&#039;"
        );
}


function scrollBottom() {

    if (!messages) {
        return;
    }

    messages.scrollTop =
        messages.scrollHeight;
}


function showWelcome() {

    if (!messages) {
        return;
    }

    messages.innerHTML = `

        <div class="welcome">

            <div class="welcome-orb">

                <div class="welcome-logo">
                    W
                </div>

            </div>

            <h1>
                Halo, saya Winky AI
            </h1>

            <p>
                Apa yang ingin kamu kerjakan hari ini?
            </p>

        </div>

    `;
}


// =========================================================
// ROBOT
// =========================================================

function showRobot() {

    if (!winkyRobot) {
        return;
    }

    winkyRobot.classList.remove(
        "hidden"
    );
}


function hideRobot() {

    if (!winkyRobot) {
        return;
    }

    winkyRobot.classList.add(
        "hidden"
    );
}


function setRobotState(
    state,
    text = ""
) {

    if (!winkyRobot) {
        return;
    }

    winkyRobot.classList.remove(
        "idle",
        "listening",
        "thinking",
        "speaking",
        "welcome"
    );

    winkyRobot.classList.add(
        state
    );

    if (robotStatus) {

        const statusText = {

            idle:
                "Halo, saya Winky AI",

            welcome:
                "Selamat datang di Winky AI",

            listening:
                "Winky sedang mendengarkan...",

            thinking:
                "Winky sedang berpikir...",

            speaking:
                "Winky sedang berbicara..."
        };

        robotStatus.textContent =
            text ||
            statusText[state] ||
            "Winky AI";
    }
}


// =========================================================
// MARKDOWN
// =========================================================

function renderMarkdown(text) {

    if (!text) {
        return "";
    }

    let safe =
        escapeHtml(text);

    const blocks = [];

    safe = safe.replace(
        /```([\w+-]*)\n?([\s\S]*?)```/g,
        (
            _,
            language,
            code
        ) => {

            const index =
                blocks.length;

            blocks.push({

                language:
                    language ||
                    "code",

                code:
                    code.trim()
            });

            return (
                `___CODE_${index}___`
            );
        }
    );

    safe = safe.replace(
        /\*\*(.*?)\*\*/g,
        "<strong>$1</strong>"
    );

    safe = safe.replace(
        /`([^`\n]+)`/g,
        "<code>$1</code>"
    );

    safe = safe.replace(
        /^### (.*)$/gm,
        "<h3>$1</h3>"
    );

    safe = safe.replace(
        /^## (.*)$/gm,
        "<h2>$1</h2>"
    );

    safe = safe.replace(
        /^# (.*)$/gm,
        "<h1>$1</h1>"
    );

    safe = safe.replace(
        /^[-*] (.*)$/gm,
        "• $1"
    );

    safe = safe.replace(
        /\n/g,
        "<br>"
    );

    blocks.forEach(
        (
            block,
            index
        ) => {

            safe = safe.replace(

                `___CODE_${index}___`,

                `

                <div class="code-box">

                    <div class="code-head">

                        <span>
                            ${escapeHtml(
                                block.language
                            )}
                        </span>

                        <button
                            class="copy-code"
                            data-code="${encodeURIComponent(
                                block.code
                            )}"
                        >
                            Copy
                        </button>

                    </div>

                    <pre>${escapeHtml(
                        block.code
                    )}</pre>

                </div>

                `
            );
        }
    );

    return safe;
}


// =========================================================
// MESSAGE
// =========================================================

function addMessage(
    text,
    role
) {

    const wrapper =
        document.createElement(
            "div"
        );

    wrapper.className =
        `message ${role}`;

    const bubble =
        document.createElement(
            "div"
        );

    bubble.className =
        "bubble";

    if (role === "ai") {

        bubble.innerHTML =
            renderMarkdown(
                text
            );

    } else {

        bubble.textContent =
            text;
    }

    wrapper.appendChild(
        bubble
    );

    messages.appendChild(
        wrapper
    );

    scrollBottom();

    return {

        wrapper,

        bubble
    };
}


// =========================================================
// ROUTER STATUS
// =========================================================

function showAIStatus(data) {

    currentRouterModel =
        data.model ||
        "";

    currentTools =
        Array.isArray(
            data.tools
        )
            ? data.tools
            : [];

    currentToolStatus =
        data.tool_status &&
        typeof data.tool_status ===
            "object"
            ? data.tool_status
            : {};

    currentOnline =
        data.online !== false;

    console.log(
        "Winky Router:",
        {

            model:
                currentRouterModel,

            tools:
                currentTools,

            toolStatus:
                currentToolStatus,

            online:
                currentOnline
        }
    );

    document.body.dataset.online =
        currentOnline
            ? "true"
            : "false";
}


// =========================================================
// SOURCES
// =========================================================

function showSources(
    sources
) {

    if (
        !Array.isArray(sources) ||
        !sources.length
    ) {

        return;
    }

    currentSources =
        sources;

    const box =
        document.createElement(
            "div"
        );

    box.className =
        "sources-box";

    box.innerHTML = `

        <div class="sources-title">
            🌐 Sumber
        </div>

        <div class="sources-list">

            ${sources
                .slice(0, 5)
                .map(
                    (
                        source,
                        index
                    ) => `

                        <a
                            href="${escapeHtml(
                                source.url ||
                                "#"
                            )}"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="source-item"
                        >

                            ${index + 1}.
                            ${escapeHtml(
                                source.title ||
                                source.url ||
                                "Sumber"
                            )}

                        </a>
                    `
                )
                .join("")}

        </div>
    `;

    messages.appendChild(
        box
    );

    scrollBottom();
}


// =========================================================
// PLAN
// =========================================================

async function loadAccountPlan() {

    try {

        const response =
            await apiFetch(
                `${API}/api/account/plan`
            );

        if (!response.ok) {

            return;
        }

        const data =
            await response.json();

        currentPlan =
            data.plan ||
            "free";

        document.body.dataset.plan =
            currentPlan;

        console.log(
            "Winky Plan:",
            currentPlan
        );

    } catch (error) {

        console.error(
            "Plan error:",
            error
        );
    }
}
// =========================================================
// HISTORY
// =========================================================

async function loadConversations() {

    try {

        const response =
            await apiFetch(
                `${API}/api/conversations`
            );

        if (response.status === 401) {

            await logout();

            return;
        }

        if (!response.ok) {

            return;
        }

        const chats =
            await response.json();

        historyList.innerHTML =
            "";

        chats.forEach(
            chat => {

                const item =
                    document.createElement(
                        "div"
                    );

                item.className =
                    "chat-item";

                if (
                    String(chat.id) ===
                    String(
                        currentConversation
                    )
                ) {

                    item.classList.add(
                        "active"
                    );
                }

                const title =
                    document.createElement(
                        "span"
                    );

                title.textContent =
                    chat.title ||
                    "Chat Baru";

                const menu =
                    document.createElement(
                        "button"
                    );

                menu.className =
                    "chat-menu";

                menu.textContent =
                    "⋮";

                menu.onclick =
                    async event => {

                        event.stopPropagation();

                        const action =
                            prompt(
                                "1 = Rename\n2 = Hapus"
                            );

                        if (
                            action ===
                            "1"
                        ) {

                            const newTitle =
                                prompt(
                                    "Nama chat baru:",
                                    chat.title ||
                                    "Chat Baru"
                                );

                            if (!newTitle) {

                                return;
                            }

                            const response =
                                await apiFetch(
                                    `${API}/api/conversations/${chat.id}`,
                                    {

                                        method:
                                            "PATCH",

                                        body:
                                            JSON.stringify({
                                                title:
                                                    newTitle
                                            })
                                    }
                                );

                            if (!response.ok) {

                                alert(
                                    "Gagal mengganti nama chat."
                                );

                                return;
                            }

                            await loadConversations();
                        }

                        if (
                            action ===
                            "2"
                        ) {

                            if (
                                !confirm(
                                    "Hapus chat ini?"
                                )
                            ) {

                                return;
                            }

                            const response =
                                await apiFetch(
                                    `${API}/api/conversations/${chat.id}`,
                                    {

                                        method:
                                            "DELETE"
                                    }
                                );

                            if (!response.ok) {

                                alert(
                                    "Gagal menghapus chat."
                                );

                                return;
                            }

                            if (
                                String(
                                    currentConversation
                                ) ===
                                String(chat.id)
                            ) {

                                currentConversation =
                                    null;

                                showWelcome();
                            }

                            await loadConversations();
                        }
                    };

                item.onclick =
                    () =>
                        openConversation(
                            chat.id
                        );

                item.appendChild(
                    title
                );

                item.appendChild(
                    menu
                );

                historyList.appendChild(
                    item
                );
            }
        );

    } catch (error) {

        console.error(
            "History error:",
            error
        );
    }
}


// =========================================================
// OPEN CONVERSATION
// =========================================================

async function openConversation(
    id
) {

    if (isGenerating) {

        return;
    }

    try {

        const response =
            await apiFetch(
                `${API}/api/conversations/${id}`
            );

        if (
            response.status ===
            401
        ) {

            await logout();

            return;
        }

        if (!response.ok) {

            alert(
                "Gagal membuka percakapan."
            );

            return;
        }

        currentConversation =
            id;

        messages.innerHTML =
            "";

        currentSources =
            [];

        const chatMessages =
            await response.json();

        chatMessages.forEach(
            message => {

                addMessage(
                    message.content,
                    message.role ===
                        "assistant"
                        ? "ai"
                        : "user"
                );
            }
        );

        scrollBottom();

        await loadConversations();

    } catch (error) {

        console.error(
            "Open chat error:",
            error
        );
    }
}


// =========================================================
// NEW CHAT
// =========================================================

async function newChat() {

    if (isGenerating) {

        return;
    }

    try {

        const response =
            await apiFetch(
                `${API}/api/conversations`,
                {

                    method:
                        "POST"
                }
            );

        if (
            response.status ===
            401
        ) {

            await logout();

            return;
        }

        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );
        }

        const data =
            await response.json();

        currentConversation =
            data.conversation_id;

        selectedFileId =
            null;

        uploadedFileName =
            "";

        currentSources =
            [];

        fileStatus.textContent =
            "";

        showWelcome();

        await loadConversations();

        input.focus();

    } catch (error) {

        console.error(
            "New chat error:",
            error
        );
    }
}


// =========================================================
// SEND CHAT
// =========================================================

async function sendMessage() {

    if (isGenerating) {

        return;
    }

    let text =
        input.value.trim();

    if (!text) {

        return;
    }

    if (webSearchEnabled) {

        if (
            !/^Cari di web/i.test(
                text
            )
        ) {

            text =
                "Cari di web dan gunakan informasi terbaru.\n\n" +
                text;
        }
    }

    isGenerating =
        true;

    currentSources =
        [];

    abortController =
        new AbortController();

    sendButton.style.display =
        "none";

    stopButton.style.display =
        "block";

    setRobotState(
        "thinking"
    );

    try {

        if (!currentConversation) {

            const response =
                await apiFetch(
                    `${API}/api/conversations`,
                    {

                        method:
                            "POST"
                    }
                );

            if (!response.ok) {

                throw new Error(
                    `HTTP ${response.status}`
                );
            }

            const data =
                await response.json();

            currentConversation =
                data.conversation_id;
        }

        const displayText =
            selectedFileId
                ? `${text}\n\n📎 ${uploadedFileName}`
                : text;

        input.value =
            "";

        addMessage(
            displayText,
            "user"
        );

        const result =
            addMessage(
                "",
                "ai"
            );

        const bubble =
            result.bubble;

        bubble.classList.add(
            "loading"
        );

        let fullText =
            "";

        const selectedModel =
            modelSelect &&
            modelSelect.value
                ? modelSelect.value
                : null;

        const response =
            await apiFetch(
                `${API}/api/chat/stream`,
                {

                    method:
                        "POST",

                    body:
                        JSON.stringify({

                            conversation_id:
                                currentConversation,

                            message:
                                text,

                            model:
                                selectedModel,

                            file_id:
                                selectedFileId
                        }),

                    signal:
                        abortController.signal
                }
            );

        if (
            response.status ===
            401
        ) {

            await logout();

            return;
        }

        if (!response.ok) {

            let detail =
                `HTTP ${response.status}`;

            try {

                const errorData =
                    await response.json();

                detail =
                    errorData.detail ||
                    detail;

            } catch {}

            throw new Error(
                detail
            );
        }

        if (!response.body) {

            throw new Error(
                "Streaming tidak tersedia."
            );
        }

        const reader =
            response.body.getReader();

        const decoder =
            new TextDecoder(
                "utf-8"
            );

        let buffer =
            "";

        while (true) {

            const result =
                await reader.read();

            if (result.done) {

                break;
            }

            buffer +=
                decoder.decode(
                    result.value,
                    {
                        stream:
                            true
                    }
                );

            const lines =
                buffer.split("\n");

            buffer =
                lines.pop() ||
                "";

            for (
                const line
                of lines
            ) {

                if (!line.trim()) {

                    continue;
                }

                let data;

                try {

                    data =
                        JSON.parse(
                            line
                        );

                } catch {

                    continue;
                }


                // =========================================
                // ROUTER
                // =========================================

                if (data.router) {

                    showAIStatus(
                        data
                    );

                    setRobotState(
                        "thinking"
                    );
                }


                // =========================================
                // TOOL
                // =========================================

                if (data.tool) {

                    console.log(
                        "Winky Tool:",
                        data.tool
                    );

                    if (
                        data.tool ===
                        "web"
                    ) {

                        setRobotState(
                            "thinking",
                            "Mencari informasi terbaru..."
                        );

                    } else if (
                        data.tool ===
                        "deep_research"
                    ) {

                        setRobotState(
                            "thinking",
                            "Winky sedang melakukan riset..."
                        );

                    } else if (
                        data.tool ===
                        "calculator"
                    ) {

                        setRobotState(
                            "thinking",
                            "Menghitung..."
                        );

                    } else if (
                        data.tool ===
                        "offline"
                    ) {

                        setRobotState(
                            "thinking",
                            "Mode offline aktif..."
                        );
                    }
                }


                // =========================================
                // SOURCES
                // =========================================

                if (data.sources) {

                    showSources(
                        data.sources
                    );
                }


                // =========================================
                // PLAN
                // =========================================

                if (data.plan) {

                    currentPlan =
                        data.plan;

                    document.body.dataset.plan =
                        currentPlan;
                }


                // =========================================
                // CONVERSATION
                // =========================================

                if (
                    data.conversation_id
                ) {

                    currentConversation =
                        data.conversation_id;
                }


                // =========================================
                // CONTENT
                // =========================================

                if (data.content) {

                    fullText +=
                        data.content;

                    bubble.innerHTML =
                        renderMarkdown(
                            fullText
                        );

                    setRobotState(
                        "speaking"
                    );

                    scrollBottom();
                }


                // =========================================
                // ERROR
                // =========================================

                if (data.error) {

                    throw new Error(
                        data.error
                    );
                }
            }
        }


        // =============================================
        // FINISH
        // =============================================

        bubble.classList.remove(
            "loading"
        );

        bubble.innerHTML =
            renderMarkdown(
                fullText
            );

        setRobotState(
            "speaking"
        );

        if (
            fullText.trim()
        ) {

            speakAIResponse(
                fullText
            );
        }

        selectedFileId =
            null;

        uploadedFileName =
            "";

        fileStatus.textContent =
            "";

        fileInput.value =
            "";

        await loadConversations();


    } catch (error) {

        const aiBubbles =
            messages.querySelectorAll(
                ".message.ai .bubble"
            );

        const bubble =
            aiBubbles[
                aiBubbles.length - 1
            ];

        if (bubble) {

            bubble.classList.remove(
                "loading"
            );

            if (
                error.name ===
                "AbortError"
            ) {

                bubble.textContent =
                    "Jawaban dihentikan.";

            } else {

                bubble.innerHTML = `

                    <strong>
                        Winky Error
                    </strong>

                    <br>

                    ${escapeHtml(
                        error.message
                    )}

                `;
            }
        }

        console.error(
            "Chat error:",
            error
        );

        setRobotState(
            "idle"
        );

    } finally {

        isGenerating =
            false;

        abortController =
            null;

        stopButton.style.display =
            "none";

        sendButton.style.display =
            "block";

        setRobotState(
            "idle"
        );

        input.focus();
    }
}


// =========================================================
// STOP GENERATION
// =========================================================

function stopGeneration() {

    if (
        isGenerating &&
        abortController
    ) {

        abortController.abort();
    }

    stopWinkyVoice();

    setRobotState(
        "idle"
    );
}


// =========================================================
// FILE UPLOAD
// =========================================================

fileInput.addEventListener(
    "change",
    async () => {

        const file =
            fileInput.files[0];

        if (!file) {

            return;
        }

        fileStatus.textContent =
            "⏳ Mengunggah file...";

        try {

            const formData =
                new FormData();

            formData.append(
                "file",
                file
            );

            const response =
                await fetch(
                    `${API}/api/files/upload`,
                    {

                        method:
                            "POST",

                        headers: {

                            Authorization:
                                `Bearer ${token}`
                        },

                        body:
                            formData
                    }
                );

            const data =
                await response.json();

            if (!response.ok) {

                throw new Error(
                    data.detail ||
                    "Upload gagal."
                );
            }

            selectedFileId =
                data.file_id;

            uploadedFileName =
                data.filename;

            fileStatus.textContent =
                `📎 ${data.filename} siap digunakan`;

            input.value =
                `Analisis file "${data.filename}"`;

            await loadFiles();

            input.focus();

        } catch (error) {

            selectedFileId =
                null;

            uploadedFileName =
                "";

            fileStatus.textContent =
                "❌ Upload gagal.";

            alert(
                error.message
            );
        }
    }
);


// =========================================================
// FILE LIST
// =========================================================

filesButton.onclick =
    async () => {

        filesPanel.classList.remove(
            "hidden"
        );

        await loadFiles();
    };


async function loadFiles() {

    try {

        const response =
            await apiFetch(
                `${API}/api/files`
            );

        if (
            response.status ===
            401
        ) {

            await logout();

            return;
        }

        if (!response.ok) {

            return;
        }

        const files =
            await response.json();

        fileList.innerHTML =
            "";

        if (!files.length) {

            fileList.innerHTML =
                "<p>Belum ada file.</p>";

            return;
        }

        files.forEach(
            file => {

                const item =
                    document.createElement(
                        "div"
                    );

                item.className =
                    "file-item";

                const sizeKb =
                    Math.max(
                        1,
                        Math.round(
                            file.size /
                            1024
                        )
                    );

                item.innerHTML = `

                    <div>

                        <strong>
                            ${escapeHtml(
                                file.filename
                            )}
                        </strong>

                        <div>
                            ${sizeKb} KB
                        </div>

                    </div>

                    <div class="file-actions">

                        <button
                            class="use-file"
                        >
                            Pakai
                        </button>

                        <button
                            class="delete-file"
                        >
                            🗑
                        </button>

                    </div>

                `;

                item.querySelector(
                    ".use-file"
                ).onclick =
                    () => {

                        selectedFileId =
                            file.id;

                        uploadedFileName =
                            file.filename;

                        fileStatus.textContent =
                            `📎 ${file.filename} dipilih`;

                        filesPanel.classList.add(
                            "hidden"
                        );

                        input.value =
                            `Analisis file "${file.filename}"`;

                        input.focus();
                    };

                item.querySelector(
                    ".delete-file"
                ).onclick =
                    async () => {

                        if (
                            !confirm(
                                `Hapus ${file.filename}?`
                            )
                        ) {

                            return;
                        }

                        const response =
                            await apiFetch(
                                `${API}/api/files/${file.id}`,
                                {

                                    method:
                                        "DELETE"
                                }
                            );

                        if (!response.ok) {

                            alert(
                                "Gagal menghapus file."
                            );

                            return;
                        }

                        if (
                            selectedFileId ===
                            file.id
                        ) {

                            selectedFileId =
                                null;

                            uploadedFileName =
                                "";

                            fileStatus.textContent =
                                "";
                        }

                        await loadFiles();
                    };

                fileList.appendChild(
                    item
                );
            }
        );

    } catch (error) {

        console.error(
            "Files error:",
            error
        );
    }
}


// =========================================================
// WEB SEARCH
// =========================================================

webButton.onclick =
    () => {

        webSearchEnabled =
            !webSearchEnabled;

        webButton.classList.toggle(
            "active",
            webSearchEnabled
        );

        input.placeholder =
            webSearchEnabled
                ? "Web Search aktif..."
                : "Tanya Winky AI...";
    };
// =========================================================
// TEXT TO SPEECH
// =========================================================

function speakWinky(text) {

    if (
        !("speechSynthesis" in window)
    ) {

        return;
    }

    if (!text) {

        return;
    }

    window.speechSynthesis.cancel();

    const cleanText =
        String(text)
            .replace(
                /```[\s\S]*?```/g,
                ""
            )
            .replace(
                /[*_#]/g,
                ""
            )
            .replace(
                /\s+/g,
                " "
            )
            .trim();

    if (!cleanText) {

        return;
    }

    const utterance =
        new SpeechSynthesisUtterance(
            cleanText
        );

    utterance.lang =
        "id-ID";

    utterance.rate =
        0.96;

    utterance.pitch =
        1.03;

    utterance.volume =
        1;

    utterance.onstart =
        () => {

            setRobotState(
                "speaking"
            );
        };

    utterance.onend =
        () => {

            if (!isGenerating) {

                setRobotState(
                    "idle"
                );
            }
        };

    utterance.onerror =
        () => {

            if (!isGenerating) {

                setRobotState(
                    "idle"
                );
            }
        };

    window.speechSynthesis.speak(
        utterance
    );
}


function speakAIResponse(
    text
) {

    speakWinky(
        text
    );
}


function stopWinkyVoice() {

    if (
        "speechSynthesis" in window
    ) {

        window.speechSynthesis.cancel();
    }
}


// =========================================================
// SPEECH TO TEXT / LISTENING
// =========================================================

const SpeechRecognition =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition;


if (SpeechRecognition) {

    recognition =
        new SpeechRecognition();

    recognition.lang =
        "id-ID";

    recognition.continuous =
        false;

    recognition.interimResults =
        true;

    recognition.maxAlternatives =
        1;


    voiceButton.onclick =
        () => {

            if (isListening) {

                try {

                    recognition.stop();

                } catch {}

                return;
            }

            try {

                stopWinkyVoice();

                setRobotState(
                    "listening"
                );

                recognition.start();

            } catch (error) {

                console.error(
                    "Recognition start:",
                    error
                );
            }
        };


    recognition.onstart =
        () => {

            isListening =
                true;

            voiceButton.classList.add(
                "active"
            );

            voiceButton.textContent =
                "🔴";

            voiceButton.title =
                "Klik untuk berhenti";

            input.placeholder =
                "Winky sedang mendengarkan...";

            fileStatus.textContent =
                "🎤 Mendengarkan...";

            setRobotState(
                "listening"
            );
        };


    recognition.onresult =
        event => {

            let transcript =
                "";

            for (
                let i =
                    event.resultIndex;

                i <
                    event.results.length;

                i++
            ) {

                transcript +=
                    event
                        .results[i][0]
                        .transcript;
            }

            transcript =
                transcript.trim();

            if (transcript) {

                input.value =
                    transcript;

                input.focus();
            }
        };


    recognition.onerror =
        event => {

            console.error(
                "Voice error:",
                event.error
            );

            isListening =
                false;

            voiceButton.classList.remove(
                "active"
            );

            voiceButton.textContent =
                "🎤";

            voiceButton.title =
                "Voice";

            input.placeholder =
                "Tanya Winky AI...";

            fileStatus.textContent =
                "";

            setRobotState(
                "idle"
            );

            if (
                event.error ===
                "not-allowed"
            ) {

                alert(
                    "Izinkan akses mikrofon untuk menggunakan Voice Winky."
                );
            }

            if (
                event.error ===
                "no-speech"
            ) {

                fileStatus.textContent =
                    "🎤 Tidak ada suara terdeteksi.";
            }
        };


    recognition.onend =
        () => {

            const wasListening =
                isListening;

            isListening =
                false;

            voiceButton.classList.remove(
                "active"
            );

            voiceButton.textContent =
                "🎤";

            voiceButton.title =
                "Voice";

            input.placeholder =
                "Tanya Winky AI...";

            fileStatus.textContent =
                "";

            if (
                wasListening &&
                autoSendVoice &&
                input.value.trim() &&
                !isGenerating
            ) {

                sendMessage();

            } else if (
                !isGenerating
            ) {

                setRobotState(
                    "idle"
                );
            }
        };

} else {

    voiceButton.disabled =
        true;

    voiceButton.title =
        "Browser tidak mendukung Voice";
}


// =========================================================
// MEMORY
// =========================================================

memoryButton.onclick =
    async () => {

        memoryPanel.classList.remove(
            "hidden"
        );

        await loadMemories();
    };


async function loadMemories() {

    try {

        const response =
            await apiFetch(
                `${API}/api/memories`
            );

        if (
            response.status ===
            401
        ) {

            await logout();

            return;
        }

        if (!response.ok) {

            return;
        }

        const data =
            await response.json();

        memoryList.innerHTML =
            "";

        if (!Array.isArray(data) ||
            !data.length) {

            memoryList.innerHTML =
                "<p>Belum ada memory.</p>";

            return;
        }

        data.forEach(
            memory => {

                const item =
                    document.createElement(
                        "div"
                    );

                item.className =
                    "memory-item";

                item.innerHTML = `

                    <div>

                        <strong>
                            ${escapeHtml(
                                memory.key
                            )}
                        </strong>

                        <div>
                            ${escapeHtml(
                                memory.value
                            )}
                        </div>

                    </div>

                    <button>
                        🗑
                    </button>

                `;

                const deleteButton =
                    item.querySelector(
                        "button"
                    );

                deleteButton.onclick =
                    async () => {

                        if (
                            !confirm(
                                "Hapus memory ini?"
                            )
                        ) {

                            return;
                        }

                        const response =
                            await apiFetch(
                                `${API}/api/memories/${memory.id}`,
                                {

                                    method:
                                        "DELETE"
                                }
                            );

                        if (
                            !response.ok
                        ) {

                            alert(
                                "Gagal menghapus memory."
                            );

                            return;
                        }

                        await loadMemories();
                    };

                memoryList.appendChild(
                    item
                );
            }
        );

    } catch (error) {

        console.error(
            "Memory error:",
            error
        );
    }
}


saveMemoryButton.onclick =
    async () => {

        const key =
            memoryKey.value.trim();

        const value =
            memoryValue.value.trim();

        if (
            !key ||
            !value
        ) {

            return;
        }

        try {

            const response =
                await apiFetch(
                    `${API}/api/memories`,
                    {

                        method:
                            "POST",

                        body:
                            JSON.stringify({
                                key,
                                value
                            })
                    }
                );

            if (!response.ok) {

                let detail =
                    "Gagal menyimpan memory.";

                try {

                    const data =
                        await response.json();

                    detail =
                        data.detail ||
                        detail;

                } catch {}

                alert(
                    detail
                );

                return;
            }

            memoryKey.value =
                "";

            memoryValue.value =
                "";

            await loadMemories();

        } catch (error) {

            console.error(
                "Save memory error:",
                error
            );

            alert(
                error.message
            );
        }
    };


closeMemory.onclick =
    () => {

        memoryPanel.classList.add(
            "hidden"
        );
    };


// =========================================================
// SETTINGS
// =========================================================

settingsButton.onclick =
    async () => {

        settingsPanel.classList.remove(
            "hidden"
        );

        await loadModels();

        await checkHealth();

        await loadAccountPlan();
    };


closeSettings.onclick =
    () => {

        settingsPanel.classList.add(
            "hidden"
        );
    };


// =========================================================
// MODELS
// =========================================================

async function loadModels() {

    try {

        const response =
            await apiFetch(
                `${API}/api/models`
            );

        if (
            response.status ===
            401
        ) {

            await logout();

            return;
        }

        if (!response.ok) {

            return;
        }

        const data =
            await response.json();

        modelSelect.innerHTML =
            "";

        const models =
            Array.isArray(
                data.models
            )
                ? data.models
                : [];

        const savedModel =
            localStorage.getItem(
                "winky_model"
            );

        models.forEach(
            model => {

                const option =
                    document.createElement(
                        "option"
                    );

                option.value =
                    model;

                option.textContent =
                    model;

                modelSelect.appendChild(
                    option
                );
            }
        );

        if (
            savedModel &&
            models.includes(
                savedModel
            )
        ) {

            modelSelect.value =
                savedModel;

        } else if (
            models.includes(
                "qwen3:0.6b"
            )
        ) {

            modelSelect.value =
                "qwen3:0.6b";

        } else if (
            models.length
        ) {

            modelSelect.value =
                models[0];
        }

        if (
            modelSelect.value
        ) {

            localStorage.setItem(
                "winky_model",
                modelSelect.value
            );
        }

    } catch (error) {

        console.error(
            "Models error:",
            error
        );
    }
}


modelSelect.addEventListener(
    "change",
    () => {

        if (!modelSelect.value) {

            return;
        }

        localStorage.setItem(
            "winky_model",
            modelSelect.value
        );
    }
);


// =========================================================
// HEALTH
// =========================================================

async function checkHealth() {

    try {

        const response =
            await fetch(
                `${API}/api/health`
            );

        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );
        }

        const data =
            await response.json();

        backendStatus.textContent =
            data.backend
                ? "● Online"
                : "● Offline";

        ollamaStatus.textContent =
            data.ollama
                ? "● Online"
                : "● Offline";

    } catch {

        backendStatus.textContent =
            "● Offline";

        ollamaStatus.textContent =
            "● Offline";
    }
}


// =========================================================
// ACCOUNT PLAN
// =========================================================

async function refreshPlan() {

    await loadAccountPlan();

    document.body.dataset.plan =
        currentPlan;
}


// =========================================================
// EXPORT
// =========================================================

exportButton.onclick =
    async () => {

        if (!currentConversation) {

            alert(
                "Belum ada chat."
            );

            return;
        }

        try {

            const response =
                await apiFetch(
                    `${API}/api/conversations/${currentConversation}`
                );

            if (!response.ok) {

                throw new Error(
                    "Gagal mengambil chat."
                );
            }

            const data =
                await response.json();

            const text =
                data
                    .map(
                        item => {

                            const role =
                                item.role ===
                                    "user"
                                    ? "USER"
                                    : "WINKY AI";

                            return (
                                role +
                                ":\n" +
                                item.content +
                                "\n"
                            );
                        }
                    )
                    .join(
                        "\n"
                    );

            const blob =
                new Blob(
                    [text],
                    {

                        type:
                            "text/plain;charset=utf-8"
                    }
                );

            const url =
                URL.createObjectURL(
                    blob
                );

            const link =
                document.createElement(
                    "a"
                );

            link.href =
                url;

            link.download =
                `winky-chat-${Date.now()}.txt`;

            document.body.appendChild(
                link
            );

            link.click();

            link.remove();

            URL.revokeObjectURL(
                url
            );

        } catch (error) {

            alert(
                error.message
            );
        }
    };


// =========================================================
// COPY CODE
// =========================================================

document.addEventListener(
    "click",
    async event => {

        const button =
            event.target.closest(
                ".copy-code"
            );

        if (!button) {

            return;
        }

        const code =
            decodeURIComponent(
                button.dataset.code ||
                ""
            );

        try {

            await navigator
                .clipboard
                .writeText(
                    code
                );

            button.textContent =
                "Copied";

            setTimeout(
                () => {

                    button.textContent =
                        "Copy";

                },
                1200
            );

        } catch (error) {

            console.error(
                "Copy error:",
                error
            );
        }
    }
);


// =========================================================
// CLOSE PANELS
// =========================================================

closeFiles.onclick =
    () => {

        filesPanel.classList.add(
            "hidden"
        );
    };


document.addEventListener(
    "keydown",
    event => {

        if (
            event.key !==
            "Escape"
        ) {

            return;
        }

        memoryPanel.classList.add(
            "hidden"
        );

        filesPanel.classList.add(
            "hidden"
        );

        settingsPanel.classList.add(
            "hidden"
        );

        stopWinkyVoice();

        if (!isGenerating) {

            setRobotState(
                "idle"
            );
        }
    }
);


// =========================================================
// GLOBAL EVENTS
// =========================================================

loginButton.onclick =
    login;

registerButton.onclick =
    register;

logoutButton.onclick =
    logout;

newChatButton.onclick =
    newChat;

sendButton.onclick =
    sendMessage;

stopButton.onclick =
    stopGeneration;


// =========================================================
// ENTER TO SEND
// =========================================================

input.addEventListener(
    "keydown",
    event => {

        if (
            event.key ===
                "Enter" &&
            !event.shiftKey
        ) {

            event.preventDefault();

            sendMessage();
        }
    }
);


// =========================================================
// START APP
// =========================================================

async function startApp() {

    showWelcome();

    usernameDisplay.textContent =
        username;

    await loadAccountPlan();

    await loadModels();

    await loadConversations();

    await loadFiles();

    await checkHealth();

    input.focus();
}


// =========================================================
// INITIALIZE
// =========================================================

async function initialize() {

    if (!token) {

        showAuth();

        return;
    }

    try {

        const response =
            await apiFetch(
                `${API}/api/auth/me`
            );

        if (!response.ok) {

            throw new Error();
        }

        const data =
            await response.json();

        username =
            data.username;

        currentPlan =
            data.plan ||
            "free";

        document.body.dataset.plan =
            currentPlan;

        localStorage.setItem(
            "winky_username",
            username
        );

        showApp();

        await startApp();

    } catch {

        token =
            "";

        currentPlan =
            "free";

        localStorage.removeItem(
            "winky_token"
        );

        showAuth();
    }
}


// =========================================================
// START
// =========================================================

initialize();