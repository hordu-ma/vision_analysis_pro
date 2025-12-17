import js from '@eslint/js'
import prettierConfig from 'eslint-config-prettier'
import prettier from 'eslint-plugin-prettier'
import pluginVue from 'eslint-plugin-vue'
import typescript from 'typescript-eslint'
import vueParser from 'vue-eslint-parser'

export default [
  js.configs.recommended,
  ...typescript.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  prettierConfig,
  {
    files: ['**/*.{js,mjs,cjs,ts,vue}'],
    plugins: {
      prettier
    },
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: typescript.parser,
        ecmaVersion: 'latest',
        sourceType: 'module'
      },
      globals: {
        console: 'readonly',
        File: 'readonly',
        URL: 'readonly',
        document: 'readonly',
        window: 'readonly'
      }
    },
    rules: {
      'prettier/prettier': 'error',
      'vue/multi-word-component-names': 'off',
      '@typescript-eslint/no-explicit-any': 'warn'
    }
  },
  {
    ignores: ['node_modules/**', 'dist/**']
  }
]
