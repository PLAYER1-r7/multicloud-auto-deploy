(function () {
  const modal = document.getElementById("post-modal");
  const modalUser = document.getElementById("modal-user");
  const modalTime = document.getElementById("modal-time");
  const modalContent = document.getElementById("modal-content");
  const modalImages = document.getElementById("modal-images");
  const modalTags = document.getElementById("modal-tags");
  const modalLink = document.getElementById("modal-link");
  const searchToggle = document.getElementById("search-toggle");
  const searchPanel = document.getElementById("search-panel");

  function formatRelativeTime(iso) {
    if (!iso) {
      return "";
    }
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) {
      return iso;
    }
    const diffMs = date.getTime() - Date.now();
    const diffSeconds = Math.round(diffMs / 1000);
    const absSeconds = Math.abs(diffSeconds);
    const rtf = new Intl.RelativeTimeFormat("ja", { numeric: "auto" });

    if (absSeconds < 60) {
      return rtf.format(diffSeconds, "second");
    }
    const diffMinutes = Math.round(diffSeconds / 60);
    if (Math.abs(diffMinutes) < 60) {
      return rtf.format(diffMinutes, "minute");
    }
    const diffHours = Math.round(diffMinutes / 60);
    if (Math.abs(diffHours) < 24) {
      return rtf.format(diffHours, "hour");
    }
    const diffDays = Math.round(diffHours / 24);
    if (Math.abs(diffDays) < 30) {
      return rtf.format(diffDays, "day");
    }
    const diffMonths = Math.round(diffDays / 30);
    if (Math.abs(diffMonths) < 12) {
      return rtf.format(diffMonths, "month");
    }
    const diffYears = Math.round(diffMonths / 12);
    return rtf.format(diffYears, "year");
  }

  function updateRelativeTimes() {
    document.querySelectorAll("[data-iso]").forEach((el) => {
      const iso = el.getAttribute("data-iso") || "";
      el.textContent = formatRelativeTime(iso);
    });
  }

  function openModal(postEl) {
    if (!modal || !modalUser || !modalTime || !modalContent || !modalImages || !modalTags || !modalLink) {
      return;
    }
    const user = postEl.getAttribute("data-user") || "";
    const created = postEl.getAttribute("data-created") || "";
    const content = postEl.getAttribute("data-content") || "";
    const tagsRaw = postEl.getAttribute("data-tags") || "";
    const imagesRaw = postEl.getAttribute("data-images") || "";
    const postId = postEl.getAttribute("data-post-id") || "";

    modalUser.textContent = user;
    modalTime.textContent = formatRelativeTime(created);
    modalContent.textContent = content;
    modalImages.innerHTML = "";
    modalTags.innerHTML = "";
    const detailUrl = postId ? `${postEl.baseURI.replace(/\/$/, "")}/posts/${postId}` : "#";
    modalLink.setAttribute("data-href", detailUrl);

    const images = imagesRaw ? imagesRaw.split(",").filter(Boolean) : [];
    images.forEach((url, index) => {
      const button = document.createElement("button");
      button.className = "thumb-button";
      button.type = "button";
      button.setAttribute("data-full", url);
      button.setAttribute("aria-label", "Open image");

      const img = document.createElement("img");
      img.className = "post-image";
      img.src = url;
      img.alt = "Post image";
      img.loading = "lazy";

      button.appendChild(img);

      if (images.length > 1) {
        const badge = document.createElement("span");
        badge.className = "thumb-count";
        badge.textContent = `${index + 1}/${images.length}`;
        button.appendChild(badge);
      }

      modalImages.appendChild(button);
    });

    const tags = tagsRaw ? tagsRaw.split(",").filter(Boolean) : [];
    tags.forEach((tag) => {
      const span = document.createElement("span");
      span.className = "tag";
      span.textContent = tag;
      modalTags.appendChild(span);
    });

    modal.hidden = false;
    document.body.style.overflow = "hidden";
  }

  function closeModal() {
    if (!modal) {
      return;
    }
    modal.hidden = true;
    document.body.style.overflow = "";
  }

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) {
      return;
    }

    if (target.closest("[data-close]")) {
      closeModal();
      return;
    }

    const postCard = target.closest(".post-card");
    if (postCard && !target.closest(".thumb-button") && !target.closest(".post-link")) {
      openModal(postCard);
      return;
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && modal && !modal.hidden) {
      closeModal();
    }
  });

  if (searchToggle && searchPanel) {
    searchToggle.addEventListener("click", () => {
      const isHidden = searchPanel.hasAttribute("hidden");
      if (isHidden) {
        searchPanel.removeAttribute("hidden");
      } else {
        searchPanel.setAttribute("hidden", "");
      }
      searchToggle.setAttribute("aria-expanded", String(isHidden));
    });
  }

  const params = new URLSearchParams(window.location.search);
  if (searchPanel && (params.get("tag") || params.get("q"))) {
    searchPanel.removeAttribute("hidden");
    if (searchToggle) {
      searchToggle.setAttribute("aria-expanded", "true");
    }
  }

  updateRelativeTimes();
})();
