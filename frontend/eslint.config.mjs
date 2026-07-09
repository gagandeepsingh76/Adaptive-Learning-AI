import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

const eslintConfig = [
  ...nextCoreWebVitals,
  ...nextTypescript,
  {
    rules: {
      "react-hooks/immutability": "off",
      "react-hooks/set-state-in-effect": "off"
    }
  },
  {
    ignores: [".next/**", "coverage/**", "next-env.d.ts", "node_modules/**", "out/**"]
  }
];

export default eslintConfig;
