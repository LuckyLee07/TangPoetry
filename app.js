let poems = [];

const FINAL_DATA_ROOT = "./data/final/";
const FINAL_INDEX_URL = `${FINAL_DATA_ROOT}poems/index.json`;

const FEATURED_VIEW = {
  "感遇其一|张九龄": {
    categories: ["咏怀", "高洁"],
    image: "assets/illustrations-wuyan-gushi/001-tang-001-gan-yu-qi-yi-feng-v1.png",
    mood: "开卷",
    layout: "layout-opening",
    composition: {
      poemTop: "43%",
      poemLeft: "42px",
      poemRight: "42px",
      poemAlign: "center",
      poemSize: "22px",
      poemMaxWidth: "330px",
      noteBottom: "54px"
    },
    noteTitle: "孤鸿入海，志在高远",
    note: "开篇写孤鸿远来，不恋池潢，也不畏弋者。它像一个清醒自持的人，把高洁心志托在辽阔天海之间。"
  },
  "静夜思|李白": {
    categories: ["思乡", "月夜"],
    image: "assets/illustrations-portrait/jing-ye-si.png",
    mood: "月夜",
    layout: "layout-right",
    composition: {
      poemTop: "47%",
      poemLeft: "46px",
      poemRight: "46px",
      poemAlign: "center",
      poemSize: "23px",
      poemMaxWidth: "320px",
      noteBottom: "42px"
    },
    noteTitle: "月光入室，乡心随起",
    note: "夜里的月色像霜一样铺在床前，诗人抬头看月，又低头想起远方的故乡。"
  },
  "鹿柴|王维": {
    categories: ["山水", "空山"],
    image: "assets/illustrations-portrait/lu-zhai.png",
    mood: "空山",
    layout: "layout-left",
    composition: {
      poemTop: "47%",
      poemLeft: "38px",
      poemRight: "86px",
      poemAlign: "left",
      poemSize: "22px",
      poemMaxWidth: "300px",
      noteBottom: "40px"
    },
    noteTitle: "空山有声，斜光照苔",
    note: "山中看不见人，只听见远处人声。夕阳返照进树林，又落在青青的苔痕上。"
  },
  "春晓|孟浩然": {
    categories: ["春日", "清晨"],
    image: "assets/illustrations-portrait/chun-xiao.png",
    mood: "春晨",
    layout: "layout-center",
    composition: {
      poemTop: "44%",
      poemLeft: "92px",
      poemRight: "34px",
      poemAlign: "right",
      poemSize: "22px",
      poemMaxWidth: "300px",
      noteBottom: "42px"
    },
    noteTitle: "醒来听鸟，想起落花",
    note: "春夜睡得香甜，不知不觉天已亮。醒来听见鸟鸣，想起昨夜风雨，不知吹落多少花。"
  },
  "江雪|柳宗元": {
    categories: ["山水", "冬雪", "孤寂"],
    image: "assets/illustrations-portrait/jiang-xue.png",
    mood: "寒江",
    layout: "layout-right",
    composition: {
      poemTop: "48%",
      poemLeft: "50px",
      poemRight: "50px",
      poemAlign: "center",
      poemSize: "23px",
      poemMaxWidth: "310px",
      noteBottom: "38px"
    },
    noteTitle: "天地皆白，一人独钓",
    note: "群山没有飞鸟，路上没有行人。大雪中的小船上，只有披蓑戴笠的老人独自垂钓。"
  },
  "渭城曲|王维": {
    categories: ["送别", "长亭"],
    image: "assets/illustrations-portrait/song-yuan-er.png",
    mood: "渭城",
    layout: "layout-left",
    composition: {
      poemTop: "43%",
      poemLeft: "38px",
      poemRight: "78px",
      poemAlign: "left",
      poemSize: "21px",
      poemMaxWidth: "314px",
      noteBottom: "40px"
    },
    noteTitle: "一杯酒里，都是远行",
    note: "清晨小雨洗净尘土，客舍旁的柳色分外新。临别再饮一杯，因为出了阳关就难见故人了。"
  }
};

