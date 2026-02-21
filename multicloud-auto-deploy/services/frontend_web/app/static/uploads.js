
(function() {
function initUploads() {
  console.log("uploads.js initializing v9 fixed");
  const form = document.getElementById("post-form");
  if (!form) return;

  const fileInput = document.getElementById("images");
  const postStatus = document.getElementById("post-status");
  const submitButton = document.getElementById("post-submit-button");
  const imageKeysContainer = document.getElementById("image-keys");
  const previewGrid = document.getElementById("image-preview");
  const uploadError = document.getElementById("upload-error");
  const previewUrls = [];

  const basePath = form.getAttribute("data-base-path") || "";
  const allowedTypes = new Set([
     "image/jpeg", "image/png", "image/heic", "image/heif"
  ]);
  const extensionMap = {
     jpg: "image/jpeg", jpeg: "image/jpeg", png: "image/png", heic: "image/heic", heif: "image/heif"
  };

  function showError(message) {
      if (uploadError) { uploadError.textContent = message; uploadError.hidden = false; }
  }
  function clearError() {
      if (uploadError) { uploadError.textContent = ""; uploadError.hidden = true; }
  }
  function guessContentType(file) {
      if (file.type && allowedTypes.has(file.type)) return file.type;
      const name = (file.name || "").toLowerCase();
      const parts = name.split(".");
      const ext = parts.length > 1 ? parts.pop() : "";
      return (ext && extensionMap[ext]) ? extensionMap[ext] : "";
  }
  function clearPreviews() {
      if (!previewGrid) return;
      previewUrls.forEach(url => URL.revokeObjectURL(url));
      previewUrls.length = 0;
      previewGrid.innerHTML = "";
  }
  function addPreview(file, contentType, index, total) {
      if (!previewGrid) return;
      const item = document.createElement("button");
      item.type = "button";
      item.className = "thumb-button preview-item";
      const url = URL.createObjectURL(file);
      previewUrls.push(url);
      item.setAttribute("data-full", url);
      
      if (contentType === "image/heic" || contentType === "image/heif") {
          const div = document.createElement("div");
          div.className = "preview-fallback";
          div.textContent = "HEIC";
          item.appendChild(div);
      } else {
          const img = document.createElement("img");
          img.className = "preview-image";
          img.src = url;
          item.appendChild(img);
      }
      previewGrid.appendChild(item);
  }

  // Previews
  if (fileInput) {
      fileInput.addEventListener("change", () => {
          clearError();
          clearPreviews();
          const files = Array.from(fileInput.files || []);
          files.forEach((file, i) => {
              const type = guessContentType(file);
              if (type && allowedTypes.has(type)) {
                  addPreview(file, type, i, files.length);
              }
          });
      });
  }

  // Submit Handler
  form.addEventListener("submit", async (event) => {
      console.log("Submit triggered");
      if (!form.checkValidity()) return;

      const files = fileInput ? Array.from(fileInput.files || []) : [];

      // Text Only
      if (files.length === 0) {
          console.log("Text-only path");
          // Use setTimeout 0 to yield to the browser's form submission process
          setTimeout(() => {
              if (submitButton) submitButton.disabled = true;
              if (postStatus) {
                  postStatus.hidden = false;
                  postStatus.textContent = "投稿中... (0.0s)";
                  const start = Date.now();
                  setInterval(() => {
                      const sec = ((Date.now() - start) / 1000).toFixed(1);
                      postStatus.textContent = `投稿中... (${sec}s)`;
                  }, 100);
              }
          }, 0);
          return; // Let the form submit normally
      }

      // Image Upload Path
      event.preventDefault();
      console.log("Image upload path");
      clearError();

      if (files.length > 16) {
          showError("Too many images (max 16)");
          return;
      }

      if (submitButton) submitButton.disabled = true;
      let timer = null;
      if (postStatus) {
          postStatus.hidden = false;
          postStatus.textContent = "アップロード中... (0.0s)";
          const start = Date.now();
          timer = setInterval(() => {
              const sec = ((Date.now() - start) / 1000).toFixed(1);
              postStatus.textContent = `アップロード中... (${sec}s)`;
          }, 100);
      }

      try {
          const contentTypes = [];
          for (const f of files) {
              const t = guessContentType(f);
              if (!t || !allowedTypes.has(t)) throw new Error("Unsupported image type");
              contentTypes.push(t);
          }

          // 1. Get Presigned URLs
          const res1 = await fetch(`${basePath}/uploads`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ count: files.length, contentTypes })
          });
          if (!res1.ok) throw new Error("Failed to get upload URLs");
          const data = await res1.json();
          const urls = data.urls || [];

          // 2. Upload to storage
          const keys = await Promise.all(files.map(async (file, i) => {
               const u = urls[i]; 
               if (!u) throw new Error("Missing upload URL");
               // x-ms-blob-type is Azure Blob Storage specific; do NOT send for GCS
               const uploadHeaders = { "Content-Type": contentTypes[i] };
               if (u.url.includes(".blob.core.windows.net")) {
                   uploadHeaders["x-ms-blob-type"] = "BlockBlob";
               }
               const uploadRes = await fetch(u.url, {
                   method: "PUT",
                   headers: uploadHeaders,
                   body: file
               });
               if (!uploadRes.ok) throw new Error(`Upload failed (${uploadRes.status})`);
               return u.key;
          }));

          // 3. Append hidden inputs
          imageKeysContainer.innerHTML = "";
          keys.forEach(k => {
              const inp = document.createElement("input");
              inp.type = "hidden";
              inp.name = "image_keys";
              inp.value = k;
              imageKeysContainer.appendChild(inp);
          });

          // 4. Submit
          if (postStatus) {
              postStatus.textContent = "投稿処理中...";
              if (timer) clearInterval(timer);
          }
          // The file input should be cleared to not re-send files? 
          // If we are simulating form submission, we can just call submit.
          // But if we clear the input, standard submit won't send the files.
          // Since we already uploaded them, we DON'T want to send them again to the server if the server logic only looks at image_keys.
          // Let's check server logic? Assuming yes.
          fileInput.value = ""; 
          
          form.submit();

      } catch (e) {
          console.error(e);
          showError(e.message || "Upload failed");
          if (submitButton) submitButton.disabled = false;
          if (postStatus) postStatus.hidden = true;
          if (timer) clearInterval(timer);
      }
  });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initUploads);
} else {
    initUploads();
}
})();
