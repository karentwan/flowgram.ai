/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

export const DEFAULT_JS_CODE = `// Here, you can retrieve input variables from the node using 'params' and output results using 'ret'.
// 'params' has been correctly injected into the environment.
// Here's an example of getting the value of the parameter named 'input' from the node input:
// const input = params.input;
// Here's an example of outputting a 'ret' object containing multiple data types:
// const ret = { "name": 'Xiaoming', "hobbies": ["Reading", "Traveling"] };

async function main({ params }) {
  // Build the output object
  const ret = {
    key0: params.input + params.input, // Concatenate the input parameter 'input' twice
    key1: ["hello", "world"], // Output an array
    key2: { // Output an Object
      key21: "hi"
    },
  };

  return ret;
}`;

export const DEFAULT_PYTHON_CODE = `# Retrieve input variables from the node using 'params' (a dict) and return a dict of outputs.
# Example of getting the value of the parameter named 'input' from the node input:
#   value = params.get('input')
# Example of outputting a dict containing multiple data types:
#   return {'key0': 'value'}

def main(params):
    return {
        'key0': str(params.get('input', '')),
        'key1': ['hello', 'world'],
        'key2': {'key21': 'hi'},
    }
`;