const THEME_TEMPLATES = {
  "思乡": {
    image: "assets/illustrations-portrait/jing-ye-si.png",
    layout: "layout-center",
    mood: "思乡",
    composition: {
      poemTop: "47%",
      poemLeft: "44px",
      poemRight: "44px",
      poemAlign: "center",
      poemSize: "21px",
      poemMaxWidth: "320px",
      noteBottom: "40px"
    }
  },
  "山水": {
    image: "assets/illustrations-portrait/lu-zhai.png",
    layout: "layout-left",
    mood: "山水",
    composition: {
      poemTop: "46%",
      poemLeft: "38px",
      poemRight: "80px",
      poemAlign: "left",
      poemSize: "20px",
      poemMaxWidth: "318px",
      noteBottom: "40px"
    }
  },
  "春日": {
    image: "assets/illustrations-portrait/chun-xiao.png",
    layout: "layout-center",
    mood: "春日",
    composition: {
      poemTop: "44%",
      poemLeft: "74px",
      poemRight: "36px",
      poemAlign: "right",
      poemSize: "20px",
      poemMaxWidth: "318px",
      noteBottom: "40px"
    }
  },
  "送别": {
    image: "assets/illustrations-portrait/song-yuan-er.png",
    layout: "layout-left",
    mood: "送别",
    composition: {
      poemTop: "43%",
      poemLeft: "38px",
      poemRight: "78px",
      poemAlign: "left",
      poemSize: "20px",
      poemMaxWidth: "318px",
      noteBottom: "40px"
    }
  },
  "边塞": {
    image: "assets/illustrations-portrait/jiang-xue.png",
    layout: "layout-center",
    mood: "边塞",
    composition: {
      poemTop: "47%",
      poemLeft: "44px",
      poemRight: "44px",
      poemAlign: "center",
      poemSize: "20px",
      poemMaxWidth: "320px",
      noteBottom: "40px"
    }
  }
};

const reader = document.querySelector(".reader");
const homeScreen = document.querySelector("#homeScreen");
const startReading = document.querySelector("#startReading");
const homeLibrary = document.querySelector("#homeLibrary");
const homeFeatured = document.querySelector("#homeFeatured");
const homeCount = document.querySelector("#homeCount");
const pages = document.querySelector("#pages");
const pageMark = document.querySelector("#pageMark");
const topbar = document.querySelector(".topbar");
const bottombar = document.querySelector(".bottombar");
const library = document.querySelector("#library");
const poemList = document.querySelector("#poemList");
const favoriteButton = document.querySelector("#favoriteButton");
const featuredButton = document.querySelector("#featuredButton");
const togglePinyin = document.querySelector("#togglePinyin");
const toggleNotes = document.querySelector("#toggleNotes");
const pageDots = document.querySelector("#pageDots");
const categoryRow = document.querySelector(".category-row");

let currentIndex = 0;
let controlsVisible = false;
let homeVisible = true;
let pinyinVisible = true;
let notesVisible = true;
const favorites = new Set(JSON.parse(localStorage.getItem("tang-favorites") || "[]"));

function inferTheme(poem) {
  const text = [poem.title, poem.section, ...(poem.tags || []), poem.text || ""].join(" ");
  if (["送", "别", "赠", "辞"].some((word) => text.includes(word))) return "送别";
  if (["塞", "凉州", "从军", "玉门", "阴山", "胡马", "边塞"].some((word) => text.includes(word))) return "边塞";
  if (["春", "花", "柳", "莺", "雨"].some((word) => text.includes(word))) return "春日";
  if (["乡", "思", "忆", "故园", "故国"].some((word) => text.includes(word))) return "思乡";
  return "山水";
}

function noteFromFinal(poem) {
  const notes = poem.notes || [];
  if (!notes.length) {
    return {
      noteTitle: "诗笺",
      note: "这首诗已按《唐诗三百首》书序收录，后续可以继续补充更适合阅读页的简注。"
    };
  }
  return {
    noteTitle: "注释",
    note: notes.slice(0, 2).map((item) => item.text).join("；")
  };
}

function toViewPoem(poem) {
  const key = `${poem.title}|${poem.author}`;
  const featured = FEATURED_VIEW[key];
  const theme = featured ? featured.categories[0] : inferTheme(poem);
  const template = THEME_TEMPLATES[theme] || THEME_TEMPLATES["山水"];
  const note = featured || noteFromFinal(poem);

  return {
    id: poem.id,
    sourceIndex: poem.sourceRefs?.base?.index || poem.order,
    bookOrder: poem.order,
    bookSequence: poem.order,
    bookSection: poem.section,
    bookTitle: poem.title,
    title: poem.title,
    sourceTitle: poem.aliases?.[0] || poem.title,
    author: poem.author,
    dynasty: poem.dynasty,
    theme,
    categories: featured?.categories || [theme, ...(poem.tags || []).filter((tag) => tag !== poem.section).slice(0, 4)],
    featured: Boolean(featured),
    mood: featured?.mood || poem.visual?.mood?.[0] || template.mood,
    image: poem.visual?.image || featured?.image || template.image,
    layout: featured?.layout || template.layout,
    composition: featured?.composition || template.composition,
    lines: poem.rubyLines?.length ? poem.rubyLines : poem.displayRubyLines || [],
    plainLines: poem.lines || [],
    noteTitle: note.noteTitle,
    note: note.note,
    notes: poem.notes || [],
    source: "data/final/poems/index.json"
  };
}

