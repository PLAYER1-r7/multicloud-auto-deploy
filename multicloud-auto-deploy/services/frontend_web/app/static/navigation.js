(function () {
  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) {
      return;
    }
    const button = target.closest("[data-href]");
    if (!(button instanceof HTMLButtonElement)) {
      return;
    }
    const href = button.getAttribute("data-href");
    if (!href) {
      return;
    }
    if (button.disabled) {
      return;
    }
    window.location.href = href;
  });
})();
