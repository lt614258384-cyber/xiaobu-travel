// Module-level state for photo upload
window.__uploadFiles = new DataTransfer();

function initPhotoUpload() {
    const zone = document.getElementById("upload-zone");
    const input = document.getElementById("photo-input");
    const previews = document.getElementById("photo-previews");
    const maxPhotos = 10;

    if (!zone || !input) return;
    zone.addEventListener("click", () => input.click());
    zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("dragover"); });
    zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
    zone.addEventListener("drop", e => { e.preventDefault(); zone.classList.remove("dragover"); addFiles(e.dataTransfer.files); });
    input.addEventListener("change", () => { addFiles(input.files); input.value = ""; });

    function addFiles(newFiles) {
        const dt = window.__uploadFiles;
        for (const file of newFiles) {
            if (dt.files.length >= maxPhotos) { alert("最多上传" + maxPhotos + "张照片"); break; }
            if (!file.type.startsWith("image/")) continue;
            dt.items.add(file);
        }
        renderPreviews();
    }
    function renderPreviews() {
        const dt = window.__uploadFiles;
        previews.innerHTML = "";
        for (let i = 0; i < dt.files.length; i++) {
            const url = URL.createObjectURL(dt.files[i]);
            const w = document.createElement("div");
            w.className = "photo-preview-wrapper";
            w.innerHTML = '<img src="' + url + '" class="photo-preview" alt="预览"><button class="remove" data-index="' + i + '" type="button">&times;</button>';
            w.querySelector(".remove").addEventListener("click", () => {
                const nf = new DataTransfer();
                for (let j = 0; j < dt.files.length; j++) if (j !== i) nf.items.add(dt.files[j]);
                window.__uploadFiles = nf;
                renderPreviews();
            });
            previews.appendChild(w);
        }
        document.getElementById("photo-count").textContent = dt.files.length + "/" + maxPhotos;
    }
}

function initTagGroups() {
    document.querySelectorAll(".tag-group").forEach(group => {
        group.addEventListener("click", e => {
            const tag = e.target.closest(".tag");
            if (!tag) return;
            if (group.dataset.multi !== "false") tag.classList.toggle("selected");
            else { group.querySelectorAll(".tag").forEach(t => t.classList.remove("selected")); tag.classList.add("selected"); }
            updateHiddenInput(group);
        });
    });
}

function updateHiddenInput(group) {
    const input = group.nextElementSibling;
    if (!input || !input.classList.contains("tag-value")) return;
    input.value = JSON.stringify(Array.from(group.querySelectorAll(".tag.selected")).map(t => t.textContent.trim()));
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}

function initProfileForm() {
    const form = document.getElementById("profile-form");
    if (!form) return;
    form.addEventListener("submit", async e => {
        e.preventDefault();
        // Inject CSRF token from cookie
        const csrf = getCookie('__Host-csrf');
        const csrfInput = document.getElementById('csrf-token');
        if (csrfInput) csrfInput.value = csrf;
        // Sync tag values
        document.querySelectorAll(".tag-value").forEach(inp => {
            const selected = Array.from(inp.previousElementSibling.querySelectorAll(".tag.selected")).map(t => t.textContent.trim());
            inp.value = JSON.stringify(selected);
        });
        // Build FormData from form fields
        const fd = new FormData(form);
        // Append uploaded files from DataTransfer (since the hidden input is cleared)
        const dt = window.__uploadFiles;
        for (let i = 0; i < dt.files.length; i++) {
            fd.append("photos", dt.files[i]);
        }
        const btn = form.querySelector(".btn-submit");
        btn.textContent = "保存中..."; btn.disabled = true;
        try {
            const resp = await fetch(form.action, { method: "POST", body: fd });
            if (resp.ok) {
                // Redirect to homepage — wait 2s for background generation to complete
                setTimeout(() => { window.location.href = "/"; }, 3000);
            } else {
                const err = await resp.json();
                alert("保存失败: " + (err.detail || "未知错误"));
                btn.textContent = "保存"; btn.disabled = false;
            }
        } catch (err) {
            alert("网络错误: " + err.message);
            btn.textContent = "保存"; btn.disabled = false;
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initPhotoUpload();
    initTagGroups();
    initProfileForm();
});
