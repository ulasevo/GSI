/*
 * Radio P53 landing-page context and focus behavior.
 * Links inherit the route context, while IntersectionObserver only adds a visual
 * focus class; native document scrolling remains the source of movement.
 */
(() => {
  const contextNode = document.querySelector("#p53-landing-context");
  let landingContext = {};
  if (contextNode) {
    try {
      landingContext = JSON.parse(contextNode.textContent || "{}");
    } catch {
      landingContext = {};
    }
  }
  // Keep the landing return path aligned with the same shared URL rules as the
  // homepage and permanent transmission pages.
  const p53State = GSIContext.read();
  const p53Params = GSIContext.archiveParams({
    state: p53State,
    filterLabels: landingContext.filterLabels || {},
  });
  const p53Artist = p53State.get("artist");
  const artistSlugs = Array.isArray(landingContext.artistSlugs) ? landingContext.artistSlugs : [];
  if (p53Artist && artistSlugs.includes(p53Artist)) p53Params.set("artist", p53Artist);

  const query = p53Params.size ? `?${p53Params}` : "";
  const homeParams = new URLSearchParams(p53Params);
  homeParams.delete("artist");
  const homeQuery = homeParams.size ? `?${homeParams}` : "";

  const homeReturn = document.querySelector("#p53-home-return");
  if (homeReturn) homeReturn.href = `../index.html${homeQuery}`;
  document.querySelectorAll("[data-base-href]").forEach(link => {
    link.href = `${link.dataset.baseHref}${query}`;
  });

  const cards = [...document.querySelectorAll(".transmission-card")];
  if (!cards.length || !("IntersectionObserver" in window)) return;

  // Focus is intentionally a class, not a scroll command. Browsers without the
  // observer still receive a complete readable list.
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      cards.forEach(card => card.classList.remove("is-focused"));
      entry.target.classList.add("is-focused");
    });
  }, { rootMargin: "-28% 0px -52% 0px", threshold: 0.15 });
  cards.forEach(card => observer.observe(card));
})();
