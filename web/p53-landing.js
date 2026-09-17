/* Radio P53 landing-page context and focus behavior. */
(() => {
  const p53State = GSIContext.read();
  const p53Params = new URLSearchParams();
  const p53Filter = p53State.get("filter");
  const p53View = p53State.get("view");
  if (p53Filter) p53Params.set("filter", p53Filter);
  if (GSIContext.allowedViews.has(p53View)) p53Params.set("view", p53View);
  if (p53State.get("format") === "albums") p53Params.set("format", "albums");
  const p53Artist = p53State.get("artist");
  if (p53Artist) p53Params.set("artist", p53Artist);

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

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      cards.forEach(card => card.classList.remove("is-focused"));
      entry.target.classList.add("is-focused");
    });
  }, { rootMargin: "-28% 0px -52% 0px", threshold: 0.15 });
  cards.forEach(card => observer.observe(card));
})();
