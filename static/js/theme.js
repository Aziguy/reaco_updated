(() => {
  let theme = null;
  try {
    theme = localStorage.getItem("theme");
  } catch (e) {}
  const dark = theme ? theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.classList.toggle("dark", dark);
})();
