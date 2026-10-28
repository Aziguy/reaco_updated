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

function setupAiForms() {
  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!form.matches("[data-ai-form]") || event.defaultPrevented) return;
    form.classList.add("is-loading");
    form.setAttribute("aria-busy", "true");
  });
  window.addEventListener("pageshow", () => {
    document.querySelectorAll("[data-ai-form].is-loading").forEach((form) => {
      form.classList.remove("is-loading");
      form.removeAttribute("aria-busy");
    });
  });
}

function setupDropzone() {
  document.addEventListener("change", (event) => {
    const zone = event.target.closest("[data-dropzone]");
    const file = event.target.files?.[0];
    if (!zone || !file) return;
    const preview = $("[data-preview]", zone);
    preview.src = URL.createObjectURL(file);
    preview.classList.remove("hidden");
    $("[data-placeholder]", zone).classList.add("hidden");
    $("[data-filename]", zone).textContent = file.name;
  });
}

function csrfToken() {
  try {
    return JSON.parse(document.body.getAttribute("hx-headers"))["X-CSRFToken"];
  } catch (e) {
    return "";
  }
}

function initChips(root) {
  root.querySelectorAll("[data-chips]:not([data-ready])").forEach((box) => {
    box.dataset.ready = "1";
    const source = $("input", box);
    const split = (text) => text.split(",").map((n) => n.trim()).filter(Boolean);
    let chips = split(source.value);
    const field = document.createElement("div");
    field.className =
      "flex min-h-11 flex-wrap items-center gap-1.5 rounded-xl border border-stone-300 bg-white px-2 py-1.5 " +
      "focus-within:border-brand-500 focus-within:ring-2 focus-within:ring-brand-500/30 dark:border-stone-700 dark:bg-stone-950";
    const typing = document.createElement("input");
    typing.type = "text";
    typing.id = source.id;
    typing.setAttribute("list", source.getAttribute("list") || "");
    typing.autocomplete = "off";
    typing.className =
      "min-w-32 flex-1 bg-transparent px-1 py-1 text-base text-stone-900 placeholder:text-stone-400 focus:outline-none dark:text-white";
    const placeholder = source.placeholder;
    source.removeAttribute("id");
    source.type = "hidden";

    const sync = () => {
      source.value = [...chips, ...split(typing.value)].join(", ");
    };
    const render = () => {
      field.querySelectorAll("[data-chip]").forEach((chip) => chip.remove());
      chips.forEach((name) => {
        const chip = document.createElement("span");
        chip.dataset.chip = "";
        chip.className = "ai-chip !py-0.5";
        chip.textContent = name;
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "ai-chip-remove !size-5";
        remove.setAttribute("aria-label", `Retirer ${name}`);
        remove.textContent = "×";
        remove.addEventListener("click", () => {
          chips = chips.filter((n) => n !== name);
          render();
          typing.focus();
        });
        chip.append(remove);
        field.insertBefore(chip, typing);
      });
      typing.placeholder = chips.length ? "Ajouter…" : placeholder;
      sync();
    };
    const commit = () => {
      const known = chips.map((n) => n.toLowerCase());
      const added = split(typing.value).filter((n) => !known.includes(n.toLowerCase()));
      if (!typing.value.trim()) return false;
      chips = [...chips, ...added];
      typing.value = "";
      render();
      return true;
    };
    typing.addEventListener("keydown", (event) => {
      if ((event.key === "Enter" || event.key === ",") && commit()) event.preventDefault();
      if (event.key === "Backspace" && !typing.value && chips.length) {
        chips = chips.slice(0, -1);
        render();
      }
    });
    typing.addEventListener("input", (event) => {
      if (event.inputType === "insertReplacementText" || !event.inputType) commit();
      else sync();
    });
    typing.addEventListener("blur", commit);
    field.addEventListener("click", (event) => event.target === field && typing.focus());
    field.append(typing);
    box.append(field);
    render();
  });
}

function setupChips() {
  initChips(document);
  document.addEventListener("htmx:load", (event) => initChips(event.target));
}

function setupPhotoIngredients() {
  document.addEventListener("change", async (event) => {
    const input = event.target.closest("[data-photo-ingredients]");
    const file = input?.files?.[0];
    if (!file) return;
    const box = document.getElementById(input.dataset.target);
    const data = new FormData();
    data.append("photo", file);
    data.append("j", $("input[name=j]", box)?.value || "");
    box.classList.add("is-loading");
    box.setAttribute("aria-busy", "true");
    try {
      const response = await fetch(input.dataset.url, {
        method: "POST",
        body: data,
        headers: { "X-CSRFToken": csrfToken(), "HX-Request": "true" },
      });
      box.outerHTML = await response.text();
      initChips(document.getElementById(input.dataset.target).parentElement);
    } catch (e) {
      box.classList.remove("is-loading");
      box.removeAttribute("aria-busy");
    }
  });
}

function setupCopy() {
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-copy]");
    if (!button) return;
    const label = $("[data-copy-label]", button);
    try {
      await navigator.clipboard.writeText(button.dataset.copy);
      if (label) label.textContent = "Copié";
    } catch (e) {
      if (label) label.textContent = "Sélectionnez";
    }
    setTimeout(() => label && (label.textContent = "Copier"), 2000);
  });
}

function setupWebauthnErrors() {
  document.addEventListener("allauth.error", (event) => {
    const message = $("[data-webauthn-error]");
    if (!message) return;
    event.preventDefault();
    message.hidden = false;
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
setupAiForms();
setupDropzone();
setupChips();
setupPhotoIngredients();
setupCopy();
setupWebauthnErrors();
