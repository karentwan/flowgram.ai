/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

const { defineFlatConfig } = require('@flowgram.ai/eslint-config');

module.exports = defineFlatConfig({
  preset: 'node',
  packageRoot: __dirname,
  rules: {
    'no-console': 'off',
  },
});
