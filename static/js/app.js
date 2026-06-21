function initPhotoUpload() {
    const zone = document.getElementById("upload-zone");
    const input = document.getElementById("photo-input");
    const previews = document.getElementById("photo-previews");
    const maxPhotos = 10;
    let files = new DataTransfer();

    if (!zone || !input) return;
    zone.addEventListener("click", () => input.click());
    zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("dragover"); });
    zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
    zone.addEventListener("drop", e => { e.preventDefault(); zone.classList.remove("dragover"); addFiles(e.dataTransfer.files); });
    input.addEventListener("change", () => { addFiles(input.files); input.value = ""; });

    function addFiles(newFiles) {
        for (const file of newFiles) {
            if (files.files.length >= maxPhotos) { alert(`最多上传${maxPhotos}张照片`); break; }
            if (!file.type.startsWith("image/")) continue;
            files.items.add(file);
        }
        renderPreviews();
    }
    function renderPreviews() {
        previews.innerHTML = "";
        for (let i = 0; i < files.files.length; i++) {
            const url = URL.createObjectURL(files.files[i]);
            const w = document.createElement("div");
            w.className = "photo-preview-wrapper";
            w.innerHTML = `<img src="${url}" class="photo-preview" alt="预览"><button class="remove" data-index="${i}" type="button">&times;</button>`;
            w.querySelector(".remove").addEventListener("click", () => {
                const nf = new DataTransfer();
                for (let j = 0; j < files.files.length; j++) if (j !== i) nf.items.add(files.files[j]);
                files = nf; renderPreviews();
            });
            previews.appendChild(w);
        }
        document.getElementById("photo-count").textContent = `${files.files.length}/${maxPhotos}`;
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

function initProfileForm() {
    const form = document.getElementById("profile-form");
    if (!form) return;
    form.addEventListener("submit", async e => {
        e.preventDefault();
        document.querySelectorAll(".tag-value").forEach(inp => {
            const selected = Array.from(inp.previousElementSibling.querySelectorAll(".tag.selected")).map(t => t.textContent.trim());
            inp.value = JSON.stringify(selected);
        });
        const fd = new FormData(form);
        const btn = form.querySelector(".btn-submit");
        btn.textContent = "保存中..."; btn.disabled = true;
        try {
            const resp = await fetch(form.action, { method: "POST", body: fd });
            if (resp.ok) window.location.href = "/";
            else { const err = await resp.json(); alert("保存失败: " + (err.detail || "未知错误")); }
        } catch (err) {
            alert("网络错误: " + err.message);
        } finally { btn.textContent = "保存"; btn.disabled = false; }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initPhotoUpload();
    initTagGroups();
    initProfileForm();
});
