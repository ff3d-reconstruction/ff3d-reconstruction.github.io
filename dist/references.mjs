const query = document.getElementById("reference-query");
const chapter = document.getElementById("reference-chapter");
const count = document.getElementById("reference-count");
const normalize = text => text.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
const entries = [...document.querySelectorAll(".reference-entry")].map(node => ({
  node, text: normalize(node.textContent), number: node.id.slice(4),
  chapters: node.dataset.chapters.split(" "),
}));

function filter() {
  const search = normalize(query.value.trim());
  const numeric = search.match(/^\[?(\d{1,3})\]?$/);
  let visible = 0;
  for (const entry of entries) {
    const matchesQuery = numeric ? entry.number === numeric[1] : entry.text.includes(search);
    entry.node.hidden = !(matchesQuery && (!chapter.value || entry.chapters.includes(chapter.value)));
    if (!entry.node.hidden) visible++;
  }
  count.textContent = visible === entries.length
    ? entries.length + " references"
    : visible + " of " + entries.length + " references";
}

function revealTarget() {
  const item = entries.find(entry => "#" + entry.node.id === location.hash);
  if (item?.node.hidden) {
    query.value = "";
    chapter.value = "";
    filter();
    item.node.scrollIntoView({block: "start"});
  }
}

const requested = new URLSearchParams(location.search).get("chapter");
if ([...chapter.options].some(option => option.value === requested)) chapter.value = requested;
query.addEventListener("input", filter);
chapter.addEventListener("change", filter);
window.addEventListener("hashchange", revealTarget);
filter();
revealTarget();
