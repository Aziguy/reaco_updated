import starlight from "@astrojs/starlight";
import { defineConfig } from "astro/config";
import mermaid from "astro-mermaid";
import starlightLinksValidator from "starlight-links-validator";

export default defineConfig({
  site: "https://aziguy.github.io",
  base: "/reaco_updated",
  integrations: [
    mermaid({ theme: "neutral", autoTheme: true }),
    starlight({
      title: "Comégusto",
      description: "Documentation développeur de Comégusto : développement, architecture, déploiement et maintenance.",
      defaultLocale: "root",
      locales: { root: { label: "Français", lang: "fr" } },
      logo: {
        light: "./src/assets/comegusto-dark.png",
        dark: "./src/assets/comegusto-light.png",
        replacesTitle: true,
      },
      favicon: "/favicon.svg",
      social: [
        { icon: "github", label: "GitHub", href: "https://github.com/Aziguy/reaco_updated" },
      ],
      editLink: { baseUrl: "https://github.com/Aziguy/reaco_updated/edit/master/docs/" },
      lastUpdated: true,
      customCss: ["./src/styles/custom.css"],
      plugins: [starlightLinksValidator({ errorOnLocalLinks: false })],
      sidebar: [
        {
          label: "Démarrer",
          items: [
            { slug: "demarrer/installation" },
            { slug: "demarrer/visite" },
          ],
        },
        { label: "Architecture", items: [{ autogenerate: { directory: "architecture" } }] },
        { label: "Développement", items: [{ autogenerate: { directory: "developpement" } }] },
        { label: "Déploiement", items: [{ autogenerate: { directory: "deploiement" } }] },
        { label: "Maintenance", items: [{ autogenerate: { directory: "maintenance" } }] },
        { label: "Évolution", items: [{ autogenerate: { directory: "evolution" } }] },
        { label: "Référence", items: [{ autogenerate: { directory: "reference" } }] },
      ],
    }),
  ],
});
