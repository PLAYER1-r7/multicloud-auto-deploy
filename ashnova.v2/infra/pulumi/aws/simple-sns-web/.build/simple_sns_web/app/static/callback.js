(function () {
  const status = document.getElementById("status");
  const root = document.getElementById("callback-root");


  if (!status || !root) {
    return;
  }

  const sessionUrl = root.getAttribute("data-session-url") || "";
  const profileUrl = root.getAttribute("data-profile-url") || "/";

  if (!window.location.hash) {
    status.textContent = "No token in URL. Please retry login.";
    return;
  }

  const params = new URLSearchParams(window.location.hash.slice(1));
  const idToken = params.get("id_token");
  const accessToken = params.get("access_token");
  const expiresIn = params.get("expires_in");

  if (!idToken && !accessToken) {
    status.textContent = "Token missing. Please retry login.";
    return;
  }

  if (!sessionUrl) {
    status.textContent = "Session URL missing. Please retry login.";
    return;
  }

  fetch(sessionUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      id_token: idToken,
      access_token: accessToken,
      expires_in: expiresIn,
    }),
  })
    .then(async (res) => {
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Failed to store session (${res.status}): ${text}`);
      }
      window.location.replace(profileUrl);
    })
    .catch((err) => {
      status.textContent = `Login failed. ${err.message}`;
    });
})();
