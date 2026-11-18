"use strict";
/*
 * Short-drama creator desk.
 *
 * The server parses every document (GET /api/series, /api/episode,
 * /api/search); this file only lays the structures out. Markdown is the one
 * source of truth: storyboard rows can be edited in their table, and
 * 編輯原文 opens the raw text. Both save against the version opened.
 * Nothing here generates, renders or submits production; actions
 * become a sentence copied for the assistant.
 *
 * Every piece of project text is escaped before it reaches innerHTML, and
 * geometry is applied through the CSSOM (data-css), so the page runs under a
 * Content-Security-Policy without inline styles.
 */

const hasDocument = typeof document !== "undefined";
const $ = (selector, root) => (hasDocument ? (root || document).querySelector(selector) : null);
const $$ = (selector, root) => (hasDocument ? Array.from((root || document).querySelectorAll(selector)) : []);
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const local = {
  get(key, fallback) { try { const value = localStorage.getItem(`desk.${key}`); return value == null ? fallback : JSON.parse(value); } catch (_error) { return fallback; } },
  set(key, value) { try { localStorage.setItem(`desk.${key}`, JSON.stringify(value)); } catch (_error) { /* private window */ } },
};

/* ================================================================ vocabulary */

const ROOT_ROLES = {
  inputs: "sources", "輸入": "sources", "输入": "sources",
  development: "project", "專案開發": "project", "项目开发": "project",
  bible: "bible", "設定集": "bible", "设定集": "bible",
  episodes: "episodes", "劇集": "episodes", "剧集": "episodes",
};

const PATH_ALIASES = {
  "输入": "輸入", "项目开发": "專案開發", "设定集": "設定集", "剧集": "劇集",
  "审查": "審查", "制作成果": "製作成果", "创作者决策": "創作者決策", "事务": "事務", "资产": "資產",
  "剧本.md": "劇本.md", "视觉设定.md": "視覺設定.md", "分镜.md": "分鏡.md",
  "图片提示词.md": "圖片提示詞.md", "视频提示词.md": "影片提示詞.md", "剪辑单.md": "剪輯單.md",
  "剧本": "劇本", "视觉设定": "視覺設定", "分镜": "分鏡", "图片提示词": "圖片提示詞", "视频提示词": "影片提示詞", "剪辑单": "剪輯單",
  "EP001-审查.md": "EP001-審查.md",
};
const pathToken = (value) => PATH_ALIASES[String(value || "")] || PATH_ALIASES[String(value || "").toLowerCase()] || String(value || "");

const HIDDEN_ROOTS = new Set([
  ".short-drama", "creator-decisions", "創作者決策", "创作者决策", "reviews", "審查", "审查",
  "delivery", "交付", "transactions", "事務", "事务",
]);

const HIDDEN_FILES = new Set([
  "short-drama.json", "manifest.json", "coverage.json", "delivery-containers.jsonl",
  "screenplay-index.jsonl",
]);

// Reading order inside one group of files: what the creator wrote, then what was built from it.
const SECTION_ORDER = ["story", "project", "sources", "analysis", "cast", "visual", "storyboard", "prompts", "production", "review", "other"];

const CONTENT_META = {
  sources: { label: "原始資料" },
  analysis: { label: "原著分析" },
  project: { label: "專案設定" },
  cast: { label: "人物場景" },
  story: { label: "故事與劇本" },
  prompts: { label: "生成文案" },
  visual: { label: "畫面設計" },
  storyboard: { label: "分鏡畫面" },
  production: { label: "製作成果" },
  review: { label: "審查意見" },
  other: { label: "其他內容" },
};

// Which stage owns a file travels with /api/status. Path rules stay in charge;
// this map only places what they do not recognise.
const OWNER_SECTIONS = {
  "short-drama": "project",
  "short-drama-novel-analyze": "analysis",
  "short-drama-develop": "project",
  "short-drama-write": "story",
  "short-drama-assets": "cast",
  "short-drama-image-prompts": "prompts",
  "short-drama-storyboard": "storyboard",
  "short-drama-video-prompts": "prompts",
  "short-drama-produce": "production",
  "short-drama-edit": "production",
  "short-drama-breakdown": "project",
};

// Mirrors project_tool.py's EPISODE_ID_RE.
const EPISODE_ID = /^EP(?:[0-9]{3}|[1-9][0-9]{3,})$/;

// The eight things an episode can have, in the order the work runs.
const STAGES = [
  { key: "script", label: "劇本", doc: "劇本.md", name: "劇本" },
  { key: "settings", label: "設定", doc: "視覺設定.md", name: "視覺設定" },
  { key: "board", label: "分鏡", doc: "分鏡.md", name: "分鏡" },
  { key: "imgp", label: "圖片詞", doc: "圖片提示詞.md", name: "圖片提示詞" },
  { key: "vidp", label: "影片詞", doc: "影片提示詞.md", name: "影片提示詞" },
  { key: "cut", label: "剪輯", doc: "剪輯單.md", name: "剪輯單" },
  { key: "film", label: "成片", doc: "", name: "成片" },
  { key: "review", label: "審查", doc: "", name: "審查意見" },
];
const DOCUMENT_STAGES = STAGES.slice(0, 5);

// The episode workspace's views, in the stage bar's order.
const VIEWS = [
  { key: "", label: "概況" }, { key: "script", label: "劇本" }, { key: "settings", label: "設定" },
  { key: "board", label: "分鏡" }, { key: "prompts", label: "提示詞" }, { key: "film", label: "成片" },
  { key: "review", label: "審查" },
];
const VIEW_DOCS = { script: "劇本.md", settings: "視覺設定.md", board: "分鏡.md", film: "剪輯單.md", review: "review" };

// Ordered far to close. 中近景 is its own rung; the rhythm profile's 近景類
// is 近景、特寫、大特寫、細節 (the server marks each shot's `close`).
const SCALE_RUNG = { "遠景": 1, "全景": 1, "中景": 2, "中近景": 3, "近景": 4, "特寫": 5, "細節": 5, "大特寫": 6 };
const LEGACY_LABELS = { "远景": "遠景", "特写": "特寫", "大特写": "大特寫", "细节": "細節", "景别": "景別", "地点": "地點", "起始帧": "起始幀", "首帧": "首幀", "尾帧": "尾幀" };
const displayLabel = (value) => LEGACY_LABELS[String(value ?? "")] || String(value ?? "");
const isGridMedia = (item) => /grid|contact|宮格|分鏡草圖/i.test(`${item?.role || ""} ${item?.kind || ""}`);
const isShotImage = (item) => !isGridMedia(item) && (Boolean(item?.verified) || /first|start|last|end|frame|keyframe|shot[_ -]?(image|still)|首幀|尾幀|起始幀/i.test(`${item?.role || ""} ${item?.kind || ""}`));
function gridCoverage(item) {
  const ids = Array.isArray(item?.shot_ids) ? [...new Set(item.shot_ids.map(String))] : [];
  if (ids.length < 4) return ids.length ? ids.join("、") : "";
  const numeric = ids.map((id) => /(\d+)$/.exec(id)?.[1] ? Number(/(\d+)$/.exec(id)[1]) : null);
  const sorted = numeric.every(Number.isFinite) ? [...numeric].sort((a, b) => a - b) : [];
  const contiguous = sorted.length === ids.length && sorted.every((value, index) => index === 0 || value === sorted[index - 1] + 1);
  const label = contiguous ? `${ids[numeric.indexOf(sorted[0])]}–${ids[numeric.indexOf(sorted.at(-1))]}` : `${ids.length} 鏡群組`;
  return `${label} · ${ids.length} 鏡`;
}
// The primary storyboard schema is always the reader's eight-column source.
const SHOT_COLUMNS = ["編號", "畫面描述", "攝影機描述", "聲音描述", "旁白對白", "時長", "影片生成方式", "畫面prompt"];

const SEVERITY_LABEL = { must: "必須改", should: "建議改", could: "可以更好" };

const COPYABLE_PROMPT_HEADINGS = new Set(["可複製提示詞", "首幀提示詞", "尾幀提示詞"]);
const IMAGE_SUFFIXES = new Set(["png", "jpg", "jpeg", "webp", "gif"]);
const VIDEO_SUFFIXES = new Set(["mp4", "webm", "mov"]);
const AUDIO_SUFFIXES = new Set(["wav", "mp3", "m4a", "aac", "flac", "opus"]);

const INTERNAL_KEY_PARTS = [
  "hash", "sha", "path", "ref", "src", "sources", "owner", "schema", "artifact",
  "authority", "lifecycle", "manifest", "checksum", "evidence", "transaction",
  "snapshot", "candidate", "reviewer", "verdict",
];
const INTERNAL_INLINE_VALUE_PATTERNS = [
  /\b[a-f0-9]{20,128}\b/gi,
  /\bshort-drama-[a-z0-9-]+\b/gi,
  /\b(?:[a-z][a-z0-9+.-]*:\/\/|file:)[^\s，。；、）》\]]*/gi,
  /(?:\.short-drama|劇集|設定集|專案開發|輸入|創作者決策|審查|交付|事務|episodes|bible|development|inputs|creator-decisions|reviews|delivery|transactions)[\\/][^\s，。；、）》\]]*/gi,
  /(?:^|[\s(（])(?:[/\\~]|\.\.?[/\\]|[a-z]:[/\\])[^\s，。；、）》\]]*/gi,
];
const INTERNAL_WHOLE_VALUE_PATTERNS = [
  /^(?:[^\\/]+[\\/])+(?:[^\\/]+\.(?:md|txt|jsonl?|ya?ml|mp4|mov|webm|png|jpe?g|webp))$/i,
  /^(?:[^\s\\/]+\\){2,}[^\s\\/]+$/,
];
const INTERNAL_VALUE_TOKENS = new Set([
  "absent", "in_progress", "materialized", "not_run", "pass_with_warnings",
  "not_requested", "provisional", "approve_with_notes", "not_evaluated",
  "delivered", "blocked", "candidate", "artifact", "snapshot", "transaction",
  "accepted", "rejected", "reject", "approve", "ready", "pending", "revise", "stale",
  "failed", "fail", "pass",
]);
const INTERNAL_EXACT_KEYS = new Set([
  "build_state", "validation_state", "creator_acceptance", "independent_review",
  "delivery_gate", "active_transaction", "last_action", "project_root", "project_id",
]);

const FILE_LABELS = {
  "readme.md": "專案說明", "creative-brief.md": "創作簡報", "story-engine.md": "核心設定",
  "director-brief.md": "導演闡述", "adaptation-map.jsonl": "改編要點", "series-arc.json": "全劇走向",
  "episode-map.jsonl": "分集安排", "characters.jsonl": "人物設定", "looks.jsonl": "造型設定",
  "locations.jsonl": "場景設定", "location-views.jsonl": "場景視角", "props.jsonl": "關鍵道具",
  "prop-states.jsonl": "道具變化", "episode-card.json": "本集提要", "beats.jsonl": "劇情節拍",
  "screenplay.md": "劇本", "劇本.md": "劇本", "視覺設定.md": "視覺設定", "分鏡.md": "分鏡",
  "圖片提示詞.md": "圖片提示詞", "影片提示詞.md": "影片提示詞", "剪輯單.md": "剪輯單",
  "剧本.md": "劇本", "视觉设定.md": "視覺設定", "分镜.md": "分鏡", "图片提示词.md": "圖片提示詞", "视频提示词.md": "影片提示詞", "剪辑单.md": "剪輯單",
  "screenplay-index.jsonl": "場次索引", "voice-record-sheet.jsonl": "配音稿",
  "occurrences.jsonl": "出場安排", "decisions.jsonl": "畫面選擇", "continuity.jsonl": "連續性",
  "image-prompt-specs.jsonl": "圖片生成方案", "image-prompts.md": "圖片生成文案",
  "shots.jsonl": "鏡頭表", "keyframes.jsonl": "關鍵幀", "keyframe-prompts.md": "關鍵幀生成文案",
  "motion-specs.jsonl": "鏡頭運動", "video-prompts.md": "影片生成文案",
};

// The server speaks a fixed English protocol; each known message becomes a
// sentence that also says what to do next.
const FAILURE_COPY = {
  "file changed since it was opened": "這份內容在別處已經更新，請重新開啟後再修改。",
  "text file cannot be opened safely": "這份內容暫時無法開啟，請重新整理後重試。",
  "text file cannot be replaced safely": "這份內容暫時無法儲存，請重新整理後重試。",
  "file is locked or not writable": "這份檔案被其他程式佔用或不可寫；關掉正在用它的程式，或檢查檔案許可權。",
  "file is protected and read-only": "這份檔案受保護，只能閱讀。",
  "media file cannot be opened safely": "這段畫面暫時無法開啟，請重新整理後重試。",
  "file type is not editable text": "這種內容不能在創作臺裡直接修改。",
  "content exceeds file limit": "內容太長，無法儲存。",
  "file exceeds preview limit": "內容太長，無法在這裡展示。",
  "media exceeds preview limit": "這段畫面太大，無法在這裡預覽。",
  "path is not a file": "找不到這份內容，可能已被移動。",
  "media path is not a file": "找不到這段畫面，可能已被移動。",
  "project not found": "找不到這個專案。",
  "episode not found": "找不到這一集，可能已被移動或改名。",
  "unknown episode": "集號寫法不對，應當像 EP001 這樣。",
  "search query is too long": "搜尋詞太長，請縮短一些。",
  "project path changed during the save": "專案位置在儲存過程中發生變化，請重新開啟。",
  "unsupported preview media": "這種畫面格式無法在這裡預覽。",
  "request body is too large": "內容太長，無法提交。",
  "internal dashboard error": "創作臺遇到問題，請重新整理後重試。",
  "invalid dashboard response": "創作臺收到無效資料，請重新整理後重試。",
};

/* ================================================================ pure helpers */

function friendlyFailure(message) {
  return FAILURE_COPY[String(message || "").trim()] || String(message || "");
}

function creatorTitle(title) {
  return typeof title === "string" && title.trim() ? title.trim() : "未命名短劇";
}

function pathSegments(path) {
  return String(path || "").split("/").filter(Boolean);
}

function ownerSection(path, ownership) {
  const normalizedPath = pathSegments(path).map(pathToken).join("/");
  const owner = ownership?.[path] || ownership?.[normalizedPath];
  return owner ? OWNER_SECTIONS[owner] || null : null;
}

function creatorSection(path, ownership = null) {
  const parts = pathSegments(path);
  const first = pathToken(parts[0] || "");
  const lowerFirst = first.toLowerCase();
  const filename = pathToken(parts.at(-1) || "").toLowerCase();
  if (["reviews", "審查"].includes(lowerFirst) && /-(審查|审查)\.md$/.test((parts.at(-1) || "").toLowerCase())) return "review";
  if (!parts.length || HIDDEN_ROOTS.has(first) || HIDDEN_ROOTS.has(lowerFirst) || HIDDEN_ROOTS.has(parts[0])) return null;
  if (HIDDEN_FILES.has(filename)) return null;
  if (parts.length === 1) {
    if (filename === "readme.md") return "project";
    return ownerSection(path, ownership) || "other";
  }
  const root = ROOT_ROLES[first] || ROOT_ROLES[lowerFirst] || ROOT_ROLES[parts[0]] || ROOT_ROLES[String(parts[0] || "").toLowerCase()];
  if (pathToken(parts[1]) === "source-analysis") return "analysis";
  if (root === "sources" || root === "project") return root;
  if (root === "bible") return "cast";
  if (root !== "episodes") return ownerSection(path, ownership) || "other";
  const area = pathToken(parts[2] || "").toLowerCase();
  if (["production", "製作成果"].includes(area)) return "production";
  if (filename === "視覺設定.md") return "cast";
  if (filename === "分鏡.md") return "storyboard";
  if (["圖片提示詞.md", "影片提示詞.md"].includes(filename)) return "prompts";
  if (filename === "劇本.md") return "story";
  if (filename === "剪輯單.md") return "production";
  if (/prompts?\.(?:md|jsonl?)$/i.test(filename) || filename.includes("prompt")) return "prompts";
  if (["assets", "資產"].includes(area)) return "visual";
  if (["storyboard", "分鏡"].includes(area)) return "storyboard";
  return "story";
}

function creatorProjection(value) {
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (INTERNAL_VALUE_TOKENS.has(normalized) || INTERNAL_WHOLE_VALUE_PATTERNS.some((pattern) => pattern.test(value.trim()))) return undefined;
    let cleaned = value;
    for (const pattern of INTERNAL_INLINE_VALUE_PATTERNS) cleaned = cleaned.replace(pattern, "");
    cleaned = cleaned.replace(/\s{2,}/g, " ").replace(/\s+([，。；、])/g, "$1").trim();
    return cleaned || undefined;
  }
  if (value === null || typeof value !== "object") return value;
  if (Array.isArray(value)) return value.map(creatorProjection).filter((item) => item !== undefined);
  const projected = {};
  for (const [key, raw] of Object.entries(value)) {
    const normalized = String(key)
      .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
      .toLowerCase()
      .replace(/[^a-z0-9一-鿿]+/g, "_")
      .replace(/^_+|_+$/g, "");
    const keyParts = normalized.split("_").filter(Boolean);
    if (INTERNAL_EXACT_KEYS.has(normalized) || INTERNAL_KEY_PARTS.some((part) => keyParts.includes(part))) continue;
    const child = creatorProjection(raw);
    if (child !== undefined) projected[key] = child;
  }
  return projected;
}

function valueIs(axis, wanted) {
  if (typeof axis === "string") return axis === wanted;
  return Boolean(axis && typeof axis === "object" && Number(axis[wanted]) > 0);
}

function axisOnly(axis, allowed) {
  if (typeof axis === "string") return allowed.includes(axis);
  if (!axis || typeof axis !== "object") return false;
  const active = Object.entries(axis).filter(([, count]) => Number(count) > 0).map(([value]) => value);
  return active.length > 0 && active.every((value) => allowed.includes(value));
}

function creatorStatus(lifecycle, recovery = null) {
  if (!lifecycle || typeof lifecycle !== "object") return ["創作中", "neutral"];
  const simple = lifecycle.artifact_state;
  if (typeof simple === "string" || (simple && typeof simple === "object")) {
    if (valueIs(simple, "revise")) return ["需要修改", "danger"];
    if (valueIs(simple, "update_needed")) return ["需要更新", "warning"];
    if (valueIs(simple, "needs_confirmation")) return ["待你確認", "warning"];
    if (axisOnly(simple, ["approved"])) return ["可以匯出", "success"];
    if (valueIs(simple, "accepted") || valueIs(simple, "approved")) return ["已採用", "success"];
    return ["創作中", "neutral"];
  }
  if (
    valueIs(lifecycle.build_state, "failed") || valueIs(lifecycle.build_state, "fail") ||
    valueIs(lifecycle.validation_state, "failed") || valueIs(lifecycle.validation_state, "fail") ||
    valueIs(lifecycle.creator_acceptance, "rejected") || valueIs(lifecycle.independent_review, "rejected") ||
    valueIs(lifecycle.independent_review, "reject") || valueIs(lifecycle.independent_review, "revise")
  ) return ["需要修改", "danger"];
  if (recovery?.needed) return ["需要更新", "warning"];
  if (valueIs(lifecycle.build_state, "stale")) return ["需要更新", "warning"];
  if (valueIs(lifecycle.creator_acceptance, "pending")) return ["待你確認", "warning"];
  const accepted = axisOnly(lifecycle.creator_acceptance, ["accepted"]);
  const reviewed = axisOnly(lifecycle.independent_review, ["approve", "approve_with_notes", "pass"]);
  const ready = axisOnly(lifecycle.delivery_gate, ["ready", "delivered"]);
  const built = lifecycle.build_state === undefined || axisOnly(lifecycle.build_state, ["materialized"]);
  const valid = lifecycle.validation_state === undefined || axisOnly(lifecycle.validation_state, ["pass", "pass_with_warnings"]);
  if (accepted && reviewed && ready && built && valid) return ["可以匯出", "success"];
  const unfinished =
    valueIs(lifecycle.build_state, "absent") || valueIs(lifecycle.build_state, "in_progress") ||
    valueIs(lifecycle.validation_state, "not_run") || valueIs(lifecycle.independent_review, "not_requested") ||
    valueIs(lifecycle.independent_review, "provisional") || valueIs(lifecycle.delivery_gate, "not_evaluated") ||
    valueIs(lifecycle.delivery_gate, "blocked");
  if (accepted && unfinished) return ["已採用", "neutral"];
  if (accepted) return ["已採用", "success"];
  return ["創作中", "neutral"];
}

function mediaKind(fileOrPath) {
  const path = typeof fileOrPath === "string" ? fileOrPath : fileOrPath?.path;
  const suffix = String(path || "").split(".").at(-1).toLowerCase();
  if (IMAGE_SUFFIXES.has(suffix)) return "image";
  if (VIDEO_SUFFIXES.has(suffix)) return "video";
  if (AUDIO_SUFFIXES.has(suffix)) return "audio";
  return "media";
}

