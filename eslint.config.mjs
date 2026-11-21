import firebaseRulesPlugin from '@firebase/eslint-plugin-security-rules';

export default [
  {
    ignores: [
      'dist/**/*',
      'site/**/*',
      'android/**/*',
      'node_modules/**/*',
      'web/**/*',
      'src/**/*',
      'tests/**/*',
      'tools/**/*',
    ],
  },
  firebaseRulesPlugin.configs['flat/recommended'],
];
