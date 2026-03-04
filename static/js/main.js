/**
 * AI Humanizer — Frontend Logic
 */

document.addEventListener("DOMContentLoaded", () => {
    // ---- Elements ----
    const inputText = document.getElementById("inputText");
    const outputText = document.getElementById("outputText");
    const humanizeBtn = document.getElementById("humanizeBtn");
    const clearBtn = document.getElementById("clearBtn");
    const pasteBtn = document.getElementById("pasteBtn");
    const copyBtn = document.getElementById("copyBtn");
    const modelSelect = document.getElementById("modelSelect");
    const statusIndicator = document.getElementById("statusIndicator");
    const intensitySlider = document.getElementById("intensitySlider");
    const intensityValue = document.getElementById("intensityValue");
    const inputCharCount = document.getElementById("inputCharCount");
    const outputCharCount = document.getElementById("outputCharCount");
    const statsBar = document.getElementById("statsBar");
    const loadingOverlay = document.getElementById("loadingOverlay");
    const toneButtons = document.querySelectorAll(".tone-btn");

    let currentTone = "normal";
    let isProcessing = false;

    // ---- Initialize ----
    checkStatus();
    loadModels();

    // ---- Event Listeners ----
    inputText.addEventListener("input", onInputChange);
    humanizeBtn.addEventListener("click", humanize);
    clearBtn.addEventListener("click", clearInput);
    pasteBtn.addEventListener("click", pasteFromClipboard);
    copyBtn.addEventListener("click", copyOutput);
    modelSelect.addEventListener("change", switchModel);
    intensitySlider.addEventListener("input", updateIntensityLabel);

    toneButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            toneButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentTone = btn.dataset.tone;
        });
    });

    // Keyboard shortcut: Ctrl+Enter to humanize
    document.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
            e.preventDefault();
            if (!isProcessing && inputText.value.trim()) {
                humanize();
            }
        }
    });

    // ---- Functions ----

    function onInputChange() {
        const len = inputText.value.length;
        inputCharCount.textContent = `${len.toLocaleString()} chars`;
        humanizeBtn.disabled = len < 20;
    }

    function updateIntensityLabel() {
        intensityValue.textContent = `${intensitySlider.value}%`;
    }

    async function checkStatus() {
        const dot = statusIndicator.querySelector(".status-dot");
        const text = statusIndicator.querySelector(".status-text");

        dot.className = "status-dot loading";
        text.textContent = "Checking...";

        try {
            const resp = await fetch("/api/status");
            const data = await resp.json();

            if (data.status === "ready") {
                dot.className = "status-dot ready";
                text.textContent = "Ready";
            } else {
                dot.className = "status-dot error";
                text.textContent = "Not ready";
                showToast(data.message, "error");
            }
        } catch (err) {
            dot.className = "status-dot error";
            text.textContent = "Offline";
            showToast("Cannot connect to server.", "error");
        }
    }

    async function loadModels() {
        try {
            const resp = await fetch("/api/models");
            const data = await resp.json();

            modelSelect.innerHTML = "";

            if (data.models.length === 0) {
                const opt = document.createElement("option");
                opt.value = "";
                opt.textContent = "No models found";
                modelSelect.appendChild(opt);
                return;
            }

            data.models.forEach(model => {
                const opt = document.createElement("option");
                opt.value = model;
                opt.textContent = model;
                if (model === data.current || model.startsWith(data.current)) {
                    opt.selected = true;
                }
                modelSelect.appendChild(opt);
            });
        } catch (err) {
            modelSelect.innerHTML = '<option value="">Error loading</option>';
        }
    }

    async function switchModel() {
        const model = modelSelect.value;
        if (!model) return;

        try {
            const resp = await fetch("/api/model", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ model }),
            });
            const data = await resp.json();
            showToast(data.message || `Switched to ${model}`, "success");
        } catch (err) {
            showToast("Failed to switch model.", "error");
        }
    }

    async function humanize() {
        const text = inputText.value.trim();
        if (!text || isProcessing) return;

        isProcessing = true;
        humanizeBtn.classList.add("processing");
        humanizeBtn.disabled = true;
        loadingOverlay.style.display = "flex";
        outputText.innerHTML = '<div class="placeholder-text">Generating...</div>';

        const intensity = parseInt(intensitySlider.value) / 100;

        try {
            const resp = await fetch("/api/humanize", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    text: text,
                    tone: currentTone,
                    intensity: intensity,
                }),
            });

            const data = await resp.json();

            if (data.error) {
                outputText.innerHTML = `<div class="placeholder-text" style="color: var(--error);">${escapeHtml(data.error)}</div>`;
                showToast(data.error, "error");
            } else {
                outputText.textContent = data.result;
                copyBtn.disabled = false;

                // Update stats
                statsBar.style.display = "flex";
                document.getElementById("statTime").textContent = `${data.time_taken}s`;
                document.getElementById("statModel").textContent = data.model;
                document.getElementById("statTone").textContent = capitalize(data.tone);
                document.getElementById("statOrigLen").textContent = `${data.original_length.toLocaleString()} chars`;
                document.getElementById("statNewLen").textContent = `${data.new_length.toLocaleString()} chars`;

                outputCharCount.textContent = `${data.new_length.toLocaleString()} chars`;
            }
        } catch (err) {
            outputText.innerHTML = `<div class="placeholder-text" style="color: var(--error);">Request failed. Is the server running?</div>`;
            showToast("Request failed. Check the server.", "error");
        } finally {
            isProcessing = false;
            humanizeBtn.classList.remove("processing");
            humanizeBtn.disabled = inputText.value.trim().length < 20;
            loadingOverlay.style.display = "none";
        }
    }

    function clearInput() {
        inputText.value = "";
        outputText.innerHTML = '<div class="placeholder-text">Humanized text will appear here...</div>';
        copyBtn.disabled = true;
        humanizeBtn.disabled = true;
        inputCharCount.textContent = "0 chars";
        outputCharCount.textContent = "0 chars";
        statsBar.style.display = "none";
        inputText.focus();
    }

    async function pasteFromClipboard() {
        try {
            const text = await navigator.clipboard.readText();
            inputText.value = text;
            onInputChange();
            inputText.focus();
            showToast("Pasted from clipboard", "success");
        } catch (err) {
            showToast("Clipboard access denied. Paste manually with Ctrl+V.", "error");
        }
    }

    async function copyOutput() {
        const text = outputText.textContent;
        if (!text) return;

        try {
            await navigator.clipboard.writeText(text);
            copyBtn.textContent = "✓";
            outputText.classList.add("copy-flash");
            showToast("Copied to clipboard!", "success");
            setTimeout(() => {
                copyBtn.textContent = "📄";
                outputText.classList.remove("copy-flash");
            }, 1500);
        } catch (err) {
            showToast("Copy failed.", "error");
        }
    }

    // ---- Utility ----

    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = "toastOut 0.3s ease forwards";
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    function capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
});
