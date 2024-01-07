document.body.addEventListener("click", async (event) => {
  if (event.target.tagName === "A") {
    event.preventDefault(); // Prevent default link behavior

    const href = event.target.getAttribute("href"); // Get the href attribute

    // Change URL state using replaceState
    window.history.replaceState(null, null, href);

    // Fetch data
    const res = await fetch(href, {
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "Content-type": "application/python",
      },
    });

    if (res.ok) {
      const data = await res.json(); // Parse JSON response
      const { body, script } = data; // Destructure data object

      // Update DOM
      document.getElementById("main").innerHTML = body;
    }
  }
});
