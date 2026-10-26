const $ = (selector, root = document) => root.querySelector(selector);

function setupThemeToggle() {
  document.addEventListener("click", (event) => {
    if (!event.target.closest("[data-theme-toggle]")) return;
    const dark = document.documentElement.classList.toggle("dark");
    try {
      localStorage.setItem("theme", dark ? "dark" : "light");
    } catch (e) {}
  });
}

function setupMenu() {
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-menu-toggle]");
    if (!button) return;
    const menu = document.getElementById(button.getAttribute("aria-controls"));
    const open = button.getAttribute("aria-expanded") !== "true";
    button.setAttribute("aria-expanded", String(open));
    menu.classList.toggle("hidden", !open);
  });
}

function setupConfirm() {
  document.addEventListener("submit", (event) => {
    const message = event.target.dataset.confirm;
    if (message && !window.confirm(message)) event.preventDefault();
  });
}

function setupBrokenLogos() {
  document.addEventListener(
    "error",
    (event) => {
      const logo = event.target;
      if (!logo.matches?.("img[data-logo]")) return;
      logo.classList.add("hidden");
      logo.nextElementSibling?.classList.remove("hidden");
    },
    true,
  );
}

function setupAutosubmit() {
  document.addEventListener("change", (event) => {
    if (event.target.matches("[data-autosubmit]")) event.target.form.requestSubmit();
  });
}

function setupPrint() {
  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-print]")) window.print();
  });
}

function setupGeolocation() {
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-geolocate]");
    if (!button || !navigator.geolocation) return;
    const form = button.closest("form");
    button.disabled = true;
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        form.elements.latitude.value = coords.latitude.toFixed(5);
        form.elements.longitude.value = coords.longitude.toFixed(5);
        form.elements.postal_code.value = "";
        button.textContent = "Position enregistrée, pensez à valider";
      },
      () => {
        button.disabled = false;
        button.textContent = "Position indisponible";
      },
      { timeout: 10000 },
    );
  });
}

async function startScanner(root) {
  const video = $("video", root);
  const status = $("[data-scanner-status]", root);
  const input = document.getElementById(root.dataset.target);
  if (!("BarcodeDetector" in window)) {
    status.textContent = "Scan non disponible sur ce navigateur : saisissez le code-barres.";
    input.focus();
    return;
  }
  const detector = new BarcodeDetector({ formats: ["ean_13", "ean_8", "upc_a", "upc_e"] });
  const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
  video.srcObject = stream;
  video.hidden = false;
  await video.play();
  status.textContent = "Visez le code-barres du produit.";
  const stop = () => stream.getTracks().forEach((track) => track.stop());
  const tick = async () => {
    if (!video.isConnected) return stop();
    const codes = await detector.detect(video).catch(() => []);
    if (codes.length) {
      stop();
      video.hidden = true;
      input.value = codes[0].rawValue;
      input.dispatchEvent(new Event("change", { bubbles: true }));
      status.textContent = `Code détecté : ${codes[0].rawValue}`;
      return;
    }
    requestAnimationFrame(tick);
  };
  tick();
}

function setupScanner() {
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-scan]");
    if (!button) return;
    const root = button.closest("[data-scanner]");
    startScanner(root).catch(() => {
      $("[data-scanner-status]", root).textContent = "Caméra inaccessible : saisissez le code-barres.";
    });
  });
}

setupThemeToggle();
setupMenu();
setupConfirm();
setupPrint();
setupAutosubmit();
setupBrokenLogos();
setupGeolocation();
setupScanner();
