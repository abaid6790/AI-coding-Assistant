Reserved for shared custom React hooks. None exist yet — `useAuth()` and
`useToast()` currently live alongside their providers in `src/context/`
since each is only ever used together with its provider. Extract a hook
here if one starts being reused independently of its current context.
