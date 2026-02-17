(function () {
  const form = document.getElementById("post-form");
  const fileInput = document.getElementById("images");
  const uploadError = document.getElementById("upload-error");
  const imageKeysContainer = document.getElementById("image-keys");
  const previewGrid = document.getElementById("image-preview");
  const previewUrls = [];

  if (!form || !fileInput || !imageKeysContainer) {
    return;
  }

  const basePath = form.getAttribute("data-base-path") || "";
  const allowedTypes = new Set([
    "image/jpeg",
    "image/png",
    "image/heic",
    "image/heif",
  ]);
  const extensionMap = {
    jpg: "image/jpeg",
    jpeg: "image/jpeg",
    png: "image/png",
    heic: "image/heic",
    heif: "image/heif",
  };

  function showError(message) {
    if (!uploadError) {
      return;
    }
    uploadError.textContent = message;
    uploadError.hidden = false;
  }

  function clearError() {
    if (!uploadError) {
      return;
    }
    uploadError.textContent = "";
    uploadError.hidden = true;
  }

  function guessContentType(file) {
    if (file.type && allowedTypes.has(file.type)) {
      return file.type;
    }
    const name = (file.name || "").toLowerCase();
    const parts = name.split(".");
    const ext = parts.length > 1 ? parts.pop() : "";
    if (ext && extensionMap[ext]) {
      return extensionMap[ext];
    }
    return "";
  }

  function clearPreviews() {
    if (!previewGrid) {
      return;
    }
    previewUrls.splice(0).forEach((url) => URL.revokeObjectURL(url));
    previewGrid.innerHTML = "";
  }

  function addPreview(file, contentType, index, total) {
    if (!previewGrid) {
      return;
    }
    const item = document.createElement("button");
    item.type = "button";
    item.className = "thumb-button preview-item";
    item.setAttribute("aria-label", "Open image");
    const isHeic = contentType === "image/heic" || contentType === "image/heif";
    const url = URL.createObjectURL(file);
    previewUrls.push(url);
    item.setAttribute("data-full", url);
    if (isHeic) {
      const fallback = document.createElement("div");
      fallback.className = "preview-fallback";
      fallback.textContent = "HEIC";
      item.appendChild(fallback);
    } else {
      const img = document.createElement("img");
      img.className = "preview-image";
      img.src = url;
      item.appendChild(img);
    }

    const badge = document.createElement("span");
    badge.className = "thumb-count preview-count";
    badge.textContent = `${index + 1}/${total}`;
    badge.style.pointerEvents = "none";
    item.appendChild(badge);

    previewGrid.appendChild(item);
  }

  fileInput.addEventListener("change", () => {
    clearError();
    clearPreviews();
    const files = Array.from(fileInput.files || []);
    files.forEach((file, index) => {
      const contentType = guessContentType(file);
      if (!contentType || !allowedTypes.has(contentType)) {
        return;
      }
      addPreview(file, contentType, index, files.length);
    });
  });

  form.addEventListener("submit", async (event) => {
    const files = Array.from(fileInput.files || []);
    if (files.length === 0) {
      return;
    }

    event.preventDefault();
    clearError();

    if (files.length > 16) {
      showError("Too many images (max 16)");
      return;
    }

    const contentTypes = [];
    for (const file of files) {
      const contentType = guessContentType(file);
      if (!contentType || !allowedTypes.has(contentType)) {
        showError("Only JPEG/PNG/HEIC/HEIF images are supported");
        return;
      }
      contentTypes.push(contentType);
    }

    try {
      const uploadRes = await fetch(`${basePath}/uploads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ count: files.length, contentTypes }),
      });

      if (!uploadRes.ok) {
        const text = await uploadRes.text();
        throw new Error(`Upload URL request failed (${uploadRes.status}): ${text}`);
      }

      const uploadBody = await uploadRes.json();
      const urls = Array.isArray(uploadBody.urls) ? uploadBody.urls : [];
      if (urls.length !== files.length) {
        throw new Error("Upload URL count mismatch");
      }

      imageKeysContainer.innerHTML = "";

      for (let i = 0; i < files.length; i += 1) {
        const uploadInfo = urls[i] || {};
        const url = uploadInfo.url;
        const key = uploadInfo.key;
        if (!url || !key) {
          throw new Error("Upload URL missing");
        }

        const putRes = await fetch(url, {
          method: "PUT",
          headers: { "Content-Type": contentTypes[i] },
          body: files[i],
        });

        if (!putRes.ok) {
          throw new Error(`Upload failed (${putRes.status})`);
        }

        const input = document.createElement("input");
        input.type = "hidden";
        input.name = "image_keys";
        input.value = key;
        imageKeysContainer.appendChild(input);
      }

      fileInput.value = "";
      form.submit();
    } catch (err) {
      showError(err instanceof Error ? err.message : "Upload failed");
    }
  });
})();