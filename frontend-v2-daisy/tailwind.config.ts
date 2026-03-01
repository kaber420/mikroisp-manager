import type { Config } from "tailwindcss";
import daisyui from "daisyui";

export default {
  content: ["./src/**/*.{html,js,svelte,ts}"],
  theme: {
    extend: {},
  },
  plugins: [daisyui],
  daisyui: {
    themes: [
      "light",
      "dark",
      "corporate",
      "dracula",
      "cyberpunk",
      "dim",
      "synthwave",
      "night",
      "forest",
      "garden",
    ],
    darkTheme: "dark",
    base: true,
    styled: true,
    utils: true,
  },
} satisfies Config;