function formatBytes(value) {
  const bytes = Number(value) || 0;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(bytes < 10 * 1024 ? 1 : 0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(bytes < 10 * 1024 * 1024 ? 1 : 0)} MB`;
}

function savedContentIsCurrent(submitted, current) {
  return submitted === current;
}

// IDs such as SHOT-EP001-001 are how the documents cite one another, so an
// unmapped name is shown as written: same case, same hyphens.
function fileLabel(path) {
  const name = pathSegments(path).at(-1) || "內容";
  const normalized = pathToken(name);
  return FILE_LABELS[name.toLowerCase()] || FILE_LABELS[normalized.toLowerCase()] || normalized.replace(/\.(md|jsonl?|txt)$/i, "");
}

function episodeName(path) {
  const parts = pathSegments(path);
  const declared = flatten(S.tree?.tree || []).find((file) => file.path === path)?.episode;
  if (declared && isKnownEpisodeId(declared)) return declared;
  if (isKnownEpisodeId(parts[0])) return parts[0];
  const root = ROOT_ROLES[pathToken(parts[0])] || ROOT_ROLES[(pathToken(parts[0]) || "").toLowerCase()] || ROOT_ROLES[parts[0]];
  if (root === "episodes") return parts[1] || "";
  if (creatorSection(path) !== "review") return "";
  const subject = /^(.+)-(?:審查|审查)\.md$/i.exec(parts.at(-1))?.[1] || "";
  return isKnownEpisodeId(subject) ? subject : "";
}

function isKnownEpisodeId(id) {
  return EPISODE_ID.test(String(id || "")) || Boolean(S.series?.episodes?.some((row) => String(row.id) === String(id)));
}

function creatorEditable(file) {
  // Mirrors the server's TEXT_EXTENSIONS; the server rejects invalid JSON on save.
  return Boolean((file?.writable ?? file?.editable) && /\.(md|markdown|csv|txt|srt|ass|json|jsonl)$/i.test(file.path));
}

const fmt = (seconds) => {
  const total = Math.round(Number(seconds) || 0);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
};
const pct = (share) => `${Math.round((Number(share) || 0) * 100)}%`;
const num = (value) => String(+Number(value || 0).toFixed(2));
const sceneShort = (id) => String(id || "").replace(/^.*-/, "");

/** Parse `#/EP001/board/SHOT-EP001-011?scene=…` into what to show. */
function parseRoute(hash) {
  const raw = String(hash || "").replace(/^#\/?/, "");
  const [path, query] = raw.split("?");
  const parts = path.split("/").filter(Boolean).map((part) => { try { return decodeURIComponent(part); } catch (_error) { return part; } });
  const q = new URLSearchParams(query || "");
  if (parts[0] && isKnownEpisodeId(parts[0])) return { page: "episode", ep: parts[0], view: parts[1] || "", arg: parts[2] || null, q };
  if (["files", "file", "edit"].includes(parts[0])) return { page: parts[0], ep: null, view: "", arg: null, q };
  return { page: "overview", ep: null, view: "", arg: null, q };
}

/** Where a structured view of a document lives, for 返回 from its editor. */
function viewForPath(path) {
  const parts = pathSegments(path);
  const name = parts.at(-1) || "";
  const episode = episodeName(path);
  if (!episode) return "#/";
  if (/-(審查|审查)\.md$/i.test(name)) return `#/${episode}/review`;
  const view = { "劇本.md": "script", "視覺設定.md": "settings", "分鏡.md": "board", "圖片提示詞.md": "prompts/image", "影片提示詞.md": "prompts/video", "剪輯單.md": "film" }[pathToken(name)];
  return view ? `#/${episode}/${view}` : `#/${episode}`;
}

function reviewPassed(row, review = null) {
  if (!row?.has?.review) return false;
  if (Number(row?.review?.must) > 0) return false;
  if (review && Array.isArray(review.findings) && review.findings.some((item) => item.sev === "must")) return false;
  const tone = review?.verdictTone ?? row?.reviewTone;
  if (tone !== undefined && tone !== null) return tone === "ok";
  return true;
}

function reviewNeedsAttention(row, review = null) {
  return Boolean(row?.has?.review) && !reviewPassed(row, review);
}

/** The next thing an episode needs, as a sentence to hand to the assistant. */
function nextFor(row) {
  const id = row.id;
  if (row.legacy) return { kind: "legacy", rank: 6, text: "舊版格式，按原文閱讀", detail: "這一集沒有五份創作文件，創作臺只列出原檔案", ask: "", href: `#/${id}` };
  const must = row.must || [];
  if (must.length) {
    const ids = must.map((item) => item.id).join("、");
    return {
      kind: "fix", rank: 0, text: `處理 ${must.length} 條必須改的審查意見`, detail: must[0].title,
      ask: `請按 ${id} 的審查意見，先改必須改的 ${must.length} 條（${ids}）。`, href: `#/${id}/review`,
    };
  }
  if (row.has.review && row.reviewTone === "bad") {
    const redo = /重做/.test(row.reviewLabel || "");
    return {
      kind: "fix", rank: 0,
      text: redo ? "按審查結論重做這一集" : "按審查意見修改這一集",
      detail: row.reviewLabel || (redo ? "需要重做" : "需要修改"),
      ask: redo ? `請按 ${id} 的審查結論重做這一集。` : `請按 ${id} 的審查意見修改這一集。`,
      href: `#/${id}/review`,
    };
  }
  const skipImgp = Boolean(row.has.vidp || row.has.cut || row.has.film);
  const started = DOCUMENT_STAGES.some((stage) => row.has[stage.key]) || skipImgp;
  const missing = DOCUMENT_STAGES.find((stage) => !row.has[stage.key] && !(stage.key === "imgp" && skipImgp));
  if (missing) {
    return {
      kind: started ? "write" : "start", rank: started ? 1 : 5, text: `寫${missing.name}`,
      ask: `請為 ${id} 寫${missing.doc}。`, href: `#/${id}`,
    };
  }
  if (!row.has.cut && !row.has.film) return { kind: "materials", rank: 2, text: row.mediaCount ? "檢視影片素材" : "依提示詞製作影片素材", detail: "剪輯單是選用的後製旁表，不影響素材瀏覽", ask: "", href: `#/${id}/film` };
  if (row.has.cut && !row.has.film) return { kind: "render", rank: 3, text: "按剪輯單渲染成片", ask: `請按 ${id} 的剪輯單.md 渲染成片。`, href: `#/${id}/film` };
  if (!row.has.review) return { kind: "review", rank: 4, text: "審查這一集", ask: `請審查 ${id}。`, href: `#/${id}` };
  if (!reviewPassed(row)) {
    const provisional = /待補/.test(row.reviewLabel || "");
    return {
      kind: "review", rank: 4,
      text: provisional ? "補齊材料後複核審查" : "確認審查結論",
      detail: row.reviewLabel || "審查結論待確認",
      ask: provisional ? `請補齊 ${id} 待核對的材料後重新審查。` : `請核對 ${id} 的審查結論。`,
      href: `#/${id}/review`,
    };
  }
  return { kind: "done", rank: 8, text: "可以匯出", ask: `請匯出 ${id} 的完整製作資料。`, href: `#/${id}` };
}

/** Up to three next steps across the series: must-fix, then the first missing document, then editing. */
function seriesTodos(rows, limit = 3) {
  return rows
    .map((row, order) => ({ row, order, next: nextFor(row) }))
    .filter((item) => item.next.kind !== "done")
    .sort((a, b) => a.next.rank - b.next.rank || a.order - b.order)
    .slice(0, limit);
}

/** A gauge: is the measured value inside what the accepted profile allows? */
function rhythmChecks(metrics, profile, target) {
  const checks = [];
  if (target != null && metrics?.shots) {
    checks.push({ key: "seconds", label: "全集時長", value: metrics.seconds, unit: " 秒", rule: "目標", goal: target, ok: null });
  }
  if (profile?.target_avg_shot_seconds != null && metrics?.avg != null) {
    checks.push({ key: "avg", label: "平均鏡長", value: metrics.avg, unit: " 秒", rule: "目標", goal: profile.target_avg_shot_seconds, ok: null });
  }
  if (profile?.close_shot_share_min != null && metrics?.close != null) {
    checks.push({ key: "close", label: "近景類佔比", value: metrics.close, share: true, rule: "不少於", goal: profile.close_shot_share_min, ok: metrics.close >= profile.close_shot_share_min });
  }
  if (profile?.vo_share_max != null && metrics?.vo != null) {
    checks.push({ key: "vo", label: "旁白佔臺詞", value: metrics.vo, share: true, rule: "不超過", goal: profile.vo_share_max, ok: metrics.vo <= profile.vo_share_max });
  }
  return checks;
}

function rhythmProfileRows(profile) {
  if (!profile) return [];
  const rows = [];
  if (profile.form != null && profile.form !== "") rows.push(["製作形態", String(profile.form)]);
  if (profile.first_hook_seconds != null) rows.push(["第一個鉤子最遲", `${num(profile.first_hook_seconds)} 秒`]);
  if (profile.target_avg_shot_seconds != null) rows.push(["目標平均鏡長", `${num(profile.target_avg_shot_seconds)} 秒`]);
  if (profile.close_shot_share_min != null) rows.push(["近景類鏡頭不少於", pct(profile.close_shot_share_min)]);
  if (profile.vo_share_max != null) rows.push(["旁白佔臺詞不超過", pct(profile.vo_share_max)]);
  if (profile.beat_interval_seconds_max != null) rows.push(["情緒觸點最長間隔", `${num(profile.beat_interval_seconds_max)} 秒`]);
  if (profile.opposed_reversals_per_episode_min != null) rows.push(["每集至少反轉", `${profile.opposed_reversals_per_episode_min} 次`]);
  if (profile.end_on_peak != null) rows.push(["集尾停在峰值", profile.end_on_peak ? "是" : "否"]);
  if (profile.reprise_previous_last_beat != null) rows.push(["承接上集尾鉤", profile.reprise_previous_last_beat ? "是" : "否"]);
  if (profile.first_major_payoff_by_episode != null) rows.push(["第一個大爽點不晚於", `第 ${profile.first_major_payoff_by_episode} 集`]);
  return rows;
}

/** Subtitles the cut list quotes verbatim: the only line-to-shot link trusted. */
function lineShots(cuts) {
  const map = new Map();
  for (const cut of (cuts || []).filter((item) => item.shot)) {
    for (const sub of cut.subs) if (!map.has(squash(sub.text))) map.set(squash(sub.text), cut.shot);
    for (const text of cut.texts) for (const item of text.items) if (!map.has(squash(item))) map.set(squash(item), cut.shot);
  }
  return map;
}
const squash = (text) => String(text || "").replace(/\s/g, "");
function lineShot(map, text) {
  const key = squash(text);
  if (map.has(key)) return map.get(key);
  for (const [line, shot] of map) if (line && key.includes(line)) return shot;
  return null;
}

/* ================================================================ Markdown */

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function button(text, className, action) {
  const node = element("button", className, text);
  node.onclick = action;
  return node;
}

function appendInlineText(node, text) {
  const tokens = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g).filter(Boolean);
  for (const token of tokens) {
    if (token.startsWith("`") && token.endsWith("`")) node.append(element("code", "", token.slice(1, -1)));
    else if (token.startsWith("**") && token.endsWith("**")) node.append(element("strong", "", token.slice(2, -2)));
    else node.append(document.createTextNode(token));
  }
}

// What a copy button copies is the block's source text -- quote markers
// removed, lines joined by newlines -- not the rendering.
function copyablePrompt(block) {
  const wrapper = element("div", "copy-block");
  const control = button("複製", "copy-button", () => copyPrompt(control, block));
  control.type = "button";
  control.dataset.copyText = "";
  wrapper.append(block, control);
  return { wrapper, control };
}

async function writeClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (_error) {
    const scratch = element("textarea", "clipboard-scratch");
    scratch.value = text;
    scratch.setAttribute("readonly", "");
    document.body.append(scratch);
    scratch.select();
    let copied = false;
    try { copied = document.execCommand("copy"); } catch (_ignored) { copied = false; }
    scratch.remove();
    return copied;
  }
}

async function copyPrompt(control, block) {
  const copied = await writeClipboard(control.dataset.copyText);
  control.focus({ preventScroll: true });
  if (copied) {
    control.textContent = "已複製";
    control.dataset.state = "copied";
    setTimeout(() => { control.textContent = "複製"; delete control.dataset.state; }, 1600);
    return;
  }
  const range = document.createRange();
  range.selectNodeContents(block);
  getSelection().removeAllRanges();
  getSelection().addRange(range);
  toast("無法直接寫入剪貼簿，已選中這段提示詞，請按 ⌘/Ctrl + C 複製。");
}

