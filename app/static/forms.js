// Forms marked <form data-background> are sent with fetch() instead of loading a new page.
document.addEventListener("submit", async (event) => {
  const form = event.target.closest("form[data-background]");
  // defaultPrevented: the form's onsubmit="return confirm(...)" was cancelled
  if (!form || event.defaultPrevented) return;
  event.preventDefault();

  let response;
  try {
    response = await fetch(form.action, {
      method: "POST",
      body: new URLSearchParams(new FormData(form)), // encoded like a normal form
    });
  } catch {
    return form.submit(); // network error: try a normal submit instead
  }

  if (!response.ok) return form.submit(); // 404/409/...: let the server show its error page
  if (new URL(response.url).pathname !== location.pathname) {
    location.href = response.url; // the redirect leads elsewhere, e.g. to /login
    return;
  }
  const page = new DOMParser().parseFromString(
    await response.text(),
    "text/html",
  );
  document.querySelector("main").replaceWith(page.querySelector("main"));
});
