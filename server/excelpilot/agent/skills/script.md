You are executing the Script Generation skill.

TypeScript Office.js Guidelines:
1. Wrap all interactions inside an async function main(context: Excel.RequestContext).
2. Load only the necessary properties on objects before calling await context.sync().
3. Call context.sync() at most once or twice. Batch loads and writes together.
4. Do not use prohibited APIs: fetch, XMLHttpRequest, eval, Function, window, document, or localStorage.
5. Provide a short 2 to 3 bullet explanation of what the script does before executing it.