function renderMarkdown(content) {
  const normalized = String(content || "").replace(/^\ufeff/, "").replace(/\r\n?/g, "\n");
  const fragment = document.createDocumentFragment();
  let list = null;
  let listKind = null;
  let fence = null;
  // Consecutive `>` lines are one blockquote: a copyable prompt is written that way on purpose.
  let quoteNode = null;
  let copyable = false;
  let quoteCopy = null;
  // Markdown comments hold creator notes; closed ones are dropped, an
  // unterminated one is rendered verbatim rather than eating the document.
  let comment = null;
  const closeList = () => { list = null; listKind = null; };
  const closeQuote = () => { quoteNode = null; quoteCopy = null; };
  const paragraph = (text) => {
    const node = element("p");
    appendInlineText(node, text);
    fragment.append(node);
  };
  const appendQuoteLine = (text) => {
    if (quoteNode) quoteNode.append(element("br"));
    else {
      quoteNode = element("blockquote");
      if (copyable) {
        const { wrapper, control } = copyablePrompt(quoteNode);
        quoteCopy = { control, lines: [] };
        fragment.append(wrapper);
      } else {
        fragment.append(quoteNode);
      }
    }
    appendInlineText(quoteNode, text);
    if (quoteCopy) {
      quoteCopy.lines.push(text);
      quoteCopy.control.dataset.copyText = quoteCopy.lines.join("\n");
    }
  };
  const codeBlock = (lines) => {
    const pre = element("pre", "code-block");
    pre.append(element("code", "", lines.join("\n")));
    if (!copyable) { fragment.append(pre); return; }
    const { wrapper, control } = copyablePrompt(pre);
    control.dataset.copyText = lines.join("\n");
    fragment.append(wrapper);
  };
  for (let line of normalized.split("\n")) {
    if (fence !== null) {
      if (fence.closeRe.test(line)) { codeBlock(fence.lines); fence = null; } else fence.lines.push(line);
      continue;
    }
    if (comment !== null) {
      const closeAt = line.indexOf("-->");
      if (closeAt === -1) { comment.push(line); continue; }
      comment = null;
      line = line.slice(closeAt + 3);
      if (!line.trim()) { closeQuote(); continue; }
    }
    const fenceOpen = /^\s*(`{3,}|~{3,})/.exec(line);
    if (fenceOpen) {
      closeList();
      closeQuote();
      const ch = fenceOpen[1][0];
      fence = { closeRe: new RegExp(`^\\s*${ch}{${fenceOpen[1].length},}\\s*$`), lines: [] };
      continue;
    }
    if (copyable) {
      const copyQuote = /^>\s?(.*)$/.exec(line);
      if (copyQuote) {
        closeList();
        appendQuoteLine(copyQuote[1]);
        continue;
      }
    }
    let stripped = line;
    for (let previous = null; previous !== stripped;) {
      previous = stripped;
      stripped = stripped.replace(/<!--[\s\S]*?-->/g, "");
    }
    const openAt = stripped.indexOf("<!--");
    if (openAt !== -1) {
      closeList();
      closeQuote();
      const before = stripped.slice(0, openAt);
      if (before.trim()) paragraph(before);
      comment = [stripped.slice(openAt)];
      continue;
    }
    if (stripped !== line) {
      if (!stripped.trim()) { if (!quoteCopy) closeQuote(); continue; }
      line = stripped;
    }
    const heading = /^(#{1,6})\s+(.+)$/.exec(line);
    if (heading) {
      closeList();
      closeQuote();
      const node = element(`h${heading[1].length}`);
      appendInlineText(node, heading[2]);
      fragment.append(node);
      copyable = COPYABLE_PROMPT_HEADINGS.has(heading[2].trim());
      continue;
    }
    const bullet = /^[-*]\s+(.+)$/.exec(line);
    const ordered = /^\d+[.)]\s+(.+)$/.exec(line);
    if (bullet || ordered) {
      closeQuote();
      const kind = bullet ? "ul" : "ol";
      if (!list || listKind !== kind) { list = element(kind); listKind = kind; fragment.append(list); }
      const node = element("li");
      appendInlineText(node, (bullet || ordered)[1]);
      list.append(node);
      continue;
    }
    closeList();
    if (!line.trim()) { if (!quoteCopy) closeQuote(); continue; }
    const quote = /^>\s?(.*)$/.exec(line);
    if (quote) {
      appendQuoteLine(quote[1]);
      continue;
    }
    closeQuote();
    paragraph(line);
  }
  if (comment !== null) for (const line of comment) paragraph(line);
  if (fence !== null && fence.lines.length) codeBlock(fence.lines);
  return fragment;
}

// A half-written file must still preview: one truncated record from an
// interrupted agent run should not hide every valid record around it.
function readJsonLines(content) {
  return String(content || "").replace(/^\ufeff/, "").replace(/\r\n?/g, "\n").split("\n").map((line, index) => ({ line: index + 1, text: line.trim() })).filter((row) => row.text).map((row) => {
    try { return { line: row.line, record: JSON.parse(row.text) }; }
    catch (error) { return { line: row.line, error: error.message, text: row.text }; }
  });
}

function friendlyKey(key) {
  const labels = {
    id: "編號", name: "名稱", title: "標題", description: "說明", summary: "概要",
    character: "人物", character_id: "人物編號", location: "場景", location_id: "場景編號",
    dialogue: "臺詞", action: "動作", prompt: "生成文案", role: "作用", type: "型別",
    episode_id: "劇集", scene_id: "場次", shot_id: "鏡頭", beat_id: "劇情節拍",
    objective: "目標", conflict: "衝突", turn: "轉折", emotion: "情緒", relationship: "關係",
    costume: "服裝", prop: "道具", props: "道具", lighting: "光線", camera: "攝影",
    composition: "構圖", duration: "時長", start_boundary: "開始畫面", end_boundary: "結束畫面",
    boundary_role: "畫面位置", continuity_state: "連續性", notes: "備註", value: "內容",
  };
  const normalized = String(key).toLowerCase().replace(/-/g, "_");
  if (labels[normalized]) return labels[normalized];
  if (/[一-鿿]/.test(String(key))) return String(key).replace(/[_-]/g, " ");
  return String(key).replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/[_-]+/g, " ").trim() || "補充資訊";
}

function appendStructuredValue(node, value) {
  if (Array.isArray(value)) {
    if (!value.length) { node.textContent = "—"; return; }
    const list = element("ul");
    for (const item of value) { const row = element("li"); appendStructuredValue(row, item); list.append(row); }
    node.append(list);
    return;
  }
  if (value && typeof value === "object") {
    const entries = Object.entries(value);
    if (!entries.length) { node.textContent = "—"; return; }
    const list = element("dl");
    for (const [key, child] of entries) {
      const detail = element("dd");
      appendStructuredValue(detail, child);
      list.append(element("dt", "", friendlyKey(key)), detail);
    }
    node.append(list);
    return;
  }
  node.textContent = value === null || value === "" ? "—" : String(value);
}

function structuredCard(value, index) {
  const card = element("article", "structured-card");
  const projected = creatorProjection(value);
  if (projected === undefined || projected === null || typeof projected !== "object") {
    card.append(element("p", "", projected === undefined ? "暫無可展示內容" : String(projected)));
    return card;
  }
  if (index !== null) card.append(element("span", "record-number", `第 ${index + 1} 項`));
  const list = element("dl");
  for (const [key, raw] of Object.entries(projected)) {
    const detail = element("dd");
    appendStructuredValue(detail, raw);
    list.append(element("dt", "", friendlyKey(key)), detail);
  }
  if (!list.childNodes.length) list.append(element("dt", "", "內容"), element("dd", "", "暫無可展示內容"));
  card.append(list);
  return card;
}

function renderDocument(path, content) {
  const host = element("div", "doc");
  try {
    if (/\.html?$/i.test(path)) host.append(element("pre", "source-html", content));
    else if (/\.md$/i.test(path)) host.append(renderMarkdown(content));
    else if (/\.json$/i.test(path)) host.append(structuredCard(JSON.parse(content), null));
    else if (/\.jsonl$/i.test(path)) {
      readJsonLines(content)
        .filter((row) => !(row.record && typeof row.record === "object" && row.record.record_type === "sources"))
        .forEach((row, index) => host.append(row.error
          ? element("p", "preview-warning", `第 ${row.line} 項內容還不完整，暫時無法展示。`)
          : structuredCard(row.record, index)));
    } else host.append(element("pre", "", content));
  } catch (_error) {
    host.replaceChildren(element("p", "preview-warning", "這份內容還不完整，暫時無法展示。"));
  }
  return host;
}

/* ================================================================ icons */

const IC = {
  search: '<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/>',
  left: '<path d="m14.5 6-6 6 6 6"/>', right: '<path d="m9.5 6 6 6-6 6"/>', down: '<path d="m6 9.5 6 6 6-6"/>',
  close: '<path d="M6 6l12 12M18 6 6 18"/>', check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
  copy: '<rect x="8.5" y="8.5" width="11" height="11" rx="2"/><path d="M15.5 8.5V6a1.5 1.5 0 0 0-1.5-1.5H6A1.5 1.5 0 0 0 4.5 6v8A1.5 1.5 0 0 0 6 15.5h2.5"/>',
  edit: '<path d="M4.5 19.5h4l10-10a2.1 2.1 0 0 0-4-4l-10 10v4Z"/><path d="m13.5 6.5 4 4"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M2.5 12h2M19.5 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"/>',
  moon: '<path d="M19.5 14.5A8 8 0 0 1 9.5 4.5a8 8 0 1 0 10 10Z"/>',
  play: '<path d="M8 5.5v13l10.5-6.5L8 5.5Z"/>',
  voice: '<path d="M12 4.5a3 3 0 0 0-3 3v4a3 3 0 0 0 6 0v-4a3 3 0 0 0-3-3Z"/><path d="M6 11.5a6 6 0 0 0 12 0M12 17.5v2.5"/>',
  sfx: '<path d="M5 13v-2M9 16V8M13 19V5M17 16V8M21 13v-2"/>',
  text: '<rect x="3.5" y="5.5" width="17" height="13" rx="2"/><path d="M8 10h8M8 14h5"/>',
  lock: '<rect x="5.5" y="10.5" width="13" height="9" rx="2"/><path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5"/>',
  alert: '<path d="M12 4 2.8 19.5h18.4L12 4Z"/><path d="M12 10v4.5M12 17.2v.3"/>',
  film: '<rect x="4.5" y="3.5" width="15" height="17" rx="2"/><path d="M4.5 8h15M4.5 16h15M9 3.5v4.5M15 3.5v4.5M9 16v4.5M15 16v4.5"/>',
  place: '<path d="M12 20.5s-6-5.2-6-10a6 6 0 0 1 12 0c0 4.8-6 10-6 10Z"/><circle cx="12" cy="10.5" r="2.2"/>',
  prop: '<path d="M7 7.5h10l-1 12H8l-1-12Z"/><path d="M9.5 7.5V5.5h5v2"/>',
  person: '<circle cx="12" cy="8.5" r="3.5"/><path d="M5 19.5c1.2-3.4 3.9-5 7-5s5.8 1.6 7 5"/>',
  list: '<path d="M9 6.5h11M9 12h11M9 17.5h11M4.5 6.5h.01M4.5 12h.01M4.5 17.5h.01"/>',
  grid: '<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>',
  doc: '<path d="M7 3.5h7l4 4v13H7z"/><path d="M14 3.5v4h4M9.5 12h6M9.5 15.5h6"/>',
  media: '<rect x="3.5" y="5.5" width="17" height="13" rx="2"/><path d="m10 9.5 4.5 2.5-4.5 2.5z"/>',
};
const icon = (name, cls = "i") => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${IC[name] || ""}</svg>`;
const fillIcon = (name) => icon(name, "i fill");

/* ================================================================ state */

const S = {
  apiBase: "",
  token: "",
  projects: [],
  project: null,
  series: null,
  tree: null,
  status: null,
  episodes: new Map(),
  theme: local.get("theme", "auto"),
  layout: local.get("layout", "cards"),
  reviewFilter: "all",
  copied: new Set(),
  edit: null,
  lastHash: "",
  renderSequence: 0,
  pendingLine: null,
  palette: { sel: 0, items: [], scope: "ep", timer: null, sequence: 0 },
};

async function api(path, options) {
  const requestPath = S.apiBase && path.startsWith("/api/") ? `${S.apiBase}${path}` : path;
  const headers = new Headers(options?.headers || {});
  if (S.token) headers.set("X-Film-Token", S.token);
  const response = await fetch(requestPath, { ...options, headers, credentials: "same-origin" });
  let data;
  try { data = await response.json(); } catch (_error) { throw new Error("invalid dashboard response"); }
  if (!response.ok) {
    const error = new Error((data && data.error) || `HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return data;
}

async function establishSession() {
  const raw = location.hash.startsWith("#") ? location.hash.slice(1) : "";
  const hashParams = new URLSearchParams(raw.startsWith("/") ? (raw.split("?")[1] || "") : raw);
  let token = hashParams.get("token") || "";
  try { token ||= sessionStorage.getItem("film.token") || ""; } catch (_error) { /* private window */ }
  if (!token) throw new Error("缺少本機工作階段權杖，請從工作臺重新開啟。");
  try { sessionStorage.setItem("film.token", token); } catch (_error) { /* private window */ }
  S.token = token;
  const response = await fetch("/api/session", { method: "POST", headers: { "X-Film-Token": token }, credentials: "same-origin" });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  if (typeof data.apiBase !== "string") throw new Error("本機工作階段回應無效");
  S.apiBase = data.apiBase;
  const route = raw.startsWith("/") ? raw : "/";
  history.replaceState(null, "", `${location.pathname}${location.search}#${route}`);
}

const query = (params) => new URLSearchParams(params).toString();
const mediaUrl = (path) => `${S.apiBase}/api/media/content?${query({ project: S.project, path })}`;

function flatten(nodes, out = []) {
  for (const node of nodes || []) {
    if (node.type === "directory") flatten(node.children, out);
    else out.push(node);
  }
  return out;
}

async function loadProject(id) {
  const [series, tree] = await Promise.all([
    api(`/api/series?${query({ project: id })}`),
    api(`/api/tree?${query({ project: id })}`),
  ]);
  S.project = id;
  S.series = series;
  S.tree = tree;
  S.files = flatten(tree.tree);
  S.episodes = new Map();
  S.copied = new Set(local.get(`copied.${id}`, []));
  local.set("project", id);
}

async function loadEpisode(ep) {
  if (S.episodes.has(ep)) return S.episodes.get(ep);
  // A save may swap S.episodes while this request is in flight; return what was read, not the new empty cache.
  const raw = await api(`/api/episode?${query({ project: S.project, ep })}`);
  const docs = { ...(raw.docs || {}) };
  const docAliases = [["劇本.md", "剧本.md"], ["視覺設定.md", "视觉设定.md"], ["分鏡.md", "分镜.md"], ["圖片提示詞.md", "图片提示词.md"], ["影片提示詞.md", "视频提示词.md"], ["剪輯單.md", "剪辑单.md"]];
  for (const [traditional, simplified] of docAliases) {
    if (!docs[traditional] && docs[simplified]) docs[traditional] = docs[simplified];
    if (!docs[simplified] && docs[traditional]) docs[simplified] = docs[traditional];
  }
  const data = {
    ...raw,
    docs,
    metrics: raw.metrics || {},
    media: { frames: {}, clips: {}, ...(raw.media || {}) },
    board: raw.board ? { ...raw.board, shots: (raw.board.shots || []).map((shot) => ({
      ...shot,
      fields: shot.fields || {},
      supplement: shot.supplement || {},
      basis: shot.basis || [],
      refs: shot.refs || [],
      imgs: shot.imgs || [],
    })) } : raw.board,
  };
  S.episodes.set(ep, data);
  return data;
}

async function refreshProject() {
  const project = S.project;
  const [series, tree] = await Promise.all([
    api(`/api/series?${query({ project })}`),
    api(`/api/tree?${query({ project })}`),
  ]);
  if (S.project !== project) return;
  S.series = series;
  S.tree = tree;
  S.files = flatten(tree.tree);
  S.episodes = new Map();
}

/* ================================================================ chrome */

const rowById = (id) => S.series?.episodes.find((row) => row.id === id) || null;
const target = () => S.series?.format?.target_seconds_per_episode || null;
const isDark = () => S.theme === "dark" || (S.theme === "auto" && typeof matchMedia === "function" && matchMedia("(prefers-color-scheme: dark)").matches);

function applyTheme() {
  if (S.theme === "auto") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.dataset.theme = S.theme;
}

function renderTop(route) {
  const rows = S.series?.episodes || [];
  // A raw document or its editor still sits inside its episode.
  const crumbEp = route.ep || episodeName(route.q.get("path") || "");
  const row = crumbEp ? rowById(crumbEp) : null;
  const index = row ? rows.indexOf(row) : -1;
  const title = creatorTitle(S.series?.title);
  const project = S.projects.length > 1
    ? `<select id="projectSelect" aria-label="選擇短劇專案">${S.projects.map((item) => `<option value="${esc(item.id)}" ${item.id === S.project ? "selected" : ""}>《${esc(creatorTitle(item.title))}》</option>`).join("")}</select>`
    : `<span class="t">《${esc(title)}》</span>`;
  const viewKey = route.page === "episode" ? route.view : "";
  $("#topbar").innerHTML = `
    <a class="zs-mark" href="#/" aria-label="回到全劇">場</a>
    <nav class="crumbs" aria-label="位置">
      ${S.projects.length > 1 ? `<span class="crumb proj">${project}</span>` : `<a class="crumb proj" href="#/">${project}${row ? "" : '<span class="s">全劇</span>'}</a>`}
      ${row ? `<span class="crumb-sep hide-s">/</span>
        <button class="crumb" id="epMenuBtn" type="button" aria-haspopup="true"><span class="t mono">${esc(row.id)}</span><span class="s">${esc(row.title || "未命名")}</span>${icon("down")}</button>
        <button class="step-btn" type="button" data-go="#/${esc(rows[index - 1]?.id || "")}/${esc(viewKey)}" ${index > 0 ? "" : "disabled"} aria-label="上一集">${icon("left")}</button>
        <button class="step-btn" type="button" data-go="#/${esc(rows[index + 1]?.id || "")}/${esc(viewKey)}" ${index >= 0 && index < rows.length - 1 ? "" : "disabled"} aria-label="下一集">${icon("right")}</button>` : ""}
    </nav>
    <span class="spacer"></span>
    <button class="search-trigger" type="button" data-act="search" aria-label="搜尋">${icon("search")}<span>搜尋臺詞、鏡頭、設定…</span><kbd>⌘K</kbd></button>
    <button class="icon-btn theme-btn" type="button" data-act="theme" aria-label="${isDark() ? "切換到淺色" : "切換到深色"}">${icon(isDark() ? "sun" : "moon")}</button>`;
  const bar = $("#stagebar");
  bar.hidden = !(route.page === "episode" && row) || Boolean(row?.legacy);
  if (bar.hidden) { bar.innerHTML = ""; return; }
  const E = S.episodes.get(row.id);
  const meta = stageMeta(row, E);
  const dot = (key) => {
    if (!key) return "";
    const state = stageState(row, key);
    return `<i class="dot ${state}" aria-hidden="true"></i>`;
  };
  bar.innerHTML = VIEWS.map((view, i) => `${i > 1 ? '<span class="tab-sep"></span>' : ""}<a class="tab" data-stage="${view.key || "home"}" href="#/${esc(row.id)}${view.key ? `/${view.key}` : ""}" ${route.view === view.key ? 'aria-current="page"' : ""}>${dot(view.key)}<span class="lbl">${view.label}</span>${meta[view.key] ? `<span class="meta">${esc(meta[view.key])}</span>` : ""}</a>`).join("");
  const current = $(".tab[aria-current]", bar);
  if (current) bar.scrollLeft = Math.max(0, current.offsetLeft - bar.clientWidth / 2 + current.clientWidth / 2);
}

function stageState(row, key) {
  if (key === "review") return !row.has.review ? "" : reviewPassed(row) ? "on" : "warn";
  if (key === "prompts") return row.has.imgp && row.has.vidp ? "on" : "";
  if (key === "film") return row.has.film ? "on" : "";
  return row.has[key] ? "on" : "";
}

function stageMeta(row, E) {
  const findings = row.review.must + row.review.should + row.review.could;
  const prompts = E ? (E.imagePrompts?.length || 0) + (E.videoPrompts?.length || 0) : null;
  return {
    "": "",
    script: row.has.script ? (E?.script ? `${E.script.scenes.length} 場` : "已寫") : "未寫",
    settings: row.has.settings ? (E?.settings ? `${E.settings.items.length} 項` : "已寫") : "未寫",
    board: row.has.board ? `${row.shots || "—"} 鏡` : "未寫",
    prompts: row.has.imgp || row.has.vidp ? (prompts != null ? `${prompts} 條` : "已寫") : "未寫",
    film: row.has.film ? fmt(row.cutSeconds || row.seconds) : row.has.cut ? "未渲染" : row.mediaCount ? `${row.mediaCount} 份素材` : "素材待製作",
    review: row.has.review ? (findings ? `${findings} 條` : "已審") : "無",
  };
}

function episodeMenu(anchor) {
  closeMenus();
  const route = parseRoute(location.hash);
  const menu = document.createElement("div");
  menu.className = "menu";
  menu.id = "epMenu";
  menu.innerHTML = (S.series?.episodes || []).map((row) => `<a href="#/${esc(row.id)}/${esc(route.view)}" ${row.id === route.ep ? 'aria-current="true"' : ""}><span class="menu-id">${esc(row.id)}</span><span class="menu-t">${esc(row.title || "未開始")}</span>${pips(row)}</a>`).join("");
  const box = anchor.getBoundingClientRect();
  menu.dataset.css = `left:${Math.max(8, Math.min(box.left, innerWidth - 300))}px;top:${box.bottom + 6}px`;
  document.body.append(menu);
  applyCss(menu.parentNode);
}
const closeMenus = () => $$(".menu").forEach((menu) => menu.remove());

function pips(row) {
  return `<span class="pips" aria-hidden="true">${STAGES.map((stage) => `<i class="${stage.key === "review" ? (!row.has.review ? "" : reviewPassed(row) ? "on" : "warn") : row.has[stage.key] ? "on" : ""}"></i>`).join("")}</span>`;
}

/* ================================================================ shared bits */

function copyButton(text, key, label = "複製") {
  const done = key && S.copied.has(key);
  return `<button class="btn sm ${done ? "done" : ""}" type="button" data-copy="${esc(text)}" ${key ? `data-key="${esc(key)}"` : ""}>${icon(done ? "check" : "copy")}${done ? "已複製" : label}</button>`;
}
function askButton(ask, primary = true, label = "複製給助手") {
  if (!ask) return "";
  return `<button class="btn sm ${primary ? "primary" : ""}" type="button" data-copy="${esc(ask)}" data-copy-label="已複製，去對話裡傳送">${icon("copy")}${label}</button>`;
}
/** Distance from a target value, stated without judging it: the profile gives the target, not a tolerance. */
function gapText(value, goal) {
  const d = Math.round((value - goal) * 10) / 10;
  return d === 0 ? "與目標相同" : `${d > 0 ? "多" : "少"} ${num(Math.abs(d))} 秒`;
}
const gap = (value, goal) => `<span class="status">${esc(gapText(value, goal))}</span>`;
function statusMark(ok, words = ["符合", "偏離"]) {
  return `<span class="status ${ok ? "ok" : "warn"}">${icon(ok ? "check" : "alert")}${ok ? words[0] : words[1]}</span>`;
}
function fieldHTML(value) {
  return esc(value ?? "未提供").replace(/&lt;br\s*\/?&gt;/gi, "<br>");
}
function problemNotices(E) {
  const resolution = E.sourceResolution || {};
  const sourceInfo = resolution.primary && resolution.alternatives?.length ? `<div class="notice source-info" role="note"><span>分鏡主表：${esc(fileLabel(resolution.primary))}；保留 ${resolution.alternatives.length} 份其他輸出供對照。${resolution.resolved === false ? "主表宣告尚待確認，請核對來源。" : resolution.conflicts?.length ? "來源差異可在單鏡詳情查看。" : "已核對為相同內容，序列化表示差異不視為錯誤。"}</span></div>` : "";
  return sourceInfo + [...new Set(E.problems || [])].map((problem) => `<div class="notice" role="note">${icon("alert")}<span>${esc(problem)}</span></div>`).join("");
}
function editButton(path, at = "", label = "編輯原文", cls = "btn") {
  if (!path) return "";
  const back = (typeof location !== "undefined" && location.hash) || "#/";
  return `<a class="${cls}" href="#/edit?${esc(query({ path, ...(at ? { at } : {}), back }))}">${icon("edit")}${label}</a>`;
}
function missingView(row, what) {
  const stage = { script: "劇本", settings: "視覺設定", board: "分鏡", prompts: "提示詞", film: "剪輯單", review: "審查意見" }[what];
  const ask = what === "film" ? `請為 ${row.id} 寫剪輯單.md。` : what === "review" ? `請審查 ${row.id}。` : what === "prompts" ? `請為 ${row.id} 寫圖片提示詞.md 和影片提示詞.md。` : `請為 ${row.id} 寫${stage}.md。`;
  return `<div class="wrap"><div class="empty"><h3>${esc(row.id)} 還沒有${stage}</h3><p>在和助手的對話裡開始這一步；寫好後回到這裡就能看到。</p><button class="btn primary" type="button" data-copy="${esc(ask)}" data-copy-label="已複製，去對話裡傳送">${icon("copy")}複製給助手：${esc(ask)}</button></div></div>`;
}
function rawFallback(E, path, heading) {
  return `<div class="wrap"><div class="head"><div><h2>${esc(heading)}</h2><div class="sub">按原文顯示</div></div><div class="actions">${editButton(path)}</div></div>${problemNotices(E)}<div data-raw="${esc(path)}"><div class="loading">正在讀取原文…</div></div></div>`;
}

/* ================================================================ episode context */

/** A still's 「運鏡」 as the cut list writes it: 固定, or 推近 6%. */
const moveLabel = (cut) => (!cut.move || cut.move.kind === "固定" ? "固定" : cut.move.rate != null ? `${cut.move.kind} ${cut.move.rate}%/秒` : `${cut.move.kind} ${cut.move.amount}%`);

function context(E) {
  const shots = E.board?.shots || [];
  const cuts = E.cutlist?.cuts || [];
  const clipByShot = {};
  for (const cut of cuts) {
    if (!E.media.clips[cut.id]) continue;
    const targets = Array.isArray(cut.group_shots) && cut.group_shots.length ? cut.group_shots : cut.shot ? [cut.shot] : [];
    for (const shotId of targets) if (!clipByShot[shotId]) clipByShot[shotId] = { path: E.media.clips[cut.id], cut };
  }
  const promptByShot = Object.fromEntries((E.videoPrompts || []).flatMap((prompt) => [...new Set([prompt.shot, ...(prompt.shot_ids || [])].filter(Boolean))].map((id) => [id, prompt])));
  return {
    E,
    shots,
    shot: Object.fromEntries(shots.map((shot) => [shot.id, shot])),
    total: shots.reduce((sum, shot) => sum + shot.sec, 0),
    cuts,
    cutTotal: E.cutlist?.seconds || 0,
    scenes: E.script?.scenes || [],
    findings: E.review?.findings || [],
    profile: S.series?.rhythm || null,
    target: target(),
    clipByShot,
    promptByShot,
    lines: lineShots(cuts),
    frame: (shot) => E.media.frames[shot.id] || null,
  };
}
const findingsFor = (C, id) => C.findings.filter((finding) => finding.targets.includes(id));
const placeOf = (C, sceneId) => C.scenes.find((scene) => scene.id === sceneId)?.place || "";

function thumb(C, shot, withSeconds = true) {
  const frame = C.frame(shot);
  const clip = C.clipByShot[shot.id];
  const ratio = aspectRatioCss(S.series?.format?.aspect_ratio);
  return `<div class="thumb" ${ratio ? `data-css="aspect-ratio:${ratio}"` : ""}>${frame ? `<img src="${esc(mediaUrl(frame))}" alt="${esc(shot.title)} 起始幀" loading="lazy">` : '<div class="thumb-missing">尚無單鏡影像</div>'}${clip ? `<span class="clip" title="已有素材">${fillIcon("play")}</span>` : ""}${withSeconds ? `<span class="sec">${esc(num(shot.sec))}s</span>` : ""}</div>`;
}

/* ================================================================ overview */

function aspectLabel(ratio) {
  const r = String(ratio || "").trim();
  if (!r) return "";
  const match = /^(\d+(?:\.\d+)?)\s*[:：/]\s*(\d+(?:\.\d+)?)$/.exec(r);
  if (!match) return `畫幅 ${r}`;
  const w = Number(match[1]);
  const h = Number(match[2]);
  if (!(w > 0 && h > 0)) return `畫幅 ${r}`;
  if (w < h) return `豎屏 ${r}`;
  if (w > h) return `橫屏 ${r}`;
  return `方畫幅 ${r}`;
}

function aspectRatioCss(value) {
  const match = /^(\d+(?:\.\d+)?)\s*[:：/×x]\s*(\d+(?:\.\d+)?)$/.exec(String(value || "").trim());
  if (!match) return "";
  const width = Number(match[1]);
  const height = Number(match[2]);
  return width > 0 && height > 0 ? `${width} / ${height}` : "";
}

function viewOverview() {
  const series = S.series;
  const rows = series.episodes;
  const count = series.format.episode_count || rows.length;
  const perEpisode = target();
  const [statusLabel] = creatorStatus(series.lifecycle);
  const withStage = (key) => rows.filter((row) => row.has[key]).length;
  const cut = rows.filter((row) => row.has.film || row.has.cut).reduce((sum, row) => sum + (row.cutSeconds || 0), 0);
  const whole = perEpisode ? count * perEpisode : 0;
  const todos = seriesTodos(rows);
  const meta = [aspectLabel(series.format.aspect_ratio), `${count} 集`, perEpisode ? `每集目標 ${perEpisode} 秒` : ""].filter(Boolean);
  const kpi = (label, value, of, unit) => `<div class="card kpi"><div class="k">${label}</div><div class="v">${value}<small>/ ${of} ${unit}</small></div><div class="bar"><i data-css="width:${of ? Math.min(100, (value / of) * 100) : 0}%"></i></div></div>`;
  const profile = series.rhythm;
  const projectFiles = (S.files || []).filter((file) => !episodeName(file.path) && creatorSection(file.path, S.status?.ownership));
  return `<div class="wrap" data-view="overview">
  <section class="hero">
    <div class="hero-t">
      <div class="eyebrow">全劇 · ${esc(statusLabel)}</div>
      <h1>《${esc(creatorTitle(series.title))}》</h1>
      <div class="meta">${meta.map((item) => `<span>${esc(item)}</span>`).join("")}</div>
      <div class="kpis">
        ${kpi("劇本", withStage("script"), count, "集")}
        ${kpi("分鏡", withStage("board"), count, "集")}
        ${kpi("成片", withStage("film"), count, "集")}
        <div class="card kpi"><div class="k">${whole ? "已剪時長 / 全劇目標" : "已剪時長"}</div><div class="v">${fmt(cut)}${whole ? `<small>/ ${fmt(whole)}</small>` : ""}</div><div class="bar"><i data-css="width:${whole ? Math.min(100, (cut / whole) * 100) : 0}%"></i></div></div>
      </div>
    </div>
    <div class="card next" id="nextSteps">
      <div class="eyebrow">下一步</div>
      ${todos.length ? todos.map((item, i) => `<div class="todo" data-ep="${esc(item.row.id)}"><span class="num ${i ? "soft" : ""}">${i + 1}</span><div><div class="t"><span class="mono">${esc(item.row.id)}</span> · ${esc(item.next.text)}</div><div class="d">${esc(todoDetail(item.row, item.next))}</div></div>
        <div class="acts">${askButton(item.next.ask, i === 0)}<a class="btn sm ghost" href="${esc(item.next.href)}">開啟</a></div></div>`).join("") : `<div class="todo"><span class="num">✓</span><div><div class="t">${rows.length ? "每一集都走完了" : "還沒有分集"}</div><div class="d">${rows.length ? "可以在對話裡請助手匯出。" : "在對話裡請助手建立第一集。"}</div></div></div>`}
      <p class="foot">創作臺只讀寫 Markdown。寫作、生成、渲染都在和助手的對話裡確認。</p>
    </div>
  </section>

  <div class="section-t"><h3>分集進度</h3><span class="n">${rows.length} 集 · 點一行進入該集</span></div>
  ${rows.length ? `<div class="card matrix-wrap"><table class="matrix">
    <thead>
      <tr><th colspan="2"></th><th class="group" colspan="5">五份創作文件</th><th class="group" colspan="2">後期</th><th colspan="3"></th></tr>
      <tr><th>集</th><th>集名</th>${STAGES.map((stage) => `<th class="c">${stage.label}</th>`).join("")}<th>時長 / 目標</th><th>下一步</th></tr>
    </thead>
    <tbody>${rows.map((row) => {
      const next = nextFor(row);
      const dim = !DOCUMENT_STAGES.some((stage) => row.has[stage.key]) && !row.legacy;
      return `<tr data-go="#/${esc(row.id)}" data-episode="${esc(row.id)}" class="${dim ? "dim" : ""}"><td class="ep"><a href="#/${esc(row.id)}">${esc(row.id)}</a></td><td class="ttl">${esc(row.title || (row.legacy ? "舊版格式" : "未開始"))}</td>
      ${STAGES.map((stage) => { const warn = stage.key === "review" && reviewNeedsAttention(row); const on = row.has[stage.key]; const warnNote = row.review.must ? "：有必須改的意見" : `：${row.reviewLabel || "審查未透過"}`;
        return `<td><div class="cell"><span class="pip ${warn ? "warn" : on ? "on" : ""}" title="${stage.label}${warn ? esc(warnNote) : on ? "：已有" : "：還沒有"}" data-stage="${stage.key}" data-on="${on ? 1 : 0}">${warn ? icon("alert") : on ? icon("check") : ""}<span class="sr-only">${stage.label}${warn ? esc(warnNote) : on ? "：已有" : "：還沒有"}</span></span></div></td>`; }).join("")}
      <td>${row.seconds ? `<div class="dur"><span class="mono">${fmt(row.cutSeconds || row.seconds)}</span>${perEpisode ? `<span class="bar"><i data-css="width:${Math.min(100, ((row.cutSeconds || row.seconds) / (perEpisode * 1.25)) * 100)}%"></i><span class="tgt" data-css="left:80%"></span></span>` : ""}</div>` : '<span class="muted">—</span>'}</td>
      <td class="nextcell">${dim ? '<span class="muted">未開始</span>' : next.kind === "fix" ? `<b>${esc(next.text)}</b>` : esc(next.text)}</td></tr>`; }).join("")}</tbody>
  </table></div>
  <div class="ep-cards">${rows.map((row) => { const next = nextFor(row);
    return `<a class="card ep-card" href="#/${esc(row.id)}" data-episode="${esc(row.id)}"><div class="r1"><span class="ep">${esc(row.id)}</span><span class="ttl">${esc(row.title || "未開始")}</span>${row.review.must ? `<span class="revdot">${icon("alert")}${row.review.must} 必須改</span>` : reviewNeedsAttention(row) ? `<span class="revdot">${icon("alert")}${esc(row.reviewLabel || "待複核")}</span>` : ""}</div>
    <div class="segs" aria-hidden="true">${STAGES.map((stage) => `<i class="${stage.key === "review" ? (!row.has.review ? "" : reviewPassed(row) ? "on" : "warn") : row.has[stage.key] ? "on" : ""}"></i>`).join("")}</div>
    <div class="r3"><span>${STAGES.filter((stage) => row.has[stage.key]).length}/8 · ${row.seconds ? fmt(row.cutSeconds || row.seconds) : "—"}</span><span>${esc(next.kind === "done" ? "可以匯出" : next.text)}</span></div></a>`; }).join("")}</div>` : `<div class="empty"><h3>還沒有分集</h3><p>分集建立在「劇集/EP001」這樣的資料夾裡。</p></div>`}

  <div class="twocol">
    <div><div class="section-t"><h3>節奏目標</h3><span class="n">${profile ? "已確認 · 分鏡與審查按它核對" : "尚未設定"}</span></div>
      ${(() => { const pRows = rhythmProfileRows(profile); return pRows.length ? `<div class="card profile">${pRows.map(([key, value]) => `<div class="row"><span class="k">${key}</span><span class="v">${esc(value)}</span></div>`).join("")}</div>`
      : `<div class="empty"><p>還沒有設定節奏目標，暫不對照平均鏡長、近景類與旁白佔比。</p>${askButton("請為這部劇提出節奏目標，我確認後寫入專案。", false, "複製給助手")}</div>`; })()}</div>
    <div><div class="section-t"><h3>人物</h3><span class="n">來自各集視覺設定</span></div>
      ${series.cast.length ? `<div class="card cast">${series.cast.map((person) => `<a class="person" href="#/${esc(person.ep)}/settings/${encodeURIComponent(settingKey("人物", person.name))}"><span class="tile">${esc(person.name[0] || "?")}</span><div><div class="pn">${esc(person.name)}</div><div class="pd">${esc(person.desc)}</div><div class="pd">${esc(person.ep)} · ${person.shots == null ? "尚無明示鏡號關聯" : `${person.shots} 鏡`}</div></div></a>`).join("")}</div>` : '<div class="empty"><p>視覺設定寫好後，人物會列在這裡。</p></div>'}</div>
  </div>

  <div class="section-t"><h3>專案檔案</h3><span class="n">${projectFiles.length} 份</span><a class="more" href="#/files">全部檔案 →</a></div>
  ${projectFiles.length ? `<div class="card files-list">${projectFiles.slice(0, 8).map(fileRow).join("")}</div>` : '<p class="muted small">專案層面還沒有其他檔案。</p>'}
</div>`;
}

function todoDetail(row, next) {
  if (next.kind === "fix" || next.kind === "legacy" || (next.kind === "review" && next.detail)) return next.detail || "";
  const done = DOCUMENT_STAGES.filter((stage) => row.has[stage.key]).map((stage) => stage.label);
  return done.length ? `已有：${done.join("、")}` : "還沒有任何文件";
}

function fileRow(file) {
  const kind = file.type === "media" ? "media" : "doc";
  const section = CONTENT_META[creatorSection(file.path, S.status?.ownership)]?.label || "";
  return `<a class="file-row" href="#/file?${esc(query({ path: file.path }))}">${icon(kind)}<span><div class="fn">${esc(fileLabel(file.path))}</div><div class="fk">${esc([episodeName(file.path), section].filter(Boolean).join(" · "))}</div></span><span class="muted small">${file.type === "media" ? esc(formatBytes(file.size)) : ""}</span></a>`;
}

/* ================================================================ episode home */

function viewEpisode(row, E) {
  const C = context(E);
  const next = nextFor(row);
  const counts = { must: 0, should: 0, could: 0 };
  C.findings.forEach((finding) => counts[finding.sev]++);
  const spoken = C.scenes.flatMap((scene) => scene.blocks).filter((block) => block.k === "line").length;
  const facts = {
    script: E.script ? `${C.scenes.length} 場 · ${spoken} 句臺詞${E.metrics.vo != null ? ` · 旁白 ${pct(E.metrics.vo)}` : ""}` : "按原文閱讀",
    settings: E.settings ? `${E.settings.items.length} 項${E.settings.era.period ? ` · 時代：${E.settings.era.period}` : ""}` : "按原文閱讀",
    board: E.board ? `${C.shots.length} 鏡 · ${num(C.total)} 秒${E.metrics.avg != null ? ` · 平均 ${num(E.metrics.avg)} 秒` : ""}` : "按原文閱讀",
    prompts: `圖片 ${E.imagePrompts?.length ?? "—"} 條 · 影片 ${E.videoPrompts?.length ?? "—"} 條`,
    film: E.cutlist ? `${C.cuts.length} 段 · ${fmt(C.cutTotal)}${E.media.film ? " · 已渲染成片" : " · 未渲染"}` : E.media.film ? "已有成片" : "按原文閱讀",
    review: E.review ? `${E.review.verdict || "已寫"} · 必須改 ${counts.must} · 建議改 ${counts.should}` : "按原文閱讀",
  };
  const docRows = [
    ["script", "劇本", row.has.script, "劇本.md"],
    ["settings", "視覺設定", row.has.settings, "視覺設定.md"],
    ["board", "分鏡", row.has.board, "分鏡.md"],
    ["prompts", "提示詞", row.has.imgp || row.has.vidp, row.has.imgp && row.has.vidp ? "圖片提示詞.md · 影片提示詞.md" : row.has.imgp ? "圖片提示詞.md" : "影片提示詞.md"],
    ["film", "剪輯與成片", row.has.cut || row.has.film, "剪輯單.md"],
    ["review", "審查", row.has.review, "審查意見"],
  ];
  const checks = rhythmChecks(E.metrics, C.profile, C.target);
  const others = (S.files || []).filter((file) => episodeName(file.path) === row.id && !isStageDocument(file.path));
  const still = C.shots.map((shot) => C.frame(shot)).find(Boolean);
  const aspectCss = aspectRatioCss(S.series?.format?.aspect_ratio);
  const posterStyle = aspectCss ? `data-css="aspect-ratio:${aspectCss}"` : "";
  const poster = E.media.film
    ? `<div class="poster has-media ${aspectCss ? "has-aspect" : "natural"}" ${posterStyle}><video src="${esc(mediaUrl(E.media.film))}#t=0.5" ${still ? `poster="${esc(mediaUrl(still))}"` : ""} preload="metadata" muted playsinline aria-label="成片畫面"></video><a class="btn primary play" href="#/${esc(row.id)}/film">${fillIcon("play")}播放成片 ${fmt(C.cutTotal || 0)}</a></div>`
    : C.shots.find((shot) => C.frame(shot))
      ? `<div class="poster has-media ${aspectCss ? "has-aspect" : "natural"}" ${posterStyle}><img src="${esc(mediaUrl(C.frame(C.shots.find((shot) => C.frame(shot)))))}" alt="起始幀"><a class="btn play" href="#/${esc(row.id)}/film">還沒有成片</a></div>`
      : `<div class="poster empty-poster"><span class="ph-note">還沒有成片。剪輯單寫好、渲染之後會在這裡播放。</span></div>`;
  return `<div class="wrap" data-view="episode"><div class="ephome">
    <div>${poster}</div>
    <div>
      <div class="head"><div><div class="eyebrow">${esc(row.id)}</div><h2 class="serif">${esc(row.title || "未命名")}</h2><div class="sub">${[C.scenes.length ? `${C.scenes.length} 場` : "", C.shots.length ? `${C.shots.length} 鏡` : "", C.shots.length ? `${num(C.total)} 秒${C.target != null ? `（目標 ${C.target} 秒）` : ""}` : ""].filter(Boolean).join(" · ") || "還沒有正文"}</div></div></div>
      ${problemNotices(E)}
      ${next.kind !== "done" ? `<div class="card next"><div class="todo"><span class="num">!</span><div><div class="t">${esc(next.text)}</div><div class="d">${esc(todoDetail(row, next))}</div></div>
        <div class="acts">${askButton(next.ask)}${next.href !== `#/${row.id}` ? `<a class="btn sm" href="${esc(next.href)}">去看</a>` : ""}</div></div></div>` : ""}
      ${checks.length ? `<div class="section-t"><h3>對照節奏目標</h3><span class="n">僅核對數值，供創作參考</span></div><div class="gauges">${checks.map((check) => gauge(check, C)).join("")}</div>` : ""}
      <div class="section-t"><h3>本集文件</h3></div>
      <div class="card pipeline">${docRows.map(([key, name, present, doc]) => {
        const revWarn = key === "review" && (counts.must > 0 || !reviewPassed(row, E.review));
        return present
          ? `<a class="pl-row" href="#/${esc(row.id)}/${key}"><span class="pip ${revWarn ? "warn" : "on"}">${revWarn ? icon("alert") : icon("check")}</span><span><div class="nm">${name}</div><div class="muted small">${esc(doc)}</div></span><span class="fx">${esc(facts[key])}</span><span class="go">${icon("right")}</span></a>`
          : `<a class="pl-row" href="#/${esc(row.id)}/${key}"><span class="pip"></span><span><div class="nm">${name}</div><div class="muted small">${esc(doc)}</div></span><span class="fx muted">還沒有</span><span class="go">${icon("right")}</span></a>`;
      }).join("")}</div>
      ${others.length ? `<div class="section-t"><h3>本集其他檔案</h3><span class="n">${others.length} 份</span></div><div class="card files-list">${others.map(fileRow).join("")}</div>` : ""}
    </div></div></div>`;
}

function isStageDocument(path) {
  const parts = pathSegments(path);
  return parts.length === 3 && ["劇本.md", "視覺設定.md", "分鏡.md", "圖片提示詞.md", "影片提示詞.md", "剪輯單.md"].includes(pathToken(parts[2])) || /-(審查|审查)\.md$/i.test(parts.at(-1) || "");
}

function viewLegacyEpisode(row) {
  const files = (S.files || []).filter((file) => episodeName(file.path) === row.id && creatorSection(file.path));
  return `<div class="wrap" data-view="episode"><div class="head"><div><div class="eyebrow">${esc(row.id)}</div><h2 class="serif">${esc(row.title || row.id)}</h2><div class="sub">這一集是舊版格式，按原文閱讀</div></div></div>
    <div class="card files-list">${files.map(fileRow).join("") || '<p class="muted small">沒有可讀的檔案。</p>'}</div></div>`;
}

function gauge(check, C) {
  const share = Boolean(check.share);
  const value = share ? pct(check.value) : num(check.value);
  const goal = share ? pct(check.goal) : `${num(check.goal)} 秒`;
  let max, fill, zone, tick, foot;
  if (check.key === "seconds") {
    max = check.goal * 1.3; fill = check.value / max; zone = [check.goal * 0.9 / max, check.goal * 1.1 / max]; tick = check.goal / max;
    const diff = check.value - check.goal;
    foot = `${diff >= 0 ? "比目標多" : "比目標少"} ${num(Math.abs(diff))} 秒（綠區為 ±10% 參考帶）`;
  } else if (check.key === "avg") {
    max = Math.max(check.goal * 2, check.value * 1.2); fill = check.value / max; zone = [(check.goal - 0.5) / max, (check.goal + 0.5) / max]; tick = check.goal / max;
    foot = `當前平均每鏡 ${num(check.value)} 秒（綠區為 ±0.5 秒參考帶）`;
  } else if (check.key === "close") {
    fill = check.value; zone = [check.goal, 1]; tick = check.goal;
    foot = `${C.E.metrics.closeCount || 0} / ${C.shots.length} 鏡；${C.E.metrics.unsized} 鏡景別未辨識或複合`;
  } else {
    fill = check.value; zone = [0, check.goal]; tick = check.goal;
    foot = "按實際念出聲的字數算；[OS] 畫外對白不計入旁白";
  }
  const clamp = (x) => Math.max(0, Math.min(100, x * 100));
  return `<div class="card gauge" data-gauge="${check.key}" ${check.ok == null ? "" : ` data-ok="${check.ok ? 1 : 0}"`}><div class="k"><span>${check.label}</span>${check.ok == null ? gap(check.value, check.goal) : statusMark(check.ok)}</div>
    <div class="v">${value}<small>${share ? "" : "秒 · "}${check.rule} ${goal}</small></div>
    <div class="bullet" role="img" aria-label="${esc(`${check.label} ${value}，${check.rule} ${goal}`)}"><span class="zone" data-css="left:${clamp(zone[0])}%;width:${clamp(zone[1]) - clamp(zone[0])}%"></span><span class="fill" data-css="width:${clamp(fill)}%"></span><span class="tick" data-css="left:${clamp(tick)}%"></span></div>
    <div class="foot">${esc(foot)}</div></div>`;
}

/* ================================================================ script */

function viewScript(row, E, arg) {
  if (!row.has.script) return missingView(row, "script");
  if (!E.script) return rawFallback(E, E.docs["劇本.md"], "劇本");
  const C = context(E);
  const speakers = {};
  for (const block of C.scenes.flatMap((scene) => scene.blocks)) if (block.k === "line") speakers[block.who] = (speakers[block.who] || 0) + 1;
  const most = Math.max(1, ...Object.values(speakers));
  const shotsIn = (id) => C.shots.filter((shot) => shot.scene === id);
  const mark = (text) => {
    const shot = lineShot(C.lines, text);
    return shot ? `<a class="shotref" href="#/${esc(row.id)}/board/${esc(shot)}" title="在第 ${esc(sceneShort(shot))} 鏡">${icon("film")}${esc(sceneShort(shot))}</a>` : "";
  };
  const block = (b) => {
    if (b.k === "action") return `<p class="blk action">${esc(b.text)}</p>`;
    if (b.k === "line") return `<div class="dlg ${b.tag === "VO" ? "vo" : ""}" data-line="${esc(b.text)}"><div class="who">${esc(b.who)}${b.tag ? `<span class="tag ${b.tag.toLowerCase()}">${b.tag === "VO" ? "旁白 VO" : "畫外 OS"}</span>` : ""}${mark(b.text)}</div>${b.paren ? `<div class="paren">（${esc(b.paren)}）</div>` : ""}<div class="said">${esc(b.text)}</div></div>`;
    if (b.tag === "畫面文字") return `<div class="onscreen" data-line="${esc(b.text)}"><span class="lab">畫面文字 · 後期疊加</span>${esc(b.text)}${mark(b.text)}</div>`;
    return `<div class="sfx" data-line="${esc(b.text)}"><span class="tag">${esc(b.tag === "SFX" ? "音效" : b.tag)}</span><span>${esc(b.text)}</span></div>`;
  };
  const sceneFindings = C.findings.filter((finding) => finding.targets.some((id) => /SC\d+$/.test(id)));
  return `<div class="wrap" data-view="script">${problemNotices(E)}<div class="script">
    <aside class="rail left"><div><h4>場次</h4>${C.scenes.map((scene) => { const shots = shotsIn(scene.id);
      return `<a class="scene-link" href="#/${esc(row.id)}/script/${esc(scene.id)}" ${arg === scene.id ? 'aria-current="true"' : ""}><div class="id">${esc(sceneShort(scene.id))}</div><div class="pl">${esc(scene.place)}</div><div class="m">${esc(scene.space)} · ${esc(scene.time)}${shots.length ? ` · ${shots.length} 鏡 · ${num(shots.reduce((sum, shot) => sum + shot.sec, 0))} 秒` : ""}</div></a>`; }).join("")}</div>
      <div class="card legend-list"><div><span class="tag vo">旁白 VO</span>內心或旁白</div><div><span class="tag os">畫外 OS</span>人在畫外說話</div><div><span class="tag plain">音效</span>[SFX]</div><div><span class="stxt">畫面文字</span>後期疊加的字</div><div><span class="shotref">${icon("film")}005</span>這句在第幾鏡（按剪輯單字幕）</div></div>
    </aside>
    <article class="page" aria-label="劇本">
      <div class="page-bar"><span class="mono">劇本.md</span><span>· 按劇本格式排版</span><span class="actions">${editButton(E.docs["劇本.md"], "", "編輯原文", "btn sm")}</span></div>
      <h1>${esc(E.script.title || row.title || row.id)}</h1>
      ${C.scenes.map((scene) => `<div class="slug" id="${esc(scene.id)}"><span class="id">${esc(sceneShort(scene.id))}</span><span class="pl">${esc(scene.space)} · ${esc(scene.place)} · ${esc(scene.time)}</span>${shotsIn(scene.id).length ? `<a class="go btn sm ghost" href="#/${esc(row.id)}/board?scene=${esc(scene.id)}">${shotsIn(scene.id).length} 鏡 ${icon("right")}</a>` : ""}</div>${scene.blocks.map(block).join("")}`).join("")}
    </article>
    <aside class="rail right">
      <div><h4>臺詞</h4><div class="card speakers">${Object.entries(speakers).sort((a, b) => b[1] - a[1]).map(([who, n]) => `<div class="spk"><span>${esc(who)}</span><span class="bar"><i data-css="width:${(n / most) * 100}%"></i></span><span class="c">${n}</span></div>`).join("") || '<span class="muted small">沒有臺詞</span>'}</div></div>
      ${C.profile?.vo_share_max != null && E.metrics.vo != null ? `<div><h4>旁白佔比</h4>${gauge(rhythmChecks(E.metrics, C.profile, null).find((check) => check.key === "vo"), C)}</div>` : ""}
      ${sceneFindings.length ? `<div><h4>本劇本的審查意見</h4>${sceneFindings.map((finding) => `<a class="card rail-card" href="#/${esc(row.id)}/review/${esc(finding.id)}"><span class="tag ${finding.sev}">${SEVERITY_LABEL[finding.sev]}</span><div class="t">${esc(finding.title)}</div></a>`).join("")}</div>` : ""}
    </aside></div></div>`;
}

/* ================================================================ storyboard */

function stripHTML(C, row, selected, keep) {
  let cursor = 0;
  const bars = C.shots.map((shot) => {
    const rung = SCALE_RUNG[displayLabel(shot.scale)];
    const on = !keep || keep(shot);
    const tip = `${shot.title} · ${num(shot.sec)}s · ${displayLabel(shot.scale) || "景別未辨識或複合"}`;
    cursor += shot.sec;
    return `<button class="sb ${rung ? `s${rung}` : "unsized"} ${selected === shot.id ? "sel" : ""} ${on ? "" : "dim"}" type="button" data-css="flex-grow:${Math.max(0.2, shot.sec)}" data-shot="${esc(shot.id)}" data-tip-b="${esc(shot.n)}" data-tip="${esc(tip)}" aria-label="${esc(`${shot.n} ${tip}`)}">${shot.close ? '<span class="cl"></span>' : ""}${esc(String(Number(shot.n) || shot.n))}</button>`;
  }).join("");
  const total = C.total || 1;
  const scenes = [];
  let acc = 0;
  let last = null;
  for (const shot of C.shots) { if (shot.scene !== last) { scenes.push([shot.scene, acc]); last = shot.scene; } acc += shot.sec; }
  const ticks = [];
  const step = total > 120 ? 20 : 10;
  for (let x = 0; x <= total + 0.001; x += step) ticks.push(`<span data-css="left:${(x / total) * 100}%">${x}s</span>`);
  const goal = C.target;
  return `<div class="strip"><div class="strip-scenes">${scenes.map(([id, x], i) => `<span data-css="left:${(x / total) * 100}%;width:${(((scenes[i + 1]?.[1] ?? total) - x) / total) * 100}%">${esc(sceneShort(id) || "未寫場次")}<em> ${esc(placeOf(C, id))}</em></span>`).join("")}</div>
    <div class="strip-bars">${bars}</div>
    ${goal && goal <= total ? `<div class="strip-target" data-css="left:${(goal / total) * 100}%"><b>目標 ${goal}s</b></div>` : ""}
    <div class="strip-axis">${ticks.join("")}</div></div>
    <div class="legend">${[["遠景/全景", 1], ["中景", 2], ["中近景", 3], ["近景", 4], ["特寫/細節", 5], ["大特寫", 6]].map(([label, rung]) => `<span><i class="s${rung}"></i>${label}</span>`).join("")}<span><i class="hatch"></i>景別未辨識或複合</span><span><span class="cl-key"></span>頂部短線 = 近景類</span></div>`;
}

function soundFlags(C, shot) {
  const cut = C.cuts.find((item) => item.shot === shot.id || (Array.isArray(item.group_shots) && item.group_shots.includes(shot.id)));
  const flags = [];
  if (cut?.subs.length || /臺詞|對白|一句|VO|OS/.test(shot.sound)) flags.push(`<span class="flag" title="有臺詞">${icon("voice")}臺詞</span>`);
  if ((shot.screenText && !/^無/.test(shot.screenText)) || cut?.texts.length) flags.push(`<span class="flag" title="有畫面文字">${icon("text")}畫面文字</span>`);
  if (cut?.sfx.length) flags.push(`<span class="flag" title="有音效">${icon("sfx")}音效</span>`);
  return flags.join("");
}

/** 場景站位: the staging a scene's shots inherit, shown as written. */
function blockingRows(block) {
  return `<dl class="blocking-dl">${block.rows.map(([key, value]) => `<dt>${esc(key)}</dt><dd>${esc(value)}</dd>`).join("")}</dl>`;
}

function blockingHTML(blocks) {
  if (!blocks.length) return "";
  return `<div class="blocking" id="boardBlocking">${blocks.map((block) => `<section class="card blocking-card" data-scene="${esc(block.scene)}"><h3>場景站位 · ${esc(sceneShort(block.scene))}${block.place ? ` ${esc(block.place)}` : ""}</h3>${blockingRows(block)}</section>`).join("")}</div>`;
}

function viewBoard(row, E, arg, q) {
  const editTable = boardTableButton(row, E);
  if (!row.has.board && !editTable) return missingView(row, "board");
  if (!E.board && editTable) return `<div class="wrap"><div class="head"><h2>分鏡</h2><div class="actions">${editTable}${editButton(E.docs["分鏡.md"])}</div></div>${problemNotices(E)}<p>分鏡表目前沒有鏡頭。</p></div>`;
  if (!E.board) return rawFallback(E, E.docs["分鏡.md"], "分鏡");
  const C = context(E);
  const sceneFilter = q.get("scene") || null;
  const entityFilter = q.get("entity") || null;
  const parsedEntity = parseSettingKey(entityFilter);
  const keep = (shot) => (!sceneFilter || shot.scene === sceneFilter) && (!entityFilter || shot.basis.some((entry) => entry.name === parsedEntity.name && (!parsedEntity.cat || categoryKey(entry.cat) === categoryKey(parsedEntity.cat))));
  const list = C.shots.filter(keep);
  const note = sceneFilter ? `場次 ${sceneShort(sceneFilter)}` : entityFilter ? `出現「${parsedEntity.cat ? `${parsedEntity.cat} · ${parsedEntity.name}` : parsedEntity.name}」` : "";
  const M = E.metrics;
  const P = C.profile;
  const metric = (label, value, rule, ok) => `<div class="card gauge"><div class="k"><span>${label}</span>${ok === null ? "" : statusMark(ok, ["符合", "留意"])}</div><div class="v">${value}</div><div class="rule">${esc(rule)}</div></div>`;
  const qs = location.hash.includes("?") ? `?${location.hash.split("?")[1]}` : "";
  const fromAlternative = (shot) => E.sourceResolution?.primary && shot.source && shot.source !== E.sourceResolution.primary;
  const alternativeLabel = (shot) => fromAlternative(shot) ? `<span class="tag plain" title="${esc(shot.source)}">對照來源</span>` : "";
  const cards = list.map((shot) => { const found = findingsFor(C, shot.id);
    return `<article class="card shot ${arg === shot.id ? "sel" : ""}" data-shot="${esc(shot.id)}" id="c-${esc(shot.id)}" tabindex="0" aria-label="${esc(`${shot.n} ${shot.title}`)}">
      ${thumb(C, shot)}
      <div><div class="hd"><span class="no">${esc(shot.n)}</span><span class="tt">${esc(shot.title)}</span>${alternativeLabel(shot)}</div>
        <div class="pills"><span class="pill">${esc(displayLabel(shot.scale) || "景別未辨識或複合")}</span>${shot.moveKind ? `<span class="pill">${fieldHTML(shot.moveKind)}</span>` : ""}<span class="pill">${esc(num(shot.sec))} 秒</span></div>
        <div class="chain"><div><b>起</b><span>${fieldHTML(shot.start)}</span></div><div><b>動</b><span>${fieldHTML(shot.action)}</span></div><div><b>終</b><span>${fieldHTML(shot.end)}</span></div></div>
        <div class="sndrow">${soundFlags(C, shot)}</div></div>
      ${found.length ? `<span class="rev"><span class="revdot ${found[0].sev === "must" ? "" : found[0].sev}">${icon("alert")}${found.length}</span></span>` : ""}
    </article>`; }).join("");
  const rows = list.map((shot) => `<tr data-shot="${esc(shot.id)}" class="${arg === shot.id ? "sel" : ""}">${SHOT_COLUMNS.map((column, index) => `<td>${fieldHTML(shot.fields?.[column])}${index === 0 ? alternativeLabel(shot) : ""}</td>`).join("")}</tr>`).join("");
  return `<div class="wrap" data-view="board">
  <div class="head"><div><h2>分鏡</h2><div class="sub">${C.shots.length} 鏡 · ${num(C.total)} 秒${C.scenes.length ? ` · ${C.scenes.length} 場` : ""}</div></div>
    <div class="actions"><div class="seg" role="group" aria-label="佈局"><button type="button" data-layout="cards" aria-pressed="${S.layout === "cards"}">${icon("grid")} 卡片</button><button type="button" data-layout="list" aria-pressed="${S.layout === "list"}">${icon("list")} 列表</button></div>
    ${editTable}${editButton(E.docs["分鏡.md"])}</div></div>
  ${problemNotices(E)}
  ${E.board.note ? `<p class="muted small" id="boardNote">${esc(E.board.note)}</p>` : ""}
  ${blockingHTML((E.board.blocking || []).filter((block) => !sceneFilter || block.scene === sceneFilter))}
  <div class="metrics" id="boardMetrics">
    ${metric("總時長", `${num(C.total)}<small> 秒</small>`, C.target != null ? `目標 ${C.target} 秒 · ${gapText(C.total, C.target)}` : "沒有設每集目標", null)}
    ${metric("平均鏡長", M.avg != null ? `${num(M.avg)}<small> 秒</small>` : "—", P?.target_avg_shot_seconds != null && M.avg != null ? `目標 ${num(P.target_avg_shot_seconds)} 秒 · ${gapText(M.avg, P.target_avg_shot_seconds)}` : "沒有設定節奏目標", null)}
    ${metric("近景類", M.close != null ? pct(M.close) : "—", P?.close_shot_share_min != null ? `不少於 ${pct(P.close_shot_share_min)}` : "沒有設定節奏目標", P?.close_shot_share_min != null && M.close != null ? M.close >= P.close_shot_share_min : null)}
    ${metric("景別未辨識或複合", `${M.unsized}<small> 鏡</small>`, "算不進近景類佔比", M.unsized === 0)}
  </div>
  <section class="card strip-card"><div class="strip-head"><h3>節奏條</h3><span class="muted small">寬度 = 時長，顏色 = 景別；點一格看這一鏡</span></div>${stripHTML(C, row, arg, sceneFilter || entityFilter ? keep : null)}</section>
  <div class="board-tools"><div class="pills">${[null, ...C.scenes.map((scene) => scene.id)].map((id) => `<a class="pill ${sceneFilter === id && !entityFilter ? "on" : ""}" href="#/${esc(row.id)}/board${id ? `?scene=${esc(id)}` : ""}">${id ? `${esc(sceneShort(id))} ${esc(placeOf(C, id))}` : "全部"}</a>`).join("")}</div>
    ${note ? `<span class="filter-note">篩選：${esc(note)} · ${list.length} 鏡 <a class="pill" href="#/${esc(row.id)}/board">${icon("close")}清除</a></span>` : ""}</div>
    ${list.length ? (S.layout === "cards" ? `<div class="shots">${cards}</div>` : `<div class="card table-card"><table class="shot-table"><thead><tr>${SHOT_COLUMNS.map((column) => `<th>${esc(column)}</th>`).join("")}</tr></thead><tbody>${rows}</tbody></table></div>`) : '<div class="empty"><p>沒有符合篩選的鏡頭。</p></div>'}
  <span hidden data-query="${esc(qs)}"></span>
  </div>`;
}

const boardEditorHref = (ep, path = "") => `#/${ep}/board?${query({ editTable: path })}`;
const boardSources = (E) => [E.sourceResolution?.primary, ...(E.sourceResolution?.alternatives || [])].filter(Boolean);
const markdownSource = (path) => /\.(md|markdown)$/i.test(path);

function boardTableButton(row, E) {
  const sources = boardSources(E);
  if (!sources.some(markdownSource)) return "";
  return `<a class="btn primary" href="${esc(boardEditorHref(row.id, sources.length === 1 ? sources[0] : ""))}">${icon("edit")}編輯表格</a>`;
}

function viewBoardEditor(row, E, path) {
  const sources = boardSources(E);
  const isSource = sources.includes(path) && markdownSource(path);
  const sourceLabel = (source) => source === E.sourceResolution?.primary
    ? (E.sourceResolution.resolved === false ? "（暫用來源）" : "（主表）") : "（對照來源）";
  const menu = sources.length > 1 || !isSource ? `<div class="pills" aria-label="分鏡來源">${sources.map((source) => {
    const name = esc(source + sourceLabel(source));
    if (source === path) return `<span class="pill on" aria-current="true">${name}</span>`;
    return markdownSource(source) ? `<a class="pill" href="${esc(boardEditorHref(row.id, source))}">${name}</a>`
      : `<a class="pill" href="#/file?${esc(query({ path: source }))}" title="查看 CSV 原文">${name} · CSV</a>`;
  }).join("")}</div>` : "";
  return `<div class="wrap" data-view="board"><div class="head"><div><h2>分鏡表格</h2><p class="sub">${isSource ? esc(path) : "請選擇要編輯的 Markdown 來源。"}</p></div>
    <div class="actions"><a class="btn ghost" href="#/${esc(row.id)}/board">返回分鏡</a>${isSource ? `${editButton(path)}
    <button class="btn primary" type="button" data-act="save-board" id="saveButton" disabled>儲存 <kbd>⌘S</kbd></button>` : ""}</div></div>
    ${menu}${problemNotices(E)}${isSource ? `<p class="muted small" id="editState" role="status">正在讀取…</p><div id="editNotice"></div><div id="boardDraft"></div>` : ""}</div>`;
}

function renderBoardDraft(edit) {
  const host = $("#boardDraft");
  host.innerHTML = edit.tables.map((table, t) => {
    const groups = table.groups.map((group, g) => {
      const rows = group.rows.map((row, r) => {
        const button = (action, label, disabled = false) => `<button class="btn sm" type="button" data-act="board-${action}" ${disabled ? "disabled" : ""}>${label}</button>`;
        const controls = `<div class="board-row-actions">${button("up", "上移", r === 0)}${button("down", "下移", r === group.rows.length - 1)}${button("delete", "刪除")}</div>`;
        const cells = row.cells.map((cell, c) => `<td>${c === 0 && row.key !== null ? `<b>${esc(cell)}</b>` :
          `<textarea data-cell="${c}" rows="${c === 0 ? 1 : 2}" aria-label="${esc(`${row.cells[0] || `第 ${r + 1} 列`} · ${SHOT_COLUMNS[c]}`)}">\n${esc(cell)}</textarea>`}${c === 0 ? controls + (row.note ? `<details><summary>修改附註</summary>${fieldHTML(row.note)}</details>` : "") : ""}</td>`).join("");
        return `<tr data-row="${r}">${cells}</tr>`;
      }).join("");
      const summary = group.summary ? `<tr class="board-summary">${group.summary.map((cell) => `<td>${esc(cell)}</td>`).join("")}</tr>` : "";
      return `<tbody data-table="${t}" data-group="${g}">${rows}<tr><td colspan="8"><button class="btn sm" type="button" data-act="board-add">＋ 新增鏡頭</button></td></tr>${summary}</tbody>`;
    }).join("");
    return `<section class="card table-card">${edit.tables.length > 1 ? `<h3>分鏡表 ${t + 1}</h3>` : ""}<table class="shot-table board-edit-table"><thead><tr>${SHOT_COLUMNS.map((column) => `<th scope="col">${esc(column)}</th>`).join("")}</tr></thead>${groups}</table></section>`;
  }).join("");
}

function boardDraftPayload(tables) {
  return tables.map((table) => table.groups.map((group) => group.rows.map(({ key, cells }) => ({ key, cells }))));
}

function updateBoardDraft(edit) {
  setDirty(JSON.stringify(boardDraftPayload(edit.tables)) !== edit.original);
}

async function openBoardEditor(path, sequence) {
  const host = $("#boardDraft");
  if (!host) return;
  const project = S.project;
  try {
    if (S.edit?.kind !== "board" || S.edit.path !== path) {
      const data = await api(`/api/storyboard-table?${query({ project, path })}`);
      if (sequence !== S.renderSequence || !host.isConnected) return;
      S.edit = { kind: "board", path, project, version: data.version, tables: data.tables,
        original: JSON.stringify(boardDraftPayload(data.tables)), writable: true, saving: false, dirty: false };
    }
    const edit = S.edit;
    $("#editState").textContent = "變更將寫回上方所選的檔案。";
    renderBoardDraft(edit);
    host.addEventListener("input", (event) => {
      const field = event.target;
      if (!field.matches("[data-cell]")) return;
      const { table, group } = field.closest("tbody").dataset;
      edit.tables[table].groups[group].rows[field.closest("tr").dataset.row].cells[field.dataset.cell] = field.value;
      updateBoardDraft(edit);
    });
    updateBoardDraft(edit);
    if (edit.notice) $("#editNotice").innerHTML = edit.notice;
  } catch (error) {
    if (sequence !== S.renderSequence || !host.isConnected) return;
    $("#editState").textContent = "";
    $("#editNotice").textContent = friendlyFailure(error.message);
  }
}

function changeBoardRows(button, action) {
  const edit = S.edit;
  if (edit?.kind !== "board" || edit.saving || button.disabled) return;
  const { table, group } = button.closest("tbody").dataset;
  const rows = edit.tables[table].groups[group].rows;
  let index = Number(button.closest("tr").dataset.row);
  if (action === "board-add") {
    index = rows.length;
    rows.push({ key: null, cells: SHOT_COLUMNS.map(() => ""), note: "" });
  } else if (action === "board-delete") {
    if (rows[index].key !== null && !confirm(`刪除鏡頭 ${rows[index].cells[0]}？相關素材與提示詞會保留。`)) return;
    rows.splice(index, 1);
  } else {
    const to = index + (action === "board-up" ? -1 : 1);
    if (to < 0 || to >= rows.length) return;
    [rows[index], rows[to]] = [rows[to], rows[index]];
    index = to;
  }
  const scroll = button.closest(".table-card").scrollLeft;
  renderBoardDraft(edit);
  const tbody = $(`#boardDraft tbody[data-table="${table}"][data-group="${group}"]`);
  tbody.closest(".table-card").scrollLeft = scroll;
  const next = tbody.querySelector(`[data-row="${index}"] [data-act="${action}"]:not(:disabled)`) ||
    tbody.querySelector(`[data-row="${index}"] textarea`) || tbody.querySelector('[data-act="board-add"]');
  next?.focus({ preventScroll: action !== "board-add" });
  updateBoardDraft(edit);
}

async function saveBoard() {
  const edit = S.edit;
  if (edit?.kind !== "board" || !edit.dirty || edit.saving || !edit.writable) return;
  edit.saving = true;
  const host = $("#boardDraft");
  $$("textarea", host).forEach((field) => { field.readOnly = true; });
  setDirty(true);
  $("#editState").textContent = "正在儲存…";
  try {
    const result = await api(`/api/storyboard-table?${query({ project: edit.project, path: edit.path })}`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expectedVersion: edit.version, tables: boardDraftPayload(edit.tables) }),
    });
    if (S.project === edit.project) S.episodes.clear();
    if (S.edit !== edit) return;
    Object.assign(edit, { version: result.version, tables: result.tables,
      original: JSON.stringify(boardDraftPayload(result.tables)), saving: false, notice: "" });
    renderBoardDraft(edit);
    setDirty(false);
    $("#editNotice").innerHTML = "";
    $("#editState").textContent = "已儲存";
    try { await refreshProject(); } catch (_error) { toast("分鏡已儲存，專案摘要暫未更新。"); }
  } catch (error) {
    if (S.edit !== edit) return;
    edit.saving = false;
    const conflict = error.status === 409;
    edit.writable = !conflict;
    $$("textarea", host).forEach((field) => { field.readOnly = false; });
    setDirty(true);
    $("#editState").textContent = "尚未儲存";
    edit.notice = `<div class="notice danger" role="alert"><span>${esc(conflict ? "來源檔已在別處修改。可先複製草稿，再載入最新版本。" : friendlyFailure(error.message))}</span>
      ${conflict ? '<div class="actions"><button type="button" class="btn sm" data-act="copy-board">複製表格草稿</button><button type="button" class="btn sm" data-act="reload-board">載入最新版本</button></div>' : ""}</div>`;
    $("#editNotice").innerHTML = edit.notice;
  }
}

function sourceVersionsHTML(shot, supplement) {
  const sources = supplement.sources || [];
  if (!sources.length) return "";
  const resolution = supplement.source_resolution || {};
  const substantive = sources.some((source) => source.substantive_differences?.length);
  const status = resolution.resolved === false ? "來源主表尚待確認，以下保留原文供核對。" : resolution.primary ? `目前讀取：${fileLabel(resolution.primary)}。${substantive ? "其他來源有欄位差異，以下保留原文供核對。" : "其他輸出內容相同；換行與表格編碼差異不視為錯誤。"}` : sources.length > 1 ? "來源尚未指定主表，請核對差異。" : "保留原始八欄來源供核對。";
  return `<div class="source-versions"><p>${esc(status)}</p>${sources.map((source, i) => `<details name="sources-${esc(shot.id)}"><summary>查看來源：${esc(source.path?.split(/[\\/]/).pop() || `來源 ${i + 1}`)}</summary>${source.substantive_differences?.length ? `<p>差異欄位：${esc(source.substantive_differences.join("、"))}</p>` : ""}${Object.entries(source.fields || {}).map(([key, value]) => `<p><strong>${esc(key)}</strong>　${fieldHTML(value || "未提供")}</p>`).join("")}${source.notes?.length ? `<p>${esc(source.notes)}</p>` : ""}</details>`).join("")}</div>`;
}

function renderInspector(row, E, id) {
  const host = $("#inspector");
  const C = E ? context(E) : null;
  const shot = C?.shot[id];
  if (!shot) {
    host.hidden = true;
    host.innerHTML = "";
    $("#scrim").hidden = true;
    document.body.classList.remove("with-inspector");
    return;
  }
  const index = C.shots.indexOf(shot);
  const prompt = C.promptByShot[shot.id];
  const found = findingsFor(C, shot.id);
  const clip = C.clipByShot[shot.id];
  const frame = C.frame(shot);
  const supplement = shot.supplement || {};
  const extraMedia = (supplement.media || []).filter((item) => item?.path && /image|frame|草圖|首幀|尾幀|keyframe|grid|reference/i.test(`${item.kind || ""} ${item.role || ""} ${item.path}`));
  const videoCandidates = (supplement.media || []).filter((item) => item?.path && (item.kind === "video" || item.role === "video_candidate") && (!Array.isArray(item.shot_ids) || !item.shot_ids.length || item.shot_ids.includes(shot.id)));
  const imageItems = [...new Map([
    ...(frame ? [[frame, { path: frame, role: "first_frame", verified: true }]] : []),
    ...extraMedia.map((item) => [item.path, item]),
  ]).values()];
  const hasSingleShotImage = imageItems.some(isShotImage);
  const images = [...new Set([frame, ...extraMedia.map((item) => item.path)].filter(Boolean))];
  const fieldPrompt = shot.fields?.["畫面prompt"] ?? shot.fields?.["画面prompt"];
  const promptItems = [
    ...(fieldPrompt ? [{ text: fieldPrompt, label: "畫面提示詞（八欄原文）", source: "八欄分鏡表", id: `field-prompt-${shot.id}` }] : []),
    ...((supplement.prompts || []).filter((item) => item?.text).map((item, i) => ({ text: item.text, label: item.kind || "補充提示詞", source: item.source || "補充資料", id: `supp-${shot.id}-${i}` }))),
    ...(shot.keyframe ? [{ text: shot.keyframe, label: "首幀提示詞", source: "分鏡", id: `kf-${shot.id}` }] : []),
    ...(shot.closing_keyframe ? [{ text: shot.closing_keyframe, label: "尾幀提示詞", source: "分鏡", id: `ckf-${shot.id}` }] : []),
    ...(prompt?.prompt ? [{ text: prompt.prompt, label: prompt.mode ? `影片提示詞 · ${prompt.mode}` : "影片提示詞", source: typeof prompt.source === "object" ? prompt.source.path : prompt.source || "影片提示詞", id: prompt.id || `vp-${shot.id}` }] : []),
  ].filter((item, index, items) => items.findIndex((candidate) => candidate.text.replace(/\r\n/g, "\n").trim() === item.text.replace(/\r\n/g, "\n").trim()) === index);
  const startAt = C.shots.slice(0, index).reduce((sum, item) => sum + item.sec, 0);
  const cut = C.cuts.find((item) => item.shot === shot.id || (Array.isArray(item.group_shots) && item.group_shots.includes(shot.id)));
  const qs = location.hash.includes("?") ? `?${location.hash.split("?")[1]}` : "";
  const startSlot = shot.refs.find((slot) => slot.kind === "REF" && String(slot.use || "").replaceAll("帧", "幀") === "起始幀");
  let refClass = shot.refState;
  let refLabel = shot.refLabel;
  if (startSlot && !frame) { refClass = "missing"; refLabel = "寫了起始幀，但專案裡找不到這張圖"; }
  else if (frame && !shot.refs.length && refClass !== "missing") { refClass = "pending"; refLabel = "已關聯起始幀候選，參考待確認"; }
  host.hidden = false;
  document.body.classList.add("with-inspector");
  $("#scrim").hidden = !(typeof matchMedia === "function" && matchMedia("(max-width: 760px)").matches);
  host.innerHTML = `<div class="ins-head"><button class="icon-btn" type="button" data-act="close-ins" aria-label="關閉">${icon("close")}</button><div><div class="id">${esc(shot.id)}</div><div class="t">${esc(shot.title)}</div></div>
    <div class="nav"><button class="icon-btn" type="button" data-shot-nav="${esc(C.shots[index - 1]?.id || "")}" ${index ? "" : "disabled"} aria-label="上一鏡">${icon("left")}</button><button class="icon-btn" type="button" data-shot-nav="${esc(C.shots[index + 1]?.id || "")}" ${index < C.shots.length - 1 ? "" : "disabled"} aria-label="下一鏡">${icon("right")}</button></div></div>
  <div class="ins-body">
    ${found.map((finding) => `<a class="refstate ${finding.sev === "must" ? "must" : "pending"}" href="#/${esc(row.id)}/review/${esc(finding.id)}"><span class="tag ${finding.sev}">${SEVERITY_LABEL[finding.sev]}</span><span><b>${esc(finding.title)}</b><br><span class="muted">${esc(finding.fix)}</span></span></a>`).join("")}
    <div class="ins-parity-grid">
      <section class="ins-visual"><h4>畫面與設定</h4>
        ${clip?.cut.still ? `<div class="thumb"><img src="${esc(mediaUrl(clip.path))}" alt="${esc(shot.title)} 成片靜幀"></div>` : clip ? `<div class="thumb"><video src="${esc(mediaUrl(clip.path))}#t=${num(clip.cut.in)},${num(clip.cut.out)}" ${frame ? `poster="${esc(mediaUrl(frame))}"` : ""} controls playsinline preload="metadata"></video></div>` : ""}
        ${imageItems.length ? `${!hasSingleShotImage ? `<div class="ins-missing">尚無此鏡單獨圖片；以下為整張分鏡草圖或關聯參考圖。</div>` : ""}<div class="ins-image-grid">${imageItems.map((item) => { const role = String(item.role || item.kind || "").toLowerCase(); const grid = isGridMedia(item); const first = /first|start|首幀|起始幀/.test(role) || item.verified; const last = /last|end|尾幀/.test(role); const label = grid ? `整張分鏡草圖${item.shot_ids?.length ? ` · ${gridCoverage(item)}` : ""}` : first ? "首幀" : last ? "尾幀" : /reference|asset|設定卡|參考/.test(role) ? "設定參考圖" : "未確認圖片候選"; return `<a href="${esc(mediaUrl(item.path))}" target="_blank" rel="noreferrer"><img src="${esc(mediaUrl(item.path))}" alt="${esc(label)}" loading="lazy"><span>${esc(label)}</span></a>`; }).join("")}</div>` : `<div class="ins-missing">${frame ? "沒有其他單鏡參考圖" : "此鏡尚無已登錄圖片"}${extraMedia.length ? "；另有未確認媒體" : ""}</div>`}
        ${videoCandidates.length ? `<div class="ins-candidates"><b>影片候選（未確認，不視為正式成片）</b>${videoCandidates.map((item) => `<div class="candidate-video"><video src="${esc(mediaUrl(item.path))}" controls playsinline preload="metadata"></video><span>${esc(item.role === "video_candidate" ? "未確認候選" : item.role || "關聯影片")}${item.shot_ids?.length > 1 ? ` · 分組鏡頭 ${esc(item.shot_ids.join("、"))}` : ""}</span></div>`).join("")}</div>` : ""}
        ${shot.basis?.length ? `<div class="ins-entities"><b>出場設定</b><div class="pills">${shot.basis.map((entry) => `<a class="pill" href="#/${esc(row.id)}/settings/${encodeURIComponent(settingKey(entry.cat, entry.name))}">${esc(entry.name)}</a>`).join("")}</div></div>` : `<div class="ins-missing">未登錄人物、造型、場景或道具設定卡</div>`}
        <div class="muted small">${clip ? `${clip.cut.still ? `成片靜幀 · ${esc(moveLabel(clip.cut))}` : "成片片段"} · 剪輯單 ${esc(clip.cut.id)}` : frame ? "已關聯首幀候選；尚無成片片段" : "尚無首幀候選或成片片段"}</div>
      </section>
      <section class="ins-prompts"><h4>提示詞 <span class="muted small">依來源分開顯示</span></h4>
        ${promptItems.length ? promptItems.map((item) => `<article class="ins-prompt"><header><b>${esc(item.label)}</b><span>${esc(item.source)}</span><span class="act">${copyButton(item.text, item.id)}</span></header><button class="prompt clamp" type="button" data-act="expand" aria-label="展開或收合${esc(item.label)}">${esc(item.text)}</button></article>`).join("") : `<div class="ins-missing">尚無此鏡提示詞</div>`}
        ${sourceVersionsHTML(shot, supplement)}
      </section>
    </div>
    ${qcRegistryHtml([shot])}
    <div class="ins-media">
      <div class="facts">
        <div class="fact"><div class="k">時長</div><div class="v">${esc(num(shot.sec))} 秒 · 第 ${fmt(startAt)} 起</div></div>
        <div class="fact"><div class="k">場次</div><div class="v">${shot.scene ? `<a href="#/${esc(row.id)}/script/${esc(shot.scene)}">${esc(sceneShort(shot.scene))} ${esc(placeOf(C, shot.scene))}</a>` : "—"}</div></div>
        <div class="fact"><div class="k">景別 / 機位</div><div class="v">${fieldHTML(shot.framing || "—")}</div></div>
        <div class="fact"><div class="k">運鏡</div><div class="v">${fieldHTML(shot.move || "—")}</div></div>
      </div>
    </div>
    ${shot.purpose ? `<div class="ins-sec"><h4>目的</h4><p class="purpose">${fieldHTML(shot.purpose)}</p></div>` : ""}
    ${(() => { const block = (E.board?.blocking || []).find((item) => item.scene === shot.scene); return block ? `<div class="ins-sec" id="insBlocking"><h4>場景站位</h4>${blockingRows(block)}</div>` : ""; })()}
    <div class="ins-sec"><h4>動作</h4><div class="timeline3"><div><b>起點</b>${fieldHTML(shot.start || "—")}</div><div class="mid"><b>本鏡動作</b>${fieldHTML(shot.action || "—")}</div><div><b>終點</b>${fieldHTML(shot.end || "—")}</div></div></div>
    <div class="ins-sec"><h4>聲音</h4><p>${fieldHTML(shot.sound || "—")}</p>${cut?.subs.length ? `<div>${cut.subs.map((sub) => `<span class="subline">「${esc(sub.text)}」</span>`).join("")}</div>` : ""}</div>
    ${shot.screenText || cut?.texts.length ? `<div class="ins-sec"><h4>畫面文字</h4>${shot.screenText ? `<p>${fieldHTML(shot.screenText)}</p>` : ""}${(cut?.texts || []).map((text) => `<div><span class="stxt">${esc(text.style)}｜${esc(text.items.join("｜"))}</span></div>`).join("")}</div>` : ""}
    <div class="ins-sec"><h4>畫面裡有</h4><div class="pills">${shot.basis.map((entry) => `<a class="pill" href="#/${esc(row.id)}/settings/${encodeURIComponent(settingKey(entry.cat, entry.name))}" title="${esc(`控制：${entry.ctl}`)}">${icon(entry.cat === "人物" || entry.cat === "造型" ? "person" : categoryKey(entry.cat) === "地點" ? "place" : "prop")}${esc(entry.name)}</a>`).join("") || '<span class="muted">無</span>'}</div></div>
    <div class="ins-sec"><h4>參考圖</h4><div class="refstate ${refClass}">${icon(refClass === "bound" ? "check" : refClass === "pending" || refClass === "missing" ? "alert" : "text")}<div><b>${esc(refLabel)}</b>${shot.refs.map((slot) => `<div class="slot">${slot.order}. ${esc(slot.name)}${slot.use ? ` · ${esc(slot.use)}` : ""} · <span class="mono">${esc(slot.path || slot.target)}</span></div>`).join("")}</div></div>
      ${shot.imgs.length ? `<div class="pills">${shot.imgs.map((img) => `<a class="pill id" href="#/${esc(row.id)}/prompts/image?id=${esc(img.id)}" title="${esc(`${img.name} · 控制：${img.ctl}`)}">${esc(img.id)}</a>`).join("")}</div>` : ""}</div>
    <div class="ins-sec"><h4>八欄資料</h4><dl class="ins-fields">${SHOT_COLUMNS.map((key) => `<div><dt>${esc(key)}</dt><dd>${fieldHTML(shot.fields?.[key])}</dd></div>`).join("")}</dl></div>
    ${supplement.notes ? `<div class="ins-sec"><h4>來源附註</h4><p>${esc(supplement.notes)}</p></div>` : ""}
    <div>${editButton(E.docs["分鏡.md"], shot.id, "在分鏡.md 裡編輯這一鏡")}</div>
  </div>`;
  host.dataset.back = `#/${row.id}/board${qs}`;
}

/* ================================================================ settings */

const SETTING_CATEGORIES = new Set(["人物", "造型", "地點", "地点", "道具"]);
const categoryKey = (value) => displayLabel(value);

function settingKey(cat, name) {
  return cat ? `${categoryKey(cat)}·${name}` : String(name ?? "");
}

function parseSettingKey(raw) {
  if (!raw) return { cat: null, name: "" };
  const sep = raw.indexOf("·");
  if (sep > 0) {
    const cat = raw.slice(0, sep);
    if (SETTING_CATEGORIES.has(cat)) return { cat: categoryKey(cat), name: raw.slice(sep + 1) };
  }
  return { cat: null, name: raw };
}

function presence(C, item) {
  return C.shots
      .filter((shot) => shot.basis.some((entry) => categoryKey(entry.cat) === categoryKey(item.cat) && entry.name === item.name))
    .map((shot) => shot.id);
}

function entryLocks(item) {
  if (Array.isArray(item?.locks)) return item.locks.filter(Boolean);
  return item?.lock ? [item.lock] : [];
}

function viewSettings(row, E) {
  if (!row.has.settings) return missingView(row, "settings");
  if (!E.settings) return rawFallback(E, E.docs["視覺設定.md"], "視覺設定");
  const C = context(E);
  const settings = E.settings;
  const card = (item) => {
    const seen = new Set(presence(C, item));
    const itemLocks = entryLocks(item);
    const locked = new Set(itemLocks.flatMap((lock) => lock.shots || []));
    const anchor = item.fields["外觀特徵"] ?? item.fields["外观特征"];
    const rest = Object.entries(item.fields).filter(([key]) => key !== "外觀特徵" && key !== "外观特征");
    const key = settingKey(item.cat, item.name);
    return `<article class="card asset" id="a-${esc(key)}" data-entry="${esc(item.name)}" data-cat="${esc(item.cat)}">
      <div class="asset-h"><span class="tile">${item.cat === "人物" ? esc(item.name[0]) : icon(categoryKey(item.cat) === "地點" ? "place" : item.cat === "造型" ? "person" : "prop")}</span><div><div class="nm">${esc(item.name)}</div><div class="cat">${esc(displayLabel(item.cat))}${item.designators.length ? ` · 提示詞名稱 <span class="mono">${esc(item.designators.join("、"))}</span>` : ""}</div></div></div>
      ${item.overlay ? '<span class="overlay-note">只在後期疊加，不進生成畫面</span>' : ""}
      ${item.desc.map((line) => `<p class="desc">${esc(line)}</p>`).join("")}
      ${anchor ? `<div class="anchor"><b>外觀特徵</b>${esc(anchor)}</div>` : ""}
      ${rest.map(([k, value]) => `<div class="field"><span class="muted">${esc(k)}：</span>${esc(value)}</div>`).join("")}
      ${itemLocks.map((lock) => `<div class="lock"><div class="ln">${icon("lock")}連戲鎖《${esc(lock.name)}》</div><span class="surface">${esc(lock.surface)}</span><div class="muted small">${lockReach(C, lock)} · 設定圖、首幀及未靠參考圖鎖住外觀的影片提示詞需帶上這段</div></div>`).join("")}
      ${C.shots.length ? `<div class="presence"><div class="pk"><span>${!seen.size && E.source_format?.["視覺設定.md"] === "native" ? "尚無明示鏡號關聯" : `出現在 ${seen.size} 鏡`}</span>${seen.size ? `<a href="#/${esc(row.id)}/board?entity=${encodeURIComponent(key)}">在分鏡裡篩出 ${icon("right")}</a>` : ""}</div>
        <div class="pstrip" aria-hidden="true">${C.shots.map((shot) => `<i data-css="flex-grow:${Math.max(0.2, shot.sec)}" class="${seen.has(shot.id) ? (locked.has(shot.id) || locked.has("全集") ? "lk" : "on") : ""}" title="${esc(shot.n)}"></i>`).join("")}</div></div>` : ""}
    </article>`;
  };
  return `<div class="wrap" data-view="settings">
    <div class="head"><div><h2>視覺設定</h2><div class="sub">${esc(settings.form)}</div></div><div class="actions">${editButton(E.docs["視覺設定.md"])}</div></div>
    ${problemNotices(E)}
    ${settings.era.period || settings.era.facets.length ? `<section class="card era"><div class="era-l"><div class="eyebrow">時代背景</div><div class="p">${esc(settings.era.period)}</div><div class="f">全集服飾、陳設與照明的年代基準</div></div>
      <div class="era-r">${settings.era.facets.map((facet) => `<div><div class="k">${esc(facet.k)}</div><div class="v">${esc(facet.v)}</div></div>`).join("")}</div></section>` : ""}
    ${["人物", "造型", "地點", "道具"].map((category) => { const items = settings.items.filter((item) => item.cat === category); if (!items.length) return "";
      return `<div class="section-t"><h3>${category}</h3><span class="n">${items.length}</span>${category === "人物" && C.shots.length ? '<span class="more">出場條：每格一鏡，寬度按時長；硃紅 = 連戲鎖生效</span>' : ""}</div><div class="assets">${items.map(card).join("")}</div>`; }).join("")}
  </div>`;
}

/** How far a continuity lock reaches, in the words its scope was written in. */
function lockReach(C, lock) {
  if (lock.shots.includes("全集")) return `鎖定全集 ${C.shots.length} 鏡`;
  if (lock.scope === "入畫") return C.shots.length ? `入畫 · 鎖定 ${lock.shots.length} 鏡` : "入畫 · 分鏡寫完後在出場鏡頭生效";
  return `鎖定 ${lock.shots.length} 鏡`;
}

/* ================================================================ prompts */

/** One copy unit per generation: a delivery group stands in for its members, in sequence. */
function videoCopyUnits(row, E) {
  const groups = E.videoGroups || [];
  const groupOf = new Map(groups.flatMap((group) => group.members.map((member) => [member, group])));
  const shortId = (id) => id.replace(/^MOTION-(EP\d+-)?/, "");
  const units = [];
  const placed = new Set();
  for (const prompt of E.videoPrompts || []) {
    const group = groupOf.get(prompt.id);
    if (group && placed.has(group.id)) continue;
    if (group) {
      placed.add(group.id);
      units.push({ key: group.id, id: group.id, title: group.title, meta: [`${num(group.sec)} 秒 · 多鏡 ${group.members.length} 鏡`, `成員 ${group.members.map((member) => esc(shortId(member))).join("、")}`], text: group.prompt });
      continue;
    }
    units.push({ key: prompt.id, id: prompt.id, title: prompt.title, meta: [`${num(prompt.sec)} 秒${prompt.mode ? ` · ${esc(prompt.mode)}` : ""}`, prompt.shot ? `分鏡 <a href="#/${esc(row.id)}/board/${esc(prompt.shot)}">${esc(sceneShort(prompt.shot))}</a>` : ""], text: prompt.prompt });
  }
  return units;
}

function keyframeCopyUnits(shots) {
  const units = [];
  for (const shot of shots || []) {
    if (shot.keyframe) {
      units.push({ key: `kf-${shot.id}`, id: shot.id, title: shot.title, meta: [`${esc(shot.scale || "景別未辨識或複合")} · ${num(shot.sec)} 秒`, "首幀"], text: shot.keyframe });
    }
    if (shot.closing_keyframe) {
      units.push({ key: `ckf-${shot.id}`, id: `${shot.id}-closing`, title: shot.title, meta: [`${esc(shot.scale || "景別未辨識或複合")} · ${num(shot.sec)} 秒`, "尾幀"], text: shot.closing_keyframe });
    }
  }
  return units;
}

function viewPrompts(row, E, arg, q) {
  if (!row.has.imgp && !row.has.vidp && !row.has.board) return missingView(row, "prompts");
  const C = context(E);
  const sets = {
    video: videoCopyUnits(row, E),
    keyframe: keyframeCopyUnits(C.shots),
    image: (E.imagePrompts || []).map((prompt) => ({ key: prompt.id, id: prompt.id, title: prompt.title, meta: [esc(prompt.use), `被 ${C.shots.filter((shot) => shot.imgs.some((img) => img.id === prompt.id)).length} 鏡引用`], text: prompt.prompt })),
  };
  const tab = ["video", "keyframe", "image"].includes(arg) ? arg : sets.video.length ? "video" : sets.keyframe.length ? "keyframe" : "image";
  const list = sets[tab].filter((item) => item.text);
  const done = list.filter((item) => S.copied.has(item.key)).length;
  const nextItem = list.find((item) => !S.copied.has(item.key));
  const open = q.get("id");
  const docFor = { video: E.docs["影片提示詞.md"], keyframe: E.docs["分鏡.md"], image: E.docs["圖片提示詞.md"] }[tab];
  const unreadable = { video: row.has.vidp && !E.videoPrompts, image: row.has.imgp && !E.imagePrompts, keyframe: row.has.board && !E.board }[tab];
  return `<div class="wrap" data-view="prompts">
    <div class="head"><div><h2>提示詞</h2><div class="sub">整段複製，粘進你的生成工具；一條就是一次生成</div></div>
      <div class="actions"><div class="seg" role="tablist">${[["video", `影片 ${sets.video.length}`], ["keyframe", `關鍵幀 ${sets.keyframe.length}`], ["image", `圖片 ${sets.image.length}`]].map(([key, label]) => `<a role="tab" href="#/${esc(row.id)}/prompts/${key}" ${tab === key ? 'aria-current="page"' : ""}>${label}</a>`).join("")}</div>${editButton(docFor)}</div></div>
    ${problemNotices(E)}
    ${unreadable ? rawFallback(E, docFor, "提示詞") : list.length ? `<div class="card copybar"><b>逐條複製</b><span class="bar"><i data-css="width:${(done / list.length) * 100}%"></i></span><span class="muted" id="copyProgress">${done} / ${list.length}</span>
      ${nextItem ? `<button class="btn sm primary" type="button" data-copy="${esc(nextItem.text)}" data-key="${esc(nextItem.key)}" data-next="1">${icon("copy")}複製下一條 · <span class="mono">${esc(nextItem.id.replace(/^(MOTION|SHOT|IMG|GROUP)-(EP\d+-)?/, ""))}</span></button>` : `<span class="status ok">${icon("check")}全部複製過</span>`}
      <button class="btn sm ghost" type="button" data-act="clear-copied" data-tab="${tab}">清除標記</button><span class="muted lbl-long">標記只存在這臺電腦的瀏覽器裡</span></div>
    <div class="plist">${list.map((item) => `<article class="card pcard ${S.copied.has(item.key) ? "copied" : ""}" id="p-${esc(item.id)}" data-key="${esc(item.key)}">
      <div><div class="pid">${esc(item.id)}</div><div class="pt">${esc(item.title)}</div><div class="pm">${item.meta.filter(Boolean).map((line) => `<span>${line}</span>`).join("")}</div></div>
      <div class="ptext ${open === item.id ? "" : "clamp"}" data-act="expand">${esc(item.text)}</div>
      <div class="pact">${copyButton(item.text, item.key)}<span class="cc">${item.text.length} 字元</span></div></article>`).join("")}</div>`
      : `<div class="empty"><h3>這一類還沒有提示詞</h3><p>${tab === "keyframe" ? "分鏡裡寫了「首幀提示詞」或「尾幀提示詞」的鏡頭會列在這裡。" : "寫好後這裡會逐條列出。"}</p></div>`}
  </div>`;
}

/* ================================================================ film */

function highlight(text, keys) {
  const raw = String(text ?? "");
  const clean = [...new Set((keys || []).map((key) => String(key ?? "")).filter(Boolean))]
    .sort((a, b) => b.length - a.length);
  if (!clean.length) return esc(raw);
  const re = new RegExp(clean.map((key) => key.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|"), "g");
  let out = "";
  let last = 0;
  for (const match of raw.matchAll(re)) {
    out += esc(raw.slice(last, match.index)) + `<mark>${esc(match[0])}</mark>`;
    last = match.index + match[0].length;
  }
  return out + esc(raw.slice(last));
}

function viewMaterialLibrary(row, E) {
  const candidates = new Map((E.media?.candidates || []).map((media) => [media.path, {path:media.path, shots:new Set(media.shot_ids || [])}]));
  for (const shot of E.board?.shots || []) for (const media of shot.supplement?.media || []) {
    if (!media.path || !(media.kind === "video" || /\.(mp4|mov|webm)$/i.test(media.path))) continue;
    const entry = candidates.get(media.path) || { path: media.path, shots: new Set() };
    for (const id of media.shot_ids?.length ? media.shot_ids : [shot.id]) entry.shots.add(id);
    candidates.set(media.path, entry);
  }
  const request = `請依 ${row.id} 已選定的實際素材規劃剪輯旁表，列出取用檔案、鏡號、入出點、字幕與聲音落點；先確認素材選擇，不改八欄分鏡，也不直接生成或渲染。`;
  return `<div class="wrap" data-view="film"><div class="head"><div><h2>影片素材與後製</h2><div class="sub">${candidates.size} 份素材候選；未經選定的片段不代表正式成片</div></div></div>${problemNotices(E)}<p>剪輯單是選用的後製旁表。瀏覽、挑選素材不需要先寫剪輯單。</p><button class="btn" data-copy="${esc(request)}">規劃剪輯（選用）</button><div class="material-library">${[...candidates.values()].map((candidate) => `<article class="card material-item"><h3>${esc([...candidate.shots].join("、") || "未對應目前分鏡的素材")}</h3><video src="${esc(mediaUrl(candidate.path))}" controls playsinline preload="metadata"></video><p>${esc(candidate.path.split("/").pop())}</p><span class="muted">素材候選，尚未確認剪輯取用</span></article>`).join("") || '<div class="empty">尚無影片素材，可先依現有提示詞製作；無須建立剪輯單。</div>'}</div></div>`;
}

function viewFilm(row, E, arg, q) {
  if (!row.has.cut && !row.has.film) return viewMaterialLibrary(row, E);
  const C = context(E);
  const CL = E.cutlist;
  const aspectCss = aspectRatioCss(S.series?.format?.aspect_ratio);
  const clipsTab = arg === "clips";
  const header = `<div class="head"><div><h2>剪輯與成片</h2><div class="sub">${CL ? `${C.cuts.length} 段 · ${fmt(C.cutTotal)} · 按剪輯單排列` : "已有成片；剪輯旁表為選用資料"}</div></div>
      <div class="actions"><div class="seg"><a href="#/${esc(row.id)}/film" ${clipsTab ? "" : 'aria-current="page"'}>成片</a><a href="#/${esc(row.id)}/film/clips" ${clipsTab ? 'aria-current="page"' : ""}>逐鏡素材</a></div>${editButton(E.docs["剪輯單.md"], "", "編輯剪輯單")}</div></div>`;
  if (row.has.cut && !CL) return `<div class="wrap" data-view="film">${header}${problemNotices(E)}<div data-raw="${esc(E.docs["剪輯單.md"])}"><div class="loading">正在讀取原文…</div></div></div>`;
  if (clipsTab) return `<div class="wrap" data-view="film">${header}${problemNotices(E)}${clipsView(C, row)}</div>`;
  const total = C.cutTotal || 1;
  const X = (t) => `${(t / total) * 100}%`;
  const ticks = [];
  for (let t = 0; t <= total + 0.001; t += total > 90 ? 10 : 5) ticks.push(`<span data-css="left:${X(t)}">${t}</span>`);
  const kindOf = (text) => { for (const scene of C.scenes) for (const block of scene.blocks) if (block.k === "line" && squash(block.text) === squash(text)) return block.tag === "VO" ? "vo" : ""; return ""; };
  const timeline = CL ? `<div class="tl-inner" id="tl">
    <div class="tl-row"><span></span><div class="tl-ruler">${ticks.join("")}</div></div>
    <div class="tl-row"><span class="tl-lab">畫面</span><div class="tl-track">${C.cuts.map((cut, i) => `<button class="tl-cut ${i % 2 ? "b" : ""}${cut.still ? " still" : ""}" type="button" data-cut="${esc(cut.id)}" data-css="left:${X(cut.at)};width:calc(${X(cut.sec)} - 2px)" data-tip-b="${esc(cut.n)}" data-tip="${esc(`${cut.title} · ${num(cut.sec)}s${cut.still ? ` · 靜幀 ${moveLabel(cut)}` : ""}`)}">${esc(cut.n.slice(-2))}</button>`).join("")}</div></div>
    <div class="tl-row"><span class="tl-lab">字幕</span><div class="tl-track">${C.cuts.flatMap((cut) => cut.subs.map((sub) => { const s = sub.s ?? 0; const e = sub.e ?? cut.sec; return `<span class="tl-sub ${kindOf(sub.text)}" data-css="left:${X(cut.at + s)};width:${X(Math.max(0.1, e - s))}" data-tip="${esc(sub.text)}">${esc(sub.text)}</span>`; })).join("")}</div></div>
    <div class="tl-row"><span class="tl-lab">畫面文字</span><div class="tl-track">${C.cuts.flatMap((cut) => cut.texts.map((text) => `<span class="tl-txt" data-css="left:${X(cut.at + text.s)};width:${X(Math.max(0.1, text.e - text.s))}" data-tip-b="${esc(text.style)}" data-tip="${esc(text.items.join(" ｜ "))}">${esc(text.style)}</span>`)).join("")}</div></div>
    <div class="tl-row"><span class="tl-lab">音效</span><div class="tl-track">${C.cuts.flatMap((cut) => cut.sfx.map((sfx) => { const name = sfx.path.split("/").at(-1); return `<span class="tl-sfx" data-css="left:${X(cut.at + sfx.s)}" data-tip="${esc(`${name} · ${num(sfx.gain)} dB`)}"></span><span class="sfx-l" data-css="left:calc(${X(cut.at + sfx.s)} + 10px)">${esc(name.replace(/\.\w+$/, ""))}</span>`; })).join("")}</div></div>
    ${C.cuts.some((cut) => cut.voices.length) ? `<div class="tl-row"><span class="tl-lab">配音</span><div class="tl-track">${C.cuts.flatMap((cut) => cut.voices.map((voice) => { const name = voice.path.split("/").at(-1); return `<span class="tl-sfx tl-voice" data-css="left:${X(cut.at + voice.s)}" data-tip="${esc(`${name}${voice.gain ? ` · ${num(voice.gain)} dB` : ""}`)}"></span><span class="sfx-l" data-css="left:calc(${X(cut.at + voice.s)} + 10px)">${esc(name.replace(/\.\w+$/, ""))}</span>`; })).join("")}</div></div>` : ""}
    <div class="tl-head" id="playhead" data-css="left:64px"></div><div class="tl-hit" id="tlhit" aria-label="點選跳轉"></div></div>` : "";
  const rows = C.cuts.map((cut) => `<tr data-cut="${esc(cut.id)}" id="r-${esc(cut.id)}"><td class="mono">${esc(cut.n)}</td><td><b>${esc(cut.title)}</b><div class="muted small">${cut.still ? `<span class="pill">靜幀 · ${esc(moveLabel(cut))}</span> ` : ""}${C.shot[cut.shot] ? `<a href="#/${esc(row.id)}/board/${esc(cut.shot)}">鏡 ${esc(sceneShort(cut.shot))}</a> · ` : ""}<span class="mono">${fmt(cut.at)}</span></div></td>
    <td class="mono hide-m">${cut.in.toFixed(2)}–${cut.out.toFixed(2)}</td><td class="mono">${esc(num(cut.sec))}s</td>
    <td>${cut.subs.map((sub) => `<span class="subline">${highlight(sub.text, sub.keys)}</span>`).join("") || '<span class="muted">—</span>'}${cut.texts.map((text) => `<div><span class="stxt">${esc(text.style)}｜${esc(text.items.join("｜"))}</span></div>`).join("")}</td>
    <td class="hide-m">${cut.bed?.path ? `<span class="pill id">環境聲 · ${esc(cut.bed.path.split("/").at(-1))}</span>` : ""}${cut.voices.map((voice) => `<span class="pill id">${icon("voice")}${esc(voice.path.split("/").at(-1))}</span>`).join("")}${cut.sfx.map((sfx) => `<span class="pill id">${icon("sfx")}${esc(sfx.path.split("/").at(-1))}</span>`).join("")}</td></tr>`).join("");
  const film = E.media.film;
  const ask = CL ? `請按 ${row.id} 的剪輯單.md 渲染成片。` : "";
  return `<div class="wrap" data-view="film">${header}${problemNotices(E)}<div class="film">
      <div class="player"><div class="frame ${aspectCss ? "has-aspect" : "natural"}" ${aspectCss ? `data-css="aspect-ratio:${aspectCss}"` : ""}>${film ? `<video id="film" src="${esc(mediaUrl(film))}" controls playsinline preload="metadata"></video>` : `<span class="ph-note">還沒有渲染成片。渲染在對話裡確認。</span>`}</div>
        ${CL ? `<div class="now"><span id="nowCut">${C.cuts[0] ? `CUT ${esc(C.cuts[0].n)} · ${esc(C.cuts[0].title)}` : ""}</span><span id="nowTime">0:00 / ${fmt(C.cutTotal)}</span></div>` : ""}
        <div class="muted small">瀏覽器只播放已有檔案；重新渲染在對話裡確認。</div>${film ? "" : askButton(ask, false, "複製渲染請求")}</div>
      <div>
        ${CL ? `<div class="deliv">${[CL.target != null ? `目標 ${num(CL.target)} 秒` : "", CL.frame ? `${S.series.format.aspect_ratio ? `${S.series.format.aspect_ratio} · ` : ""}${CL.frame.join("×")}${CL.fps ? ` · ${num(CL.fps)}fps` : ""}` : "", CL.lufs != null ? `響度 ${num(CL.lufs)} LUFS` : "", CL.burn ? "硬字幕" : "不燒字幕", CL.grain != null ? `顆粒 ${num(CL.grain)}` : "", CL.shot_match ? "接鏡匹配" : ""].filter(Boolean).map((item) => `<span class="pill">${esc(item)}</span>`).join("")}</div>
        <section class="card tl">${timeline}</section>
        <div class="card table-card"><table class="cuts"><thead><tr><th>段</th><th>鏡頭</th><th class="hide-m">入–出</th><th>時長</th><th>字幕與畫面文字</th><th class="hide-m">配音與音效</th></tr></thead><tbody>${rows}</tbody></table></div>
        ${CL.unused.length ? `<p class="muted small">未採用：${esc(CL.unused.join("；"))}</p>` : ""}` : '<div class="empty"><p>剪輯單寫好後，這裡會按段列出字幕、畫面文字、配音與音效。</p></div>'}
      </div></div></div>`;
}

function clipsView(C, row) {
  if (!C.shots.length) return '<div class="empty"><p>分鏡寫好後，每鏡一格。</p></div>';
  return `<p class="muted small">每鏡素材只按剪輯單「來源」顯示；沒有來源的鏡頭保持空位，不按檔名猜。</p><div class="clips">${C.shots.map((shot) => { const clip = C.clipByShot[shot.id];
    return `<a class="cliptile" href="#/${esc(row.id)}/board/${esc(shot.id)}" data-shot-tile="${esc(shot.id)}" data-has-clip="${clip ? 1 : 0}">${clip ? `<div class="thumb">${clip.cut.still ? `<img src="${esc(mediaUrl(clip.path))}" alt="${esc(shot.title)} 關鍵幀" loading="lazy">` : `<video src="${esc(mediaUrl(clip.path))}#t=${num(clip.cut.in)}" preload="metadata" muted playsinline></video>`}<span class="sec">${esc(num(shot.sec))}s</span></div>` : `<div class="thumb"><div class="thumb-missing">尚無成片素材</div><span class="sec">${esc(num(shot.sec))}s</span></div>`}<span class="m"><b>${esc(shot.n)}</b>${clip ? esc(shot.title) : "待生成"}</span></a>`; }).join("")}</div>`;
}

function bindFilm(C) {
  const video = $("#film");
  const tl = $("#tl");
  if (!tl) return;
  const hit = $("#tlhit");
  const head = $("#playhead");
  const total = C.cutTotal || 1;
  // The rendered film can differ from the declared total by a few frames; scale to what plays.
  const scale = () => (video && video.duration && Number.isFinite(video.duration) ? video.duration / total : 1);
  let last = null;
  const place = (t) => {
    head.style.left = `${64 + (Math.min(total, t) / total) * (tl.clientWidth - 64)}px`;
    const cut = C.cuts.find((item) => t >= item.at && t < item.at + item.sec) || C.cuts.at(-1);
    const now = $("#nowTime");
    if (now) now.textContent = `${fmt(t)} / ${fmt(total)}`;
    if (cut && cut.id !== last) {
      last = cut.id;
      const label = $("#nowCut");
      if (label) label.textContent = `CUT ${cut.n} · ${cut.title}`;
      $$(".cuts tr.on, .tl-cut.on").forEach((node) => node.classList.remove("on"));
      document.getElementById(`r-${cut.id}`)?.classList.add("on");
      $(`.tl-cut[data-cut="${CSS.escape(cut.id)}"]`)?.classList.add("on");
      if (video && !video.paused) document.getElementById(`r-${cut.id}`)?.scrollIntoView({ block: "nearest" });
    }
  };
  const sync = () => place(video ? video.currentTime / scale() : 0);
  const seek = (t) => { if (video) { video.currentTime = t * scale(); } place(t); };
  if (video) ["timeupdate", "seeked", "loadedmetadata"].forEach((name) => video.addEventListener(name, sync));
  hit.addEventListener("click", (event) => { const box = hit.getBoundingClientRect(); seek(((event.clientX - box.left) / box.width) * total); });
  $$(".cuts tr[data-cut], .tl-cut").forEach((node) => node.addEventListener("click", (event) => {
    if (event.target.closest("a")) return;
    const cut = C.cuts.find((item) => item.id === node.dataset.cut);
    if (cut) seek(cut.at + 0.01);
  }));
  const focus = parseRoute(location.hash).q.get("cut");
  const wanted = C.cuts.find((item) => item.id === focus);
  if (wanted) { seek(wanted.at + 0.01); document.getElementById(`r-${wanted.id}`)?.scrollIntoView({ block: "center" }); }
  else sync();
}

/* ================================================================ review */

function qcRegistryHtml(shots = []) {
  const categories = [["assets", "資產登錄"], ["generations", "生成記錄"], ["reviews", "QC 審閱記錄"], ["issues", "QC 問題記錄"]];
  const records = [];
  for (const shot of shots || []) for (const [key, label] of categories) {
    for (const record of shot?.[key] || []) records.push({ shot, label, record });
  }
  if (!records.length) return "";
  return `<section class="card qc-registry"><h3>QC 登錄（唯讀，非當前驗證結論）</h3><p class="muted small">以下是已存在的 QA/QC 紀錄；紀錄中的狀態不代表本次審查通過。</p><div class="qc-items">${records.map(({ shot, label, record }, index) => {
    const source = typeof record?.source_file === "string" ? record.source_file : typeof shot?.source_file === "string" ? shot.source_file : "";
    const basename = source.split(/[\\/]/).pop();
    const title = record?.title || record?.name || record?.summary || `${label} ${index + 1}`;
    const sourceLink = source ? `<a class="btn sm ghost" href="#/file?${esc(query({ path: source }))}">查看來源：${esc(basename)}</a>` : "";
    const safeRecord = (value) => Array.isArray(value) ? value.map(safeRecord) : value && typeof value === "object"
      ? Object.fromEntries(Object.entries(value).filter(([key]) => !/path|source_file|hash|checksum/i.test(key)).map(([key, child]) => [key, safeRecord(child)]))
      : value;
    return `<details class="qc-record"><summary><span>${esc(shot?.id || "鏡頭")}</span> · ${esc(label)} · ${esc(title)}</summary><div class="qc-record-body"><pre>${esc(JSON.stringify(safeRecord(record), null, 2) ?? String(record))}</pre>${sourceLink}</div></details>`;
  }).join("")}</div></section>`;
}

function viewReview(row, E, arg) {
  const qcHtml = qcRegistryHtml(E.board?.shots || []);
  if (!row.has.review) return qcHtml ? `<div class="wrap" data-view="review"><div class="head"><div><h2>審查與 QC 登錄</h2><div class="sub">QC 登錄為唯讀紀錄，不能當成正式審查結論</div></div></div>${qcHtml}${missingView(row, "review")}</div>` : missingView(row, "review");
  const review = E.review;
  const hooks = review?.deleted_hooks || [];
  if (!review || (!review.findings.length && !hooks.length && !review.verdict)) {
    return `<div class="wrap" data-view="review"><div class="head"><div><h2>審查意見</h2><div class="sub">按原文顯示；修改請交給助手</div></div><div class="actions">${editButton(E.docs.review)}</div></div>${qcHtml}${problemNotices(E)}<div data-raw="${esc(E.docs.review)}"><div class="loading">正在讀取原文…</div></div></div>`;
  }
  const C = context(E);
  const counts = { must: 0, should: 0, could: 0 };
  review.findings.forEach((finding) => counts[finding.sev]++);
  if (arg && S.reviewFilter !== "all" && review.findings.some((finding) => finding.id === arg && finding.sev !== S.reviewFilter)) {
    S.reviewFilter = "all";
  }
  const list = review.findings.filter((finding) => S.reviewFilter === "all" || finding.sev === S.reviewFilter);
  const where = (id) => {
    if (id.startsWith("SHOT-")) return `<a class="pill id" href="#/${esc(row.id)}/board/${esc(id)}">${icon("film")}鏡 ${esc(sceneShort(id))} ${esc(C.shot[id]?.title || "")}</a>`;
    if (id.startsWith("CUT-")) return `<a class="pill id" href="#/${esc(row.id)}/film?cut=${esc(id)}">${icon("sfx")}剪輯 ${esc(sceneShort(id))}</a>`;
    return `<a class="pill id" href="#/${esc(row.id)}/script/${esc(id)}">${icon("text")}劇本 ${esc(sceneShort(id))}</a>`;
  };
  const tone = review.verdictTone || (/可以繼續/.test(review.verdict) ? "ok" : /待補/.test(review.verdict) ? "warn" : "bad");
  const hooksHtml = hooks.length ? `<article class="card finding should" id="f-deleted-hooks"><span class="stripe"></span><div class="fb">
    <div class="fh"><span class="tag should">亮點保護</span><span class="t">被刪的強鉤子</span></div>
    <div>${hooks.map((hook) => `<p>${esc(hook)}</p>`).join("")}</div>
  </div></article>` : "";
  return `<div class="wrap" data-view="review">
    <div class="head"><div><h2>審查意見</h2><div class="sub">只讀；修改請交給助手</div></div><div class="actions">${editButton(E.docs.review)}</div></div>
    ${problemNotices(E)}
    ${qcHtml}
    <section class="card verdict"><span class="vv ${esc(tone)}">${icon(tone === "ok" ? "check" : "alert")}${esc(review.verdict || "已審查")}</span><span class="vm">${review.independent ? "獨立審查" : "自檢"}${review.scope ? ` · 範圍：${esc(review.scope)}` : ""}</span>
      ${review.findings.length ? `<div class="seg">${[["all", `全部 ${review.findings.length}`], ["must", `必須改 ${counts.must}`], ["should", `建議改 ${counts.should}`], ["could", `可以更好 ${counts.could}`]].map(([key, label]) => `<button type="button" data-rf="${key}" aria-pressed="${S.reviewFilter === key}">${label}</button>`).join("")}</div>` : ""}</section>
    ${list.map((finding) => { const shots = finding.targets.filter((id) => C.shot[id]);
      return `<article class="card finding ${finding.sev}" id="f-${esc(finding.id)}"><span class="stripe"></span><div class="fb">
      <div class="fh"><span class="tag ${finding.sev}">${SEVERITY_LABEL[finding.sev]}</span><span class="t">${esc(finding.title)}</span><span class="rid">${esc(finding.id)}</span></div>
      <div class="fgrid"><span class="k">在哪</span><div class="pills">${finding.targets.map(where).join("") || esc(finding.where || "—")}</div>
        <span class="k">看到了什麼</span><div>${esc(finding.evidence || "—")}</div>
        <span class="k">為什麼要改</span><div>${esc(finding.impact || "—")}</div>
        <span class="k">改成什麼樣</span><div class="fix">${esc(finding.fix || "—")}</div></div>
      <div class="ff"><button class="btn sm primary" type="button" data-copy="${esc(`請按 ${row.id} 審查意見 ${finding.id}（${finding.title}）修改：${finding.fix}`)}" data-copy-label="已複製，去對話裡傳送">${icon("copy")}複製修改請求</button>
        ${shots.length ? `<span class="mini-thumbs">${shots.map((id) => `<a href="#/${esc(row.id)}/board/${esc(id)}" title="${esc(id)}">${thumb(C, C.shot[id], false)}</a>`).join("")}</span>` : ""}</div>
    </div></article>`; }).join("")}
    ${hooksHtml}
  </div>`;
}

/* ================================================================ files and editor */

function viewFiles() {
  const visible = (S.files || []).filter((file) => creatorSection(file.path, S.status?.ownership));
  const groups = new Map();
  for (const file of visible) {
    const key = episodeName(file.path) || "全劇";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(file);
  }
  const order = [...groups.keys()].sort((a, b) => (a === "全劇" ? -1 : b === "全劇" ? 1 : a.localeCompare(b, "zh-TW", { numeric: true })));
  const rank = (file) => SECTION_ORDER.indexOf(creatorSection(file.path, S.status?.ownership));
  return `<div class="wrap" data-view="files"><div class="head"><div><h2>全部檔案</h2><div class="sub">${visible.length} 份 · 系統內部檔案不在這裡顯示</div></div></div>
    ${(S.tree?.warnings || []).length ? '<div class="notice">部分內容暫時無法讀取，已列出其餘檔案。</div>' : ""}
    ${order.map((key) => `<div class="file-group"><h4>${esc(key)}</h4><div class="card files-list">${groups.get(key).sort((a, b) => rank(a) - rank(b) || fileLabel(a.path).localeCompare(fileLabel(b.path), "zh-TW")).map(fileRow).join("")}</div></div>`).join("") || '<div class="empty"><p>專案裡還沒有創作檔案。</p></div>'}
  </div>`;
}

function viewFile(q) {
  const path = q.get("path") || "";
  const isHtml = /\.html?$/i.test(path);
  const file = (S.files || []).find((item) => item.path === path);
  const back = episodeName(path) ? `#/${episodeName(path)}` : "#/files";
  return `<div class="wrap" data-view="file"><div class="head"><div><div class="eyebrow">${esc([episodeName(path) || "全劇", CONTENT_META[creatorSection(path)]?.label].filter(Boolean).join(" · "))}</div><h2>${isHtml ? "HTML 原始碼（唯讀）" : esc(fileLabel(path))}</h2><div class="sub mono">${esc(pathSegments(path).at(-1) || "")}</div></div>
    <div class="actions"><a class="btn ghost" href="${esc(back)}">${icon("left")}返回</a>${file && creatorEditable(file) ? editButton(path) : ""}</div></div>
    ${isHtml ? '<div class="notice" role="note">以純文字來源檢視，不會執行其中的程式碼或載入遠端內容。</div>' : ""}
    <div data-raw="${esc(path)}" data-kind="${file?.type === "media" ? "media" : "text"}"><div class="loading">正在讀取…</div></div></div>`;
}

async function fillRaw(sequence) {
  for (const host of $$("[data-raw]")) {
    const path = host.dataset.raw;
    if (!path) { host.innerHTML = '<p class="muted">找不到這份檔案。</p>'; continue; }
    try {
      if (host.dataset.kind === "media") {
        const info = await api(`/api/media?${query({ project: S.project, path })}`);
        if (sequence !== S.renderSequence) return;
        const box = element("div", "media-view");
        const node = document.createElement(info.kind === "video" ? "video" : info.kind === "audio" ? "audio" : "img");
        node.src = info.contentUrl;
        if (info.kind === "image") node.alt = fileLabel(path);
        else { node.controls = true; node.preload = "metadata"; if (info.kind === "video") node.playsInline = true; }
        box.append(node, element("span", "muted small", formatBytes(info.size)));
        host.replaceChildren(box);
      } else {
        const data = await api(`/api/file?${query({ project: S.project, path })}`);
        if (sequence !== S.renderSequence) return;
        host.replaceChildren(renderDocument(path, data.content));
      }
    } catch (error) {
      if (sequence !== S.renderSequence) return;
      host.innerHTML = `<div class="notice danger">${icon("alert")}<span>${esc(friendlyFailure(error.message))}</span></div>`;
    }
  }
}

function viewEdit(q) {
  const path = q.get("path") || "";
  return `<div class="wrap" data-view="edit"><div class="editbar" id="editbar">${icon("edit")}<span>正在編輯 <b class="mono">${esc(pathSegments(path).at(-1) || "")}</b>。儲存只寫回這一份 Markdown，不會觸發任何生成。</span>
      <span class="actions"><span class="state" id="editState">正在讀取…</span><a class="btn sm ghost" href="${esc(q.get("back") || viewForPath(path))}">返回</a><button class="btn sm primary" type="button" id="saveButton" data-act="save" disabled>儲存 <kbd>⌘S</kbd></button></span></div>
    <div id="editNotice"></div>
    <label class="sr-only" for="editor">原文</label><textarea class="editor" id="editor" spellcheck="false" disabled></textarea></div>`;
}

function findHeadingOffset(content, at) {
  const target = String(at || "").trim();
  if (!target) return -1;
  const text = String(content || "");
  const escaped = target.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const headingRe = new RegExp(`^##[ \\t\\u3000]+${escaped}(?=[ \\t\\u3000·\\r\\n]|$)`);
  let fence = null;
  let inComment = false;
  let offset = 0;
  for (const rawLine of text.split("\n")) {
    const lineStart = offset;
    offset += rawLine.length + 1;
    const line = rawLine.endsWith("\r") ? rawLine.slice(0, -1) : rawLine;
    if (fence !== null) {
      if (fence.test(line)) fence = null;
      continue;
    }
    let scan = line;
    if (inComment) {
      const closeAt = scan.indexOf("-->");
      if (closeAt === -1) continue;
      inComment = false;
      scan = scan.slice(closeAt + 3);
    }
    const fenceOpen = /^\s*(`{3,}|~{3,})/.exec(scan);
    if (fenceOpen) {
      const ch = fenceOpen[1][0];
      fence = new RegExp(`^\\s*${ch}{${fenceOpen[1].length},}\\s*$`);
      continue;
    }
    let stripped = scan;
    for (let prev = null; prev !== stripped;) {
      prev = stripped;
      stripped = stripped.replace(/<!--[\s\S]*?-->/g, "");
    }
    const openAt = stripped.indexOf("<!--");
    if (openAt !== -1) {
      inComment = true;
      stripped = stripped.slice(0, openAt);
    }
    if (headingRe.test(stripped) && line.trimStart().startsWith("##")) {
      return lineStart + line.indexOf("##");
    }
  }
  return -1;
}

async function openEditor(q, sequence) {
  const path = q.get("path") || "";
  const at = q.get("at") || "";
  try {
    const data = await api(`/api/file?${query({ project: S.project, path })}`);
    if (sequence !== S.renderSequence) return;
    const editable = Boolean(data.writable ?? data.editable);
    S.edit = { path, version: data.version, original: data.content, dirty: false, saving: false, writable: editable };
    const editor = $("#editor");
    editor.value = data.content;
    editor.disabled = !editable;
    editor.addEventListener("input", () => setDirty(editor.value !== S.edit.original));
    setDirty(false);
    $("#editState").textContent = editable ? "已載入" : "只讀";
    if (at) {
      const fullText = editor.value;
      const index = findHeadingOffset(fullText, at);
      if (index >= 0) {
        // Measure the wrapped height of everything above the heading, so the
        // shot lands at the top however long its preceding lines wrap.
        editor.value = fullText.slice(0, index);
        const above = editor.scrollHeight;
        editor.value = fullText;
        editor.focus({ preventScroll: true });
        editor.setSelectionRange(index, index);
        editor.scrollTop = Math.max(0, above - 40);
      }
    } else if (editable) editor.focus({ preventScroll: true });
  } catch (error) {
    if (sequence !== S.renderSequence) return;
    $("#editState").textContent = "";
    $("#editNotice").innerHTML = `<div class="notice danger">${icon("alert")}<span>${esc(friendlyFailure(error.message))}</span></div>`;
  }
}

function setDirty(dirty) {
  if (!S.edit) return;
  S.edit.dirty = dirty;
  const save = $("#saveButton");
  if (save) save.disabled = !S.edit.writable || S.edit.saving || !dirty;
  const state = $("#editState");
  if (state && !S.edit.saving) state.textContent = dirty ? "有未儲存的修改" : state.textContent === "有未儲存的修改" ? "已儲存" : state.textContent;
  document.title = `${dirty ? "● " : ""}${document.title.replace(/^● /, "")}`;
}

async function save() {
  const edit = S.edit;
  if (!edit || !edit.dirty || edit.saving || !edit.writable) return;
  const editor = $("#editor");
  const content = editor.value;
  edit.saving = true;
  setDirty(true);
  $("#editState").textContent = "正在儲存…";
  try {
    const result = await api(`/api/file?${query({ project: S.project, path: edit.path })}`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project: S.project, path: edit.path, content, expectedVersion: edit.version }),
    });
    if (S.edit !== edit) return;
    // Structured views must never show the text from before this save.
    S.episodes = new Map();
    edit.version = result.version;
    edit.original = content;
    edit.saving = false;
    $("#editNotice").innerHTML = "";
    $("#editState").textContent = `已儲存 · ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    setDirty(!savedContentIsCurrent(content, editor.value));
    toast("已儲存，頁面內容已同步更新。");
    try { await refreshProject(); } catch (_error) { toast("內容已儲存，但重新整理失敗，請稍後重試"); }
  } catch (error) {
    if (S.edit !== edit) return;
    edit.saving = false;
    setDirty(true);
    $("#editState").textContent = "沒有儲存";
    const conflict = error.status === 409 || /changed since it was opened/.test(error.message);
    $("#editNotice").innerHTML = `<div class="notice danger" id="saveError" data-conflict="${conflict ? 1 : 0}">${icon("alert")}<span>${esc(conflict ? "這份檔案在別處改過了，你的修改沒有儲存。先複製你的修改，再載入最新版本合併。" : friendlyFailure(error.message))}</span>
      ${conflict ? `<span class="actions"><button class="btn sm" type="button" data-act="copy-draft">${icon("copy")}複製我的修改</button><button class="btn sm primary" type="button" data-act="reload-latest">載入最新版本</button></span>` : ""}</div>`;
  }
}

/* ================================================================ search */

function openPalette(initial = "") {
  const host = $("#palette");
  const route = parseRoute(location.hash);
  S.palette.scope = route.ep ? "ep" : "series";
  S.palette.ep = route.ep;
  host.hidden = false;
  host.innerHTML = `<div class="pal"><div class="pal-in">${icon("search")}<input id="palq" placeholder="搜尋臺詞、鏡頭、設定、提示詞、審查…" autocomplete="off" aria-label="搜尋"><kbd>esc</kbd></div>
    <div class="pal-scope">${route.ep ? `<button class="pill ${S.palette.scope === "ep" ? "on" : ""}" type="button" data-scope="ep">本集 ${esc(route.ep)}</button>` : ""}<button class="pill ${S.palette.scope === "series" ? "on" : ""}" type="button" data-scope="series">全劇</button></div>
    <div class="pal-res" id="palres" role="listbox"></div>
    <div class="pal-foot"><span>↑↓ 選擇</span><span>↵ 開啟</span><span>搜尋只讀，不改任何檔案</span></div></div>`;
  const input = $("#palq");
  input.value = initial;
  input.focus();
  input.addEventListener("input", () => { S.palette.sel = 0; scheduleSearch(); });
  input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      S.palette.sel = Math.max(0, Math.min(S.palette.items.length - 1, S.palette.sel + (event.key === "ArrowDown" ? 1 : -1)));
      paintResults(input.value, true);
    }
    if (event.key === "Enter" && S.palette.items[S.palette.sel]) pick(S.palette.items[S.palette.sel]);
  });
  scheduleSearch(0);
}

function scheduleSearch(delay = 140) {
  clearTimeout(S.palette.timer);
  S.palette.timer = setTimeout(runSearch, delay);
}

async function runSearch() {
  const input = $("#palq");
  if (!input) return;
  const text = input.value.trim();
  const sequence = ++S.palette.sequence;
  if (!text) { S.palette.items = []; paintResults(""); return; }
  try {
    const params = { project: S.project, q: text, scope: S.palette.scope };
    if (S.palette.scope === "ep" && S.palette.ep) params.ep = S.palette.ep;
    const data = await api(`/api/search?${query(params)}`);
    if (sequence !== S.palette.sequence) return;
    S.palette.items = data.hits;
    paintResults(text);
  } catch (error) {
    if (sequence !== S.palette.sequence) return;
    $("#palres").innerHTML = `<div class="pal-empty">${esc(friendlyFailure(error.message))}</div>`;
  }
}

function snippet(hit) {
  const text = hit.snippet;
  const at = hit.at;
  if (at < 0) return esc(text);
  return `${hit.clipped ? "…" : ""}${esc(text.slice(0, at))}<mark>${esc(text.slice(at, at + hit.len))}</mark>${esc(text.slice(at + hit.len))}`;
}

function paintResults(text, keepScroll = false) {
  const host = $("#palres");
  if (!host) return;
  if (!text) {
    host.innerHTML = '<div class="pal-g">可以搜</div><div class="pal-hint">一句臺詞 · 鏡號「014」· 人物名 · 道具 · 畫面文字 · 審查意見</div>';
    return;
  }
  const hits = S.palette.items;
  if (!hits.length) { host.innerHTML = `<div class="pal-empty">沒有找到「${esc(text)}」</div>`; return; }
  const groups = [...new Set(hits.map((hit) => hit.g))];
  host.innerHTML = groups.map((group) => `<div class="pal-g">${esc(group)}</div>${hits.map((hit, index) => ({ hit, index })).filter((item) => item.hit.g === group).map(({ hit, index }) => {
    const inTitle = hit.field !== "x";
    return `<div class="pal-item" role="option" data-i="${index}" aria-selected="${index === S.palette.sel}"><span class="w">${S.palette.scope === "series" ? `${esc(hit.ep)} · ` : ""}${hit.field === "w" ? snippet(hit) : esc(hit.w)}</span><span class="x">${hit.field === "t" ? snippet(hit) : esc(hit.t)}${inTitle ? "" : `<span class="sn">${snippet(hit)}</span>`}</span></div>`;
  }).join("")}`).join("");
  $$(".pal-item", host).forEach((node) => node.addEventListener("click", () => pick(S.palette.items[Number(node.dataset.i)])));
  const selected = $('.pal-item[aria-selected="true"]', host);
  if (keepScroll && selected) selected.scrollIntoView({ block: "nearest" });
}

function hitHref(hit) {
  const base = `#/${hit.ep}`;
  if (hit.view === "board") return `${base}/board/${hit.arg}`;
  if (hit.view === "script") return `${base}/script/${hit.arg}`;
  if (hit.view === "settings") return `${base}/settings/${encodeURIComponent(settingKey(hit.w, hit.arg))}`;
  if (hit.view === "prompts") return `${base}/prompts/${hit.arg}?id=${encodeURIComponent(hit.id)}`;
  if (hit.view === "review") return `${base}/review/${hit.arg}`;
  if (hit.view === "film") return `${base}/film?cut=${encodeURIComponent(hit.cut || "")}`;
  return base;
}

function pick(hit) {
  closePalette();
  S.pendingLine = hit.line || null;
  go(hitHref(hit));
}
const closePalette = () => { const host = $("#palette"); host.hidden = true; host.innerHTML = ""; };

/* ================================================================ render */

function applyCss(root) {
  // Geometry goes through the CSSOM, which the page's CSP allows; inline style attributes it does not.
  for (const node of $$("[data-css]", root)) {
    node.style.cssText = node.dataset.css;
    node.removeAttribute("data-css");
  }
}

function go(hash) {
  if (location.hash === hash) render();
  else location.hash = hash;
}

function showError(message) {
  $("#view").innerHTML = `<div class="wrap"><div class="notice danger" id="notices">${icon("alert")}<span>${esc(message)}</span></div></div>`;
  $("#view").dataset.state = "error";
}

async function render() {
  const sequence = ++S.renderSequence;
  const route = parseRoute(location.hash);
  const tablePath = route.view === "board" ? route.q.get("editTable") : null;
  if (tablePath !== null) S.layout = "list";
  closeMenus();
  if (!S.series) return;
  const view = $("#view");
  if (S.edit?.kind === "board" ? tablePath !== S.edit.path : route.page !== "edit") S.edit = null;
  view.dataset.state = "loading";
  let E = null;
  const row = route.ep ? rowById(route.ep) : null;
  if (route.page === "episode" && row) {
    if (!S.episodes.has(row.id)) {
      renderTop(route);
      view.innerHTML = '<div class="loading">正在讀取這一集…</div>';
    }
    try { E = await loadEpisode(row.id); }
    catch (error) { if (sequence === S.renderSequence) showError(friendlyFailure(error.message)); return; }
    if (sequence !== S.renderSequence) return;
  }
  renderTop(route);
  let html;
  if (route.page === "files") html = viewFiles();
  else if (route.page === "file") html = viewFile(route.q);
  else if (route.page === "edit") html = viewEdit(route.q);
  else if (route.page === "episode" && !row) html = `<div class="wrap"><div class="empty"><h3>沒有 ${esc(route.ep)} 這一集</h3><p>它可能已被移動或改名。</p><a class="btn" href="#/">回到全劇</a></div></div>`;
  else if (route.page === "episode" && row.legacy) html = viewLegacyEpisode(row);
  else if (route.page === "episode") {
    const args = [row, E, route.arg, route.q];
    switch (route.view) {
      case "script": html = viewScript(...args); break;
      case "settings": html = viewSettings(...args); break;
      case "board": html = tablePath === null ? viewBoard(...args) : viewBoardEditor(row, E, tablePath); break;
      case "prompts": html = viewPrompts(...args); break;
      case "film": html = viewFilm(...args); break;
      case "review": html = viewReview(...args); break;
      default: html = viewEpisode(...args);
    }
  } else html = viewOverview();
  view.innerHTML = html;
  applyCss(view);
  applyCss($("#topbar"));
  const viewLabel = VIEWS.find((item) => item.key === route.view)?.label || "";
  document.title = `${route.ep ? `${route.ep} ${viewLabel} · ` : ""}《${creatorTitle(S.series.title)}》· 短劇創作臺`;
  renderInspector(row, E, route.view === "board" && tablePath === null ? route.arg : null);
  applyCss($("#inspector"));
  if (route.page === "episode" && route.view === "film" && E) bindFilm(context(E));
  if (route.page === "edit") await openEditor(route.q, sequence);
  if (tablePath) await openBoardEditor(tablePath, sequence);
  if (sequence !== S.renderSequence) return;
  view.dataset.route = location.hash || "#/";
  view.dataset.state = "ready";
  afterRender(route);
  await fillRaw(sequence);
}

function afterRender(route) {
  let node = null;
  if (route.view === "script" && route.arg) node = document.getElementById(route.arg);
  if (route.view === "board" && route.arg) node = document.getElementById(`c-${route.arg}`);
  if (route.view === "settings" && route.arg) {
    node = document.getElementById(`a-${route.arg}`) || $(`.asset[data-entry="${CSS.escape(route.arg)}"]`);
  }
  if (route.view === "review" && route.arg) node = document.getElementById(`f-${route.arg}`);
  if (route.view === "prompts" && route.q.get("id")) node = document.getElementById(`p-${route.q.get("id")}`);
  if (S.pendingLine) {
    const line = $$("[data-line]").find((item) => item.dataset.line === S.pendingLine);
    if (line) { node = line; line.classList.add("hl"); }
    S.pendingLine = null;
  }
  if (node) {
    const target = node;
    requestAnimationFrame(() => {
      target.scrollIntoView({ block: route.view === "board" ? "nearest" : "start" });
      if (!target.classList.contains("hl")) { target.classList.add("flash"); setTimeout(() => target.classList.remove("flash"), 1300); }
    });
  } else if (!(route.view === "board" && route.arg) && route.page !== "edit") scrollTo(0, 0);
}

function toast(message) {
  const host = $("#toast");
  host.textContent = message;
  host.classList.add("show");
  clearTimeout(host.hideTimer);
  host.hideTimer = setTimeout(() => host.classList.remove("show"), 2400);
}

/* ================================================================ events */

async function onClick(event) {
  const node = event.target;
  if (!node.closest("#epMenu") && !node.closest("#epMenuBtn")) closeMenus();
  if (node.closest("#epMenuBtn")) { episodeMenu(node.closest("#epMenuBtn")); return; }
  if (node.id === "palette") { closePalette(); return; }
  if (node.id === "scrim") { go($("#inspector").dataset.back || location.hash.split("/SHOT-")[0]); return; }
  const scope = node.closest("[data-scope]");
  if (scope) { S.palette.scope = scope.dataset.scope; $$(".pal-scope .pill").forEach((pill) => pill.classList.toggle("on", pill === scope)); S.palette.sel = 0; scheduleSearch(0); return; }
  const copy = node.closest("[data-copy]");
  if (copy) {
    const copied = await writeClipboard(copy.dataset.copy);
    if (copy.dataset.key) {
      S.copied.add(copy.dataset.key);
      local.set(`copied.${S.project}`, [...S.copied]);
    }
    toast(copied ? (copy.dataset.copyLabel || `已複製 · ${copy.dataset.copy.length} 字元`) : "瀏覽器拒絕了剪貼簿，請手動選中複製");
    if (copy.dataset.key) {
      const route = parseRoute(location.hash);
      const next = copy.dataset.next ? copy.dataset.key : null;
      await render();
      if (next) {
        const domId = next.startsWith("ckf-") ? `${next.slice(4)}-closing` : next.replace(/^kf-/, "");
        document.getElementById(`p-${domId}`)?.scrollIntoView({ block: "center" });
      }
      if (route.view !== "prompts") $(`#inspector [data-key="${CSS.escape(copy.dataset.key)}"]`)?.focus();
    }
    return;
  }
  const jump = node.closest("[data-go]");
  if (jump && jump.dataset.go && !jump.disabled && !node.closest("a")) { go(jump.dataset.go); return; }
  const nav = node.closest("[data-shot-nav]");
  if (nav && nav.dataset.shotNav) { go(shotHref(nav.dataset.shotNav)); return; }
  const action = node.closest("[data-act]")?.dataset.act;
  if (action === "search") { openPalette(); return; }
  if (action === "theme") { S.theme = isDark() ? "light" : "dark"; local.set("theme", S.theme); applyTheme(); renderTop(parseRoute(location.hash)); return; }
  if (action === "save") { save(); return; }
  if (action === "save-board") { saveBoard(); return; }
  if (["board-add", "board-up", "board-down", "board-delete"].includes(action)) {
    changeBoardRows(node.closest("[data-act]"), action);
    return;
  }
  if (action === "reload-board") {
    if (!confirm("捨棄草稿並載入來源檔的最新版本？")) return;
    S.edit = null;
    render();
    return;
  }
  if (action === "copy-board") {
    const line = (cells) => `| ${cells.map((cell) => cell.replace(/\|/g, "\\|").replace(/\n/g, "<br>")).join(" | ")} |`;
    const text = S.edit.tables.map((table) => [line(SHOT_COLUMNS), line(SHOT_COLUMNS.map(() => "---")),
      ...table.groups.flatMap((group) => [...group.rows.map((row) => line(row.cells)), ...(group.summary ? [line(group.summary)] : [])])
    ].join("\n")).join("\n\n");
    toast(await writeClipboard(text) ? "已複製表格草稿" : "無法存取剪貼簿，請手動複製修改內容。");
    return;
  }
  if (action === "close-ins") { go($("#inspector").dataset.back); return; }
  if (action === "copy-draft") { const ok = await writeClipboard($("#editor").value); toast(ok ? "已複製你的修改" : "瀏覽器拒絕了剪貼簿，請手動選中複製"); return; }
  if (action === "reload-latest") {
    if (!confirm("載入最新版本會丟掉編輯框裡還沒儲存的修改。確定嗎？")) return;
    S.edit.dirty = false;
    render();
    return;
  }
  if (action === "clear-copied") {
    const tab = node.closest("[data-act]").dataset.tab;
    const keys = new Set($$(".pcard").map((card) => card.dataset.key));
    for (const key of [...S.copied]) if (keys.has(key)) S.copied.delete(key);
    local.set(`copied.${S.project}`, [...S.copied]);
    if (tab) render();
    return;
  }
  if (action === "expand") { node.closest("[data-act]").classList.toggle("clamp"); return; }
  const layout = node.closest("[data-layout]");
  if (layout) { S.layout = layout.dataset.layout; local.set("layout", S.layout); render(); return; }
  const filter = node.closest("[data-rf]");
  if (filter) {
    S.reviewFilter = filter.dataset.rf;
    const route = parseRoute(location.hash);
    if (route.view === "review" && route.arg && typeof history !== "undefined" && typeof history.replaceState === "function") {
      history.replaceState(null, "", `#/${route.ep}/review`);
      S.lastHash = location.hash;
    }
    render();
    return;
  }
  const shot = node.closest("[data-shot]");
  if (shot && shot.dataset.shot && !node.closest("a") && !node.closest("video")) go(shotHref(shot.dataset.shot));
}

function shotHref(id) {
  const route = parseRoute(location.hash);
  const qs = location.hash.includes("?") ? `?${location.hash.split("?")[1]}` : "";
  return `#/${route.ep}/board/${id}${qs}`;
}

function onKey(event) {
  const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName || "");
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); openPalette(); return; }
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "s") {
    if (S.edit) { event.preventDefault(); if (S.edit.kind === "board") saveBoard(); else save(); }
    return;
  }
  if (event.key === "Escape") {
    if (!$("#palette").hidden) { closePalette(); return; }
    if (!$("#inspector").hidden) { go($("#inspector").dataset.back); return; }
  }
  if (event.key === "/" && !typing && $("#palette").hidden) { event.preventDefault(); openPalette(); return; }
  const route = parseRoute(location.hash);
  if (route.view === "board" && route.arg && !typing && $("#palette").hidden && ["ArrowRight", "ArrowLeft", "j", "k"].includes(event.key)) {
    const E = S.episodes.get(route.ep);
    const shots = E?.board?.shots || [];
    const index = shots.findIndex((shot) => shot.id === route.arg);
    const next = shots[index + (event.key === "ArrowRight" || event.key === "j" ? 1 : -1)];
    if (next) go(shotHref(next.id));
  }
  if (event.key === "Enter" && event.target.classList?.contains("shot")) event.target.click();
}

