import eslint from "@eslint/js";
import vue from "eslint-plugin-vue";
import { defineConfig, createConfig } from "@vue/eslint-config-typescript";

export default defineConfig(
  {
    ignores: ["dist/**", "node_modules/**", "**/.vite/**", "src/api/schema.d.ts"],
  },
  eslint.configs.recommended,
  ...vue.configs["flat/recommended"],
  ...createConfig(),
  {
    rules: {
      "vue/multi-word-component-names": "off",
    },
  },
  {
    files: ["scripts/**/*.mjs"],
    languageOptions: {
      globals: {
        console: "readonly",
      },
    },
  },
  {
    files: ["src/components/SanitizedHtml.vue"],
    rules: {
      "vue/no-v-html": "off",
    },
  },
);
