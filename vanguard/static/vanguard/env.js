async function main() {
  let pyodide = await loadPyodide();
  console.log(
    pyodide.runPython(`
            import sys
            sys.version
        `)
  );
  pyodide.runPython("print(1 + 2)");
}
main();