function onHover(event) {
  const node = event.target.closest?.("[data-tip]");
  const tip = $("#tip");
  if (!node) { tip.hidden = true; return; }
  tip.replaceChildren();
  if (node.dataset.tipB) tip.append(element("b", "", node.dataset.tipB));
  tip.append(document.createTextNode(node.dataset.tip));
  tip.hidden = false;
  const box = node.getBoundingClientRect();
  tip.style.left = `${Math.min(innerWidth - tip.offsetWidth - 8, Math.max(8, box.left + box.width / 2 - tip.offsetWidth / 2))}px`;
  tip.style.top = `${Math.max(8, box.top - tip.offsetHeight - 8)}px`;
}

function onHashChange() {
  if (S.edit?.kind === "board" && S.edit.saving) {
    history.replaceState(null, "", S.lastHash);
    return;
  }
  if (S.edit?.dirty && !confirm("當前修改還沒有儲存，確認離開嗎？")) {
    history.replaceState(null, "", S.lastHash);
    return;
  }
  S.lastHash = location.hash;
  render();
}

async function selectProject(id) {
  if (S.edit?.kind === "board" && S.edit.saving) return;
  if (S.edit?.dirty && !confirm("當前修改還沒有儲存，確認離開嗎？")) { render(); return; }
  S.edit = null;
  $("#view").dataset.state = "loading";
  try {
    await loadProject(id);
    S.status = await api(`/api/status?${query({ project: id })}`).catch(() => null);
    if (location.hash !== "#/") { S.lastHash = "#/"; history.replaceState(null, "", "#/"); }
    render();
  } catch (error) {
    showError(friendlyFailure(error.message));
  }
}

