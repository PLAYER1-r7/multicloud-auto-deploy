(function () {
  const lightbox = document.getElementById("lightbox");
  const lightboxImage = document.getElementById("lightbox-image");

  if (!lightbox || !lightboxImage) {
    return;
  }

  function openLightbox(url) {
    lightboxImage.src = url;
    lightbox.hidden = false;
    document.body.style.overflow = "hidden";
  }

  function closeLightbox() {
    lightboxImage.removeAttribute("src");
    lightbox.hidden = true;
    document.body.style.overflow = "";
  }

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) {
      return;
    }

    const thumb = target.closest(".thumb-button");
    if (thumb instanceof HTMLElement) {
      const url = thumb.getAttribute("data-full") || "";
      if (url) {
        openLightbox(url);
      }
      return;
    }

    if (target.closest("[data-close]") || target.classList.contains("lightbox")) {
      closeLightbox();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !lightbox.hidden) {
      closeLightbox();
    }
  });
})();