async function loadFinalPoems() {
  const indexResponse = await fetch(FINAL_INDEX_URL);
  if (!indexResponse.ok) throw new Error(`index.json ${indexResponse.status}`);
  const index = await indexResponse.json();
  const entries = index.poems || [];
  const poemPayloads = await Promise.all(entries.map(async (entry) => {
    const response = await fetch(`${FINAL_DATA_ROOT}${entry.path}`);
    if (!response.ok) throw new Error(`${entry.path} ${response.status}`);
    return response.json();
  }));
  return poemPayloads
    .map((payload) => toViewPoem(payload.poem))
    .sort((left, right) => left.bookOrder - right.bookOrder);
}

function ruby(chars) {
  return chars.map(([text, pinyin]) => {
    if (!pinyin) return `<span>${text}</span>`;
    return `<ruby>${text}<rt>${pinyin}</rt></ruby>`;
  }).join("");
}

function pageVars(poem) {
  const composition = poem.composition || {};
  return [
    `--poem-top: ${composition.poemTop || "49%"}`,
    `--poem-left: ${composition.poemLeft || "34px"}`,
    `--poem-right: ${composition.poemRight || "34px"}`,
    `--poem-align: ${composition.poemAlign || "center"}`,
    `--poem-size: ${composition.poemSize || "23px"}`,
    `--poem-max-width: ${composition.poemMaxWidth || "320px"}`,
    `--note-bottom: ${composition.noteBottom || "46px"}`
  ].join("; ");
}

function renderPages() {
  pages.innerHTML = poems.map((poem, index) => `
    <article class="poem-page ${poem.layout} ${index === 0 ? "opening-page" : ""}" data-index="${index}" style="${pageVars(poem)}">
      ${index === 0 ? '<div class="opening-title">唐诗三百首</div>' : ""}
      <div class="book-ribbon">第${poem.bookOrder || poem.sourceIndex}首 · ${poem.bookSection || poem.theme}</div>
      <div class="theme-chip">${poem.mood}</div>
      <figure class="scene">
        <img src="${poem.image}" alt="${poem.title}插画" loading="${index < 2 ? "eager" : "lazy"}" decoding="async" fetchpriority="${index === 0 ? "high" : "low"}" />
      </figure>
      <div class="poem-body">
        <div class="poem-meta">
          <div class="poem-title">${poem.title}</div>
          ${poem.bookTitle && poem.bookTitle !== poem.title ? `<div class="poem-book-title">${poem.bookTitle}</div>` : ""}
          <div class="poem-author">${poem.author}</div>
        </div>
        <div class="poem-lines">
          ${poem.lines.map((line) => `<div>${ruby(line)}</div>`).join("")}
        </div>
      </div>
      <section class="note">
        <h2>${poem.noteTitle}</h2>
        <p>${poem.note}</p>
      </section>
    </article>
  `).join("");
}

function renderDots() {
  pageDots.hidden = poems.length > 30;
  pageDots.innerHTML = poems.map((poem, index) => `
    <button class="page-dot" data-index="${index}" aria-label="${poem.title}"></button>
  `).join("");
}

function renderCategories() {
  const themes = [...new Set(poems.map((poem) => poem.theme).filter(Boolean))];
  categoryRow.innerHTML = [
    '<button data-theme="all" class="active">全部</button>',
    '<button data-theme="featured">精选</button>',
    ...themes.map((theme) => `<button data-theme="${theme}">${theme}</button>`)
  ].join("");
}

function renderLibrary(theme = "all") {
  poemList.innerHTML = poems
    .map((poem, index) => ({ poem, index }))
    .filter(({ poem }) => theme === "all" || (theme === "featured" ? poem.featured : poem.theme === theme))
    .map(({ poem, index }) => `
      <button class="poem-row ${index === currentIndex ? "current" : ""}" data-index="${index}">
        <span class="poem-thumb" style="background-image: url('${poem.image}')"></span>
        <span class="poem-row-copy">
          <strong>${poem.title}</strong>
          <span>${poem.bookOrder || poem.sourceIndex}. ${poem.author} · ${poem.bookSection || poem.theme}</span>
        </span>
        <em>${favorites.has(poem.title) ? "已藏" : "翻阅"}</em>
      </button>
    `).join("");
}

function setControls(visible) {
  if (homeVisible) return;
  controlsVisible = visible;
  topbar.dataset.visible = String(visible);
  bottombar.dataset.visible = String(visible);
}

function setHome(visible) {
  homeVisible = visible;
  reader.dataset.home = String(visible);
  homeScreen.setAttribute("aria-hidden", String(!visible));
  if (visible) {
    controlsVisible = false;
    topbar.dataset.visible = "false";
    bottombar.dataset.visible = "false";
  }
}