async function boot() {
  applyTheme();
  try {
    await establishSession();
    const data = await api("/api/projects");
    if (!data || !Array.isArray(data.projects)) throw new Error("invalid dashboard response");
    S.projects = data.projects;
    if (!S.projects.length) { $("#topbar").innerHTML = '<a class="zs-mark" href="#/" aria-label="短劇創作臺">場</a>'; showError("還沒有發現可開啟的短劇專案。"); return; }
    const remembered = local.get("project", null);
    const id = S.projects.some((project) => project.id === remembered) ? remembered : S.projects[0].id;
    await loadProject(id);
    S.status = await api(`/api/status?${query({ project: id })}`).catch(() => null);
    S.lastHash = location.hash;
    await render();
  } catch (error) {
    showError(friendlyFailure(error.message));
  }
}

/** Documents are written in the conversation, not here: reread them when the creator comes back to this tab. */
async function refreshOnReturn() {
  if (!S.project || parseRoute(location.hash).page === "edit") return;
  try { await refreshProject(); } catch (_error) { return; }
  render();
}

function start() {
  document.addEventListener("click", (event) => { onClick(event); });
  document.addEventListener("keydown", onKey);
  document.addEventListener("mouseover", onHover);
  document.addEventListener("change", (event) => { if (event.target.id === "projectSelect") selectProject(event.target.value); });
  addEventListener("hashchange", onHashChange);
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") refreshOnReturn(); });
  addEventListener("beforeunload", (event) => { if (S.edit?.dirty) { event.preventDefault(); event.returnValue = ""; } });
  if (typeof matchMedia === "function") matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { if (S.theme === "auto") renderTop(parseRoute(location.hash)); });
  boot();
}

if (hasDocument && typeof window !== "undefined" && !window.__DESK_NO_START__) start();
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    S,
    aspectLabel,
    context,
    creatorEditable,
    creatorProjection,
    creatorSection,
    creatorStatus,
    creatorTitle,
    entryLocks,
    episodeName,
    fileLabel,
    findHeadingOffset,
    formatBytes,
    friendlyFailure,
    friendlyKey,
    highlight,
    hitHref,
    keyframeCopyUnits,
    lineShot,
    lineShots,
    mediaKind,
    nextFor,
    parseRoute,
    parseSettingKey,
    pips,
    presence,
    readJsonLines,
    renderMarkdown,
    reviewNeedsAttention,
    reviewPassed,
    rhythmChecks,
    rhythmProfileRows,
    savedContentIsCurrent,
    seriesTodos,
    settingKey,
    stageState,
    viewEpisode,
    viewFilm,
    viewForPath,
    viewOverview,
    viewReview,
    viewSettings,
    OWNER_SECTIONS,
    SECTION_ORDER,
  };
}
