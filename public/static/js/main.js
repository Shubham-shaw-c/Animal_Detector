/**
 * main.js
 * Animal AI Dashboard & Chatbot Client Controller.
 * Handles drag-and-drop, image preview & prediction, 10 scientific facts rendering,
 * conversational follow-up questions, and real-time autonomous model retraining.
 */

document.addEventListener("DOMContentLoaded", () => {
    // State
    let currentDetectedAnimal = null;
    let stagedFile = null;
    let isAnalyzing = false;
    let downloadPollInterval = null;
    let trainingPollInterval = null;

    // DOM Elements - Header & Popover
    const classesCountBadge = document.getElementById("classesCountBadge");
    const classesCountText = document.getElementById("classesCountText");
    const speciesPopover = document.getElementById("speciesPopover");
    const speciesTagsGrid = document.getElementById("speciesTagsGrid");
    const closeSpeciesPopover = document.getElementById("closeSpeciesPopover");
    const clearChatBtn = document.getElementById("clearChatBtn");
    const resetChatHeaderBtn = document.getElementById("resetChatHeaderBtn");

    // DOM Elements - Chatbot
    const chatbotContainer = document.getElementById("chatbotContainer");
    const chatMessages = document.getElementById("chatMessages");
    const dragDropOverlay = document.getElementById("dragDropOverlay");
    const fileInput = document.getElementById("fileInput");
    const uploadTriggerBtn = document.getElementById("uploadTriggerBtn");
    const chatTextInput = document.getElementById("chatTextInput");
    const sendMessageBtn = document.getElementById("sendMessageBtn");

    // DOM Elements - Staged Upload Bar
    const stagedUploadBar = document.getElementById("stagedUploadBar");
    const stagedImagePreview = document.getElementById("stagedImagePreview");
    const removeStagedImageBtn = document.getElementById("removeStagedImageBtn");
    const stagedFileName = document.getElementById("stagedFileName");
    const stagedFileSize = document.getElementById("stagedFileSize");
    const analyzeStagedBtn = document.getElementById("analyzeStagedBtn");

    // DOM Elements - Add Animal Modal
    const openAddModalBtn = document.getElementById("openAddModalBtn");
    const addAnimalModal = document.getElementById("addAnimalModal");
    const closeAddModalBtn = document.getElementById("closeAddModalBtn");
    const cancelAddBtn = document.getElementById("cancelAddBtn");
    const modalFormView = document.getElementById("modalFormView");
    const modalProgressView = document.getElementById("modalProgressView");
    const newAnimalInput = document.getElementById("newAnimalInput");
    const submitAddAnimalBtn = document.getElementById("submitAddAnimalBtn");
    const exampleChips = document.querySelectorAll(".example-chip");

    // DOM Elements - Pipeline Progress
    const pipelineStatusMsg = document.getElementById("pipelineStatusMsg");
    const pipelinePercentVal = document.getElementById("pipelinePercentVal");
    const pipelineProgressBar = document.getElementById("pipelineProgressBar");
    const metricAnimalName = document.getElementById("metricAnimalName");
    const metricImagesCount = document.getElementById("metricImagesCount");
    const metricTrainAcc = document.getElementById("metricTrainAcc");
    const metricValAcc = document.getElementById("metricValAcc");
    const pipelineLogTerminal = document.getElementById("pipelineLogTerminal");
    const successConfirmationBanner = document.getElementById("successConfirmationBanner");
    const confDetailsText = document.getElementById("confDetailsText");
    const finishPipelineBtn = document.getElementById("finishPipelineBtn");

    // Stepper elements
    const step1 = document.getElementById("step1");
    const step2 = document.getElementById("step2");
    const step3 = document.getElementById("step3");
    const step4 = document.getElementById("step4");
    const step5 = document.getElementById("step5");
    const conn1 = document.getElementById("conn1");
    const conn2 = document.getElementById("conn2");
    const conn3 = document.getElementById("conn3");
    const conn4 = document.getElementById("conn4");

    // Toast Container
    const toastContainer = document.getElementById("toastContainer");

    // ==========================================
    // INITIALIZATION & METRICS
    // ==========================================
    fetchSupportedAnimals();

    function fetchSupportedAnimals() {
        fetch("/api/animals")
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    const count = data.total_classes;
                    classesCountText.textContent = `${count} Supported Species`;
                    renderSpeciesPills(data.classes);
                }
            })
            .catch(err => {
                console.error("Failed fetching supported animals:", err);
            });
    }

    function renderSpeciesPills(classes) {
        speciesTagsGrid.innerHTML = "";
        classes.forEach(c => {
            const pill = document.createElement("div");
            pill.className = "species-pill";
            pill.innerHTML = `<i class="fa-solid fa-paw"></i> ${c}`;
            speciesTagsGrid.appendChild(pill);
        });
    }

    // Toggle Species Popover
    classesCountBadge.addEventListener("click", () => {
        speciesPopover.classList.toggle("active");
    });

    closeSpeciesPopover.addEventListener("click", () => {
        speciesPopover.classList.remove("active");
    });

    document.addEventListener("click", (e) => {
        if (!classesCountBadge.contains(e.target) && !speciesPopover.contains(e.target)) {
            speciesPopover.classList.remove("active");
        }
    });

    // ==========================================
    // DRAG & DROP & FILE SELECTION
    // ==========================================
    uploadTriggerBtn.addEventListener("click", (e) => {
        e.preventDefault();
        fileInput.value = "";
        fileInput.click();
    });

    fileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files[0]) {
            handleSelectedFile(e.target.files[0]);
        }
    });

    // Drag-over container
    ["dragenter", "dragover"].forEach(eventName => {
        chatbotContainer.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dragDropOverlay.classList.add("active");
        });
    });

    ["dragleave", "drop"].forEach(eventName => {
        dragDropOverlay.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (eventName === "drop") {
                const dt = e.dataTransfer;
                const files = dt.files;
                if (files && files[0]) {
                    handleSelectedFile(files[0]);
                }
            }
            dragDropOverlay.classList.remove("active");
        });
    });

    // Clipboard paste support (Ctrl+V anywhere)
    window.addEventListener("paste", (e) => {
        if (e.clipboardData && e.clipboardData.items) {
            for (let i = 0; i < e.clipboardData.items.length; i++) {
                const item = e.clipboardData.items[i];
                if (item.type && item.type.startsWith("image/")) {
                    const blob = item.getAsFile();
                    if (blob) {
                        handleSelectedFile(blob);
                        showToast("Image pasted from clipboard!", "info");
                        break;
                    }
                }
            }
        }
    });

    function handleSelectedFile(file) {
        if (!file || !file.type || !file.type.startsWith("image/")) {
            showToast("Please select a valid image file (JPG, PNG, WEBP).", "error");
            return;
        }
        triggerAnalysis(file);
    }

    // Quick Demo Sample Chips click handler
    chatMessages.addEventListener("click", (e) => {
        const chip = e.target.closest(".sample-test-chip");
        if (chip) {
            const animal = chip.getAttribute("data-animal");
            if (animal) {
                showToast(`Fetching ${animal.toUpperCase()} sample photo...`, "info");
                fetch(`/api/sample/${animal}`)
                    .then(res => {
                        if (!res.ok) throw new Error("Sample not found");
                        return res.blob();
                    })
                    .then(blob => {
                        const file = new File([blob], `${animal}_sample.jpg`, { type: "image/jpeg" });
                        handleSelectedFile(file);
                    })
                    .catch(err => {
                        showToast(`Could not load ${animal} sample: ${err.message}`, "error");
                    });
            }
        }
    });

    function clearStagedImage() {
        stagedFile = null;
        if (fileInput) fileInput.value = "";
        if (stagedUploadBar) stagedUploadBar.classList.add("hidden");
        if (stagedImagePreview) stagedImagePreview.src = "";
    }

    if (removeStagedImageBtn) {
        removeStagedImageBtn.addEventListener("click", clearStagedImage);
    }

    if (analyzeStagedBtn) {
        analyzeStagedBtn.addEventListener("click", () => {
            if (stagedFile && !isAnalyzing) {
                triggerAnalysis(stagedFile);
            }
        });
    }

    // ==========================================
    // PREDICTION WORKFLOW (POST /api/predict)
    // ==========================================
    function triggerAnalysis(file) {
        if (isAnalyzing) return;
        isAnalyzing = true;

        // 1. Append User Message (clean text notification)
        appendUserMessage(`Analyzing animal photo: <strong>${file.name}</strong>`);
        clearStagedImage();

        // 2. Append AI Typing / Inference Indicator
        const loadingRow = appendLoadingIndicator("Analyzing image with deep learning neural network...");

        // 3. Send to /api/predict
        const formData = new FormData();
        formData.append("image", file);

        fetch("/api/predict", {
            method: "POST",
            body: formData
        })
            .then(res => res.json())
            .then(data => {
                loadingRow.remove();
                isAnalyzing = false;

                if (!data.success) {
                    appendAIMessage(`<div style="color:#f87171;"><i class="fa-solid fa-triangle-exclamation"></i> ${data.error || "Prediction failed."}</div>`);
                    return;
                }

                currentDetectedAnimal = data.detected_animal;
                renderDetectionResultCard(data);
            })
            .catch(err => {
                loadingRow.remove();
                isAnalyzing = false;
                appendAIMessage(`<div style="color:#f87171;"><i class="fa-solid fa-triangle-exclamation"></i> Network error: ${err.message}</div>`);
            });
    }

    function renderDetectionResultCard(result) {
        const animal = result.detected_animal;
        const confidence = result.confidence;
        const top3 = result.top_predictions || [];
        const facts = result.facts || [];

        // Confidence badge class
        let confClass = "high";
        if (confidence < 70) confClass = "medium";
        if (confidence < 45) confClass = "low";

        // Build top 3 HTML
        let top3Html = "";
        top3.forEach(item => {
            top3Html += `
                <div class="top3-row">
                    <span class="top3-name">${item.animal}</span>
                    <div class="top3-bar-track">
                        <div class="top3-bar-fill" style="width: ${item.confidence}%"></div>
                    </div>
                    <span class="top3-percent">${item.confidence.toFixed(1)}%</span>
                </div>
            `;
        });

        // Build 10 Facts HTML
        let factsHtml = "";
        facts.forEach(f => {
            factsHtml += `
                <div class="fact-card">
                    <div class="fact-card-header">
                        <span class="fact-number-pill">${f.id}</span>
                        <span class="fact-card-title">${f.icon} ${f.category}</span>
                    </div>
                    <div class="fact-card-body">${f.content}</div>
                </div>
            `;
        });

        const cardContent = `
            <div class="detection-result-card">
                <div class="detection-header-banner">
                    <div class="detection-title-group">
                        <h3><i class="fa-solid fa-check-circle" style="color:#10b981;"></i> Detected: ${animal}</h3>
                        <p>Classified using deep learning transfer model</p>
                    </div>
                    <div class="confidence-badge ${confClass}">
                        <i class="fa-solid fa-bullseye"></i>
                        <span>${confidence.toFixed(2)}% Confidence</span>
                    </div>
                </div>

                <div class="top3-breakdown-wrapper">
                    <div class="top3-title"><i class="fa-solid fa-chart-simple"></i> Confidence Ranking</div>
                    ${top3Html}
                </div>

                <div class="facts-section-header">
                    <i class="fa-solid fa-book-open"></i>
                    <span>10 Important Facts About ${animal}</span>
                </div>

                <div class="facts-grid">
                    ${factsHtml}
                </div>

                <div class="quick-queries-bar">
                    <span style="font-size:0.75rem; color:var(--text-muted); align-self:center;">Explore more:</span>
                    <button class="quick-chip" data-q="Where does this animal live?">🏞️ Natural Habitat</button>
                    <button class="quick-chip" data-q="What does this animal eat?">🥩 Diet & Food</button>
                    <button class="quick-chip" data-q="What is its lifespan?">⏳ Lifespan</button>
                    <button class="quick-chip" data-q="Is this animal endangered?">🛡️ Conservation Status</button>
                    <button class="quick-chip" data-q="Tell me more about its behaviour.">👥 Social Behaviour</button>
                </div>
            </div>
        `;

        appendAIMessage(cardContent);

        // Bind quick query chips
        const chips = chatMessages.querySelectorAll(".quick-chip");
        chips.forEach(chip => {
            chip.addEventListener("click", () => {
                const query = chip.getAttribute("data-q");
                handleUserQuestion(query);
            });
        });
    }

    // ==========================================
    // FOLLOW-UP CONVERSATION (POST /api/chat)
    // ==========================================
    sendMessageBtn.addEventListener("click", () => {
        submitUserChatMessage();
    });

    chatTextInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            if (stagedFile && !isAnalyzing) {
                triggerAnalysis(stagedFile);
            } else {
                submitUserChatMessage();
            }
        }
    });

    function submitUserChatMessage() {
        const text = chatTextInput.value.trim();
        if (!text) return;
        chatTextInput.value = "";
        handleUserQuestion(text);
    }

    function handleUserQuestion(questionText) {
        appendUserMessage(questionText);

        const loadingRow = appendLoadingIndicator("Thinking...");

        fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: questionText,
                animal: currentDetectedAnimal || ""
            })
        })
            .then(res => res.json())
            .then(data => {
                loadingRow.remove();
                if (data.success) {
                    appendAIMessage(formatMarkdown(data.reply));
                } else {
                    appendAIMessage(`<div>${data.error || "Unable to retrieve answer."}</div>`);
                }
            })
            .catch(err => {
                loadingRow.remove();
                appendAIMessage(`<div style="color:#f87171;">Connection error: ${err.message}</div>`);
            });
    }

    // Helper: basic markdown to HTML converter for bullet points & bold
    function formatMarkdown(text) {
        if (!text) return "";
        let formatted = text
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.*?)\*/g, "<em>$1</em>")
            .replace(/\n\n/g, "<br><br>")
            .replace(/\n• /g, "<br>• ");
        return formatted;
    }

    // ==========================================
    // CHAT MESSAGE UI HELPERS
    // ==========================================
    function appendUserMessage(text, imageSrc = null) {
        const row = document.createElement("div");
        row.className = "message-row user-row";

        let imgHtml = "";
        if (imageSrc) {
            imgHtml = `<img src="${imageSrc}" class="user-image-thumb" alt="Uploaded Animal">`;
        }

        row.innerHTML = `
            <div class="message-avatar user-avatar"><i class="fa-solid fa-user"></i></div>
            <div class="message-bubble user-bubble">
                ${imgHtml}
                <div>${text}</div>
            </div>
        `;
        chatMessages.appendChild(row);
        scrollToBottom();
    }

    function appendAIMessage(contentHtml) {
        const row = document.createElement("div");
        row.className = "message-row ai-row";
        row.innerHTML = `
            <div class="message-avatar ai-avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="message-bubble ai-bubble">
                ${contentHtml}
            </div>
        `;
        chatMessages.appendChild(row);
        scrollToBottom();
    }

    function appendLoadingIndicator(label = "Processing...") {
        const row = document.createElement("div");
        row.className = "message-row ai-row loading-row";
        row.innerHTML = `
            <div class="message-avatar ai-avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="message-bubble ai-bubble">
                <div class="typing-indicator-row">
                    <span style="font-size:0.85rem; color:var(--text-muted); margin-right:8px;">${label}</span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                </div>
            </div>
        `;
        chatMessages.appendChild(row);
        scrollToBottom();
        return row;
    }

    function scrollToBottom() {
        setTimeout(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }, 50);
    }

    // Reset Chat
    clearChatBtn.addEventListener("click", resetConversation);
    resetChatHeaderBtn.addEventListener("click", resetConversation);

    function resetConversation() {
        currentDetectedAnimal = null;
        clearStagedImage();
        chatMessages.innerHTML = `
            <div class="message-row ai-row">
                <div class="message-avatar ai-avatar"><i class="fa-solid fa-robot"></i></div>
                <div class="message-bubble ai-bubble welcome-card">
                    <div class="welcome-badge">
                        <i class="fa-solid fa-wand-magic-sparkles"></i> Deep Learning Zoo Assistant
                    </div>
                    <h2>Welcome to Animal AI</h2>
                    <p class="welcome-intro">
                        Upload or drag & drop any animal photograph. Our AI will classify the species with high precision and present <strong>10 verified scientific facts</strong> covering its taxonomy, habitat, diet, lifespan, and conservation status.
                    </p>
                    <div class="quick-samples-bar" style="margin-top: 14px; padding-top: 14px; border-top: 1px solid rgba(52, 211, 153, 0.25);">
                        <span style="font-size: 0.8rem; font-weight: 700; color: #a7f3d0; margin-right: 8px; display: inline-flex; align-items: center; gap: 6px;">
                            <i class="fa-solid fa-flask"></i> Quick Demo Test:
                        </span>
                        <button class="sample-test-chip" data-animal="tiger">🐯 Tiger</button>
                        <button class="sample-test-chip" data-animal="elephant">🐘 Elephant</button>
                        <button class="sample-test-chip" data-animal="panda">🐼 Panda</button>
                        <button class="sample-test-chip" data-animal="penguin">🐧 Penguin</button>
                        <button class="sample-test-chip" data-animal="zebra">🦓 Zebra</button>
                    </div>
                </div>
            </div>
        `;
        showToast("Conversation cleared.", "info");
    }

    // ==========================================
    // ADD NEW ANIMAL WORKFLOW & MODAL
    // ==========================================
    openAddModalBtn.addEventListener("click", () => {
        openModal();
    });

    closeAddModalBtn.addEventListener("click", () => {
        closeModal();
    });

    cancelAddBtn.addEventListener("click", () => {
        closeModal();
    });

    function openModal() {
        addAnimalModal.classList.remove("hidden");
        modalFormView.classList.remove("hidden");
        modalProgressView.classList.add("hidden");
        successConfirmationBanner.classList.add("hidden");
        newAnimalInput.value = "";
        resetStepper();
    }

    function closeModal() {
        addAnimalModal.classList.add("hidden");
        clearInterval(downloadPollInterval);
        clearInterval(trainingPollInterval);
    }

    // Example chips click
    exampleChips.forEach(chip => {
        chip.addEventListener("click", () => {
            newAnimalInput.value = chip.getAttribute("data-name");
            newAnimalInput.focus();
        });
    });

    submitAddAnimalBtn.addEventListener("click", () => {
        const rawName = newAnimalInput.value.trim();
        if (!rawName) {
            showToast("Please enter an animal name.", "error");
            newAnimalInput.focus();
            newAnimalInput.classList.add("input-error");
            setTimeout(() => newAnimalInput.classList.remove("input-error"), 1500);
            return;
        }

        const originalBtnHTML = submitAddAnimalBtn.innerHTML;
        submitAddAnimalBtn.disabled = true;
        submitAddAnimalBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Verifying Animal...</span>';

        // Call /api/add-animal to strictly validate the animal species before proceeding
        fetch("/api/add-animal", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: rawName, limit: 100 })
        })
            .then(res => res.json())
            .then(data => {
                submitAddAnimalBtn.disabled = false;
                submitAddAnimalBtn.innerHTML = originalBtnHTML;

                if (!data.success) {
                    // STOP IMMEDIATELY: Do not switch views, do not download, do not create folders
                    showToast(data.error, "error");
                    newAnimalInput.focus();
                    newAnimalInput.classList.add("input-error");
                    setTimeout(() => newAnimalInput.classList.remove("input-error"), 2500);
                    return;
                }

                // ONLY VALID ANIMALS PROCEED HERE:
                // Switch to progress view
                modalFormView.classList.add("hidden");
                modalProgressView.classList.remove("hidden");
                metricAnimalName.textContent = data.display_name || rawName;

                logToTerminal(`[System] Genuine animal species "${data.display_name}" verified!`, "text-success");
                logToTerminal(`[System] Initializing autonomous learning pipeline...`, "text-info");

                // Step 1: Complete, Step 2: Active
                setStepState(step1, "completed");
                setStepConnector(conn1, true);
                setStepState(step2, "active");

                pipelineStatusMsg.textContent = `Gathering candidate images for "${data.display_name}"...`;
                pipelineProgressBar.style.width = "15%";
                pipelinePercentVal.textContent = "15%";

                logToTerminal(`[Download] Scraping high-resolution photos for ${data.display_name}...`, "text-info");

                // Start Polling Download Progress
                startDownloadPolling(data.animal);
            })
            .catch(err => {
                submitAddAnimalBtn.disabled = false;
                submitAddAnimalBtn.innerHTML = originalBtnHTML;
                showToast(`Request failed: ${err.message}`, "error");
            });
    });

    function startDownloadPolling(animalName) {
        clearInterval(downloadPollInterval);

        downloadPollInterval = setInterval(() => {
            fetch("/api/download-progress")
                .then(res => res.json())
                .then(res => {
                    const data = res.data;
                    if (!data) return;

                    if (data.status === "validating") {
                        setStepState(step2, "completed");
                        setStepConnector(conn2, true);
                        setStepState(step3, "active");
                    }

                    metricImagesCount.textContent = `${data.validated || 0} / ${data.target || 100}`;
                    pipelineStatusMsg.textContent = data.message || "Downloading images...";

                    // Map download progress to 10% - 50%
                    const mappedPercent = Math.min(50, 10 + Math.floor((data.percent || 0) * 0.4));
                    pipelineProgressBar.style.width = `${mappedPercent}%`;
                    pipelinePercentVal.textContent = `${mappedPercent}%`;

                    if (data.status === "completed") {
                        clearInterval(downloadPollInterval);
                        setStepState(step2, "completed");
                        setStepConnector(conn2, true);
                        setStepState(step3, "completed");
                        setStepConnector(conn3, true);

                        logToTerminal(`[Download] ${data.validated} images downloaded and validated with PIL.`, "text-success");
                        logToTerminal(`[Trainer] Initiating deep neural network transfer learning on complete dataset...`, "text-info");

                        // Trigger Step 4: Retraining
                        triggerRetraining(animalName, data.validated);
                    } else if (data.status === "failed") {
                        clearInterval(downloadPollInterval);
                        logToTerminal(`[Error] Download failed: ${data.error}`, "text-error");
                        pipelineStatusMsg.textContent = "Download failed.";
                        showToast(data.error || "Image download failed.", "error");
                    }
                })
                .catch(err => {
                    console.error("Error polling download progress:", err);
                });
        }, 1200);
    }

    function triggerRetraining(animalName, validImagesCount) {
        setStepState(step4, "active");
        pipelineStatusMsg.textContent = "Configuring deep neural architecture & callbacks...";

        fetch("/api/train", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ animal: animalName, epochs: 10 })
        })
            .then(res => res.json())
            .then(data => {
                if (!data.success) {
                    logToTerminal(`[Trainer Error] ${data.error}`, "text-error");
                    pipelineStatusMsg.textContent = "Retraining failed to start.";
                    return;
                }
                startTrainingPolling(animalName, validImagesCount);
            })
            .catch(err => {
                logToTerminal(`[Trainer Error] Network error: ${err.message}`, "text-error");
            });
    }

    function startTrainingPolling(animalName, validImagesCount) {
        clearInterval(trainingPollInterval);

        trainingPollInterval = setInterval(() => {
            fetch("/api/training-status")
                .then(res => res.json())
                .then(res => {
                    const data = res.data;
                    if (!data) return;

                    if (data.train_accuracy) {
                        metricTrainAcc.textContent = `${data.train_accuracy}%`;
                    }
                    if (data.val_accuracy) {
                        metricValAcc.textContent = `${data.val_accuracy}%`;
                    }

                    if (data.status === "training") {
                        pipelineStatusMsg.textContent = data.message || `Training epoch ${data.current_epoch}/${data.total_epochs}...`;
                        
                        // Map training 50% - 90%
                        const mapped = Math.min(90, 50 + Math.floor((data.progress_percent || 0) * 0.4));
                        pipelineProgressBar.style.width = `${mapped}%`;
                        pipelinePercentVal.textContent = `${mapped}%`;

                        logToTerminal(`[Epoch ${data.current_epoch}/${data.total_epochs}] Train Acc: ${data.train_accuracy}%, Val Acc: ${data.val_accuracy}%, Loss: ${data.train_loss}`);
                    } else if (data.status === "validating_model") {
                        pipelineStatusMsg.textContent = "Validating weights & performing safe zero-downtime hot swap...";
                        pipelineProgressBar.style.width = "95%";
                        pipelinePercentVal.textContent = "95%";
                        logToTerminal("[Deploy] Validating temporary checkpoint and updating class_labels.json...", "text-info");
                    } else if (data.status === "completed") {
                        clearInterval(trainingPollInterval);
                        
                        setStepState(step4, "completed");
                        setStepConnector(conn4, true);
                        setStepState(step5, "completed");

                        pipelineProgressBar.style.width = "100%";
                        pipelinePercentVal.textContent = "100%";
                        pipelineStatusMsg.textContent = "Model updated and deployed successfully!";

                        logToTerminal(`[Success] Retraining complete! ${data.total_classes} classes now active.`, "text-success");

                        // Reveal confirmation card
                        successConfirmationBanner.classList.remove("hidden");
                        confDetailsText.textContent = `Species: ${animalName} • ${validImagesCount} new images • ${data.total_classes} total classes • Final Val Acc: ${data.val_accuracy}%.`;

                        showToast(`New animal "${animalName}" successfully added & retrained!`, "success");

                        // Refresh header badge and classes
                        fetchSupportedAnimals();
                    } else if (data.status === "error") {
                        clearInterval(trainingPollInterval);
                        logToTerminal(`[Error] Training failed: ${data.error}`, "text-error");
                        pipelineStatusMsg.textContent = "Retraining failed.";
                        showToast(data.error || "Training encountered an error.", "error");
                    }
                })
                .catch(err => {
                    console.error("Error polling training status:", err);
                });
        }, 1500);
    }

    finishPipelineBtn.addEventListener("click", () => {
        closeModal();
    });

    // Stepper UI helper
    function setStepState(stepElem, state) {
        stepElem.classList.remove("active", "completed");
        if (state) stepElem.classList.add(state);
    }

    function setStepConnector(connElem, isCompleted) {
        if (isCompleted) {
            connElem.classList.add("completed");
        } else {
            connElem.classList.remove("completed");
        }
    }

    function resetStepper() {
        [step1, step2, step3, step4, step5].forEach(s => setStepState(s, ""));
        [conn1, conn2, conn3, conn4].forEach(c => setStepConnector(c, false));
        pipelineProgressBar.style.width = "0%";
        pipelinePercentVal.textContent = "0%";
        metricAnimalName.textContent = "-";
        metricImagesCount.textContent = "0 / 100";
        metricTrainAcc.textContent = "--";
        metricValAcc.textContent = "--";
        pipelineLogTerminal.innerHTML = '<div class="log-line text-muted">[System] Ready to start pipeline...</div>';
    }

    function logToTerminal(msg, className = "") {
        const line = document.createElement("div");
        line.className = `log-line ${className}`;
        line.textContent = msg;
        pipelineLogTerminal.appendChild(line);
        pipelineLogTerminal.scrollTop = pipelineLogTerminal.scrollHeight;
    }

    // ==========================================
    // TOAST NOTIFICATIONS
    // ==========================================
    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;

        let icon = "fa-circle-info";
        if (type === "success") icon = "fa-circle-check";
        if (type === "error") icon = "fa-triangle-exclamation";

        toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.classList.add("fadeOut");
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 3500);
    }
});