function updateState() {
  if (!poems.length) return;
  pageMark.textContent = `${currentIndex + 1} / ${poems.length}`;
  favoriteButton.classList.toggle("active", favorites.has(poems[currentIndex].title));
  pages.classList.toggle("pinyin-off", !pinyinVisible);
  pages.classList.toggle("notes-off", !notesVisible);
  togglePinyin.classList.toggle("off", !pinyinVisible);
  toggleNotes.classList.toggle("off", !notesVisible);
  document.querySelectorAll(".poem-page").forEach((page, index) => {
    page.classList.toggle("is-current", index === currentIndex);
  });
  document.querySelectorAll(".page-dot").forEach((dot, index) => {
    dot.classList.toggle("active", index === currentIndex);
  });
  document.querySelectorAll(".poem-row").forEach((row) => {
    row.classList.toggle("current", Number(row.dataset.index) === currentIndex);
  });
}

function goTo(index) {
  currentIndex = Math.max(0, Math.min(poems.length - 1, index));
  pages.scrollTo({ left: currentIndex * pages.clientWidth, behavior: "smooth" });
  updateState();
}

function enterReader(index = currentIndex) {
  setHome(false);
  goTo(index);
}

function openLibrary() {
  library.classList.add("open");
  library.setAttribute("aria-hidden", "false");
  renderLibrary();
}

async function init() {
  try {
    poems = await loadFinalPoems();
  } catch (error) {
    console.error("Failed to load poems", error);
    pages.innerHTML = '<article class="poem-page is-current"><section class="note"><h2>诗库加载失败</h2><p>请确认 data/final/poems/index.json 和单诗文件存在，并通过本地服务打开原型。</p></section></article>';
    return;
  }
  currentIndex = 0;
  renderCategories();
  renderPages();
  renderDots();
  renderLibrary();
  homeCount.textContent = `${poems.length}首`;
  setHome(true);
  updateState();
}

pages.addEventListener("click", () => setControls(!controlsVisible));

pages.addEventListener("scroll", () => {
  const index = Math.round(pages.scrollLeft / pages.clientWidth);
  if (index !== currentIndex) {
    currentIndex = index;
    updateState();
  }
}, { passive: true });

document.querySelector("#openLibrary").addEventListener("click", (event) => {
  event.stopPropagation();
  openLibrary();
});

document.querySelector("#closeLibrary").addEventListener("click", () => {
  library.classList.remove("open");
  library.setAttribute("aria-hidden", "true");
});

library.addEventListener("click", (event) => {
  if (event.target === library) {
    library.classList.remove("open");
    library.setAttribute("aria-hidden", "true");
  }
});

poemList.addEventListener("click", (event) => {
  const row = event.target.closest(".poem-row");
  if (!row) return;
  enterReader(Number(row.dataset.index));
  library.classList.remove("open");
  library.setAttribute("aria-hidden", "true");
});

document.querySelector(".category-row").addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  document.querySelectorAll(".category-row button").forEach((item) => item.classList.remove("active"));
  button.classList.add("active");
  renderLibrary(button.dataset.theme);
  updateState();
});

favoriteButton.addEventListener("click", (event) => {
  event.stopPropagation();
  const title = poems[currentIndex].title;
  if (favorites.has(title)) {
    favorites.delete(title);
  } else {
    favorites.add(title);
  }
  localStorage.setItem("tang-favorites", JSON.stringify([...favorites]));
  updateState();
});

featuredButton.addEventListener("click", (event) => {
  event.stopPropagation();
  const index = poems.findIndex((poem) => poem.featured);
  if (index >= 0) goTo(index);
});

startReading.addEventListener("click", () => enterReader(0));

homeLibrary.addEventListener("click", (event) => {
  event.stopPropagation();
  openLibrary();
});

homeFeatured.addEventListener("click", (event) => {
  event.stopPropagation();
  const index = poems.findIndex((poem) => poem.featured);
  enterReader(index >= 0 ? index : 0);
});

togglePinyin.addEventListener("click", (event) => {
  event.stopPropagation();
  pinyinVisible = !pinyinVisible;
  updateState();
});

toggleNotes.addEventListener("click", (event) => {
  event.stopPropagation();
  notesVisible = !notesVisible;
  updateState();
});

window.addEventListener("keydown", (event) => {
  if (homeVisible && event.key === "Enter") enterReader(0);
  if (homeVisible) return;
  if (event.key === "ArrowRight") goTo(currentIndex + 1);
  if (event.key === "ArrowLeft") goTo(currentIndex - 1);
});

window.addEventListener("resize", () => goTo(currentIndex));

pageDots.addEventListener("click", (event) => {
  const dot = event.target.closest(".page-dot");
  if (!dot) return;
  event.stopPropagation();
  goTo(Number(dot.dataset.index));
});

init();
