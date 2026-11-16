"use strict";
(() => {
  const $ = (selector, root = document) => root.querySelector(selector);
  const state = {
    project: null,
    episode: "",
    query: "",
    view: "table",
    selected: null,
    selectedKey: null,
    preview: null,
    file: null,
    draft: null,
    unsaved: false,
    conflict: "",
  };
  const app = $("#app");
  const detail = $("#detail");
  const topbar = $("#topbar");
  const toast = $("#toast");
  let token = new URLSearchParams(location.hash.slice(1)).get("token") || sessionStorage.getItem("film.token") || "";

  if (token) {
    sessionStorage.setItem("film.token", token);
    history.replaceState(null, "", location.pathname + location.search);
  }

  function node(tag, text, className) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = String(text ?? "");
    if (className) element.className = className;
    return element;
  }

  function button(label, onClick, className) {
    const element = node("button", label, className);
    element.type = "button";
    element.addEventListener("click", onClick);
    return element;
  }

  async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});
    if (token) headers.set("X-Film-Token", token);
    if (options.body) headers.set("Content-Type", "application/json");
    const response = await fetch(path, { ...options, headers, credentials: "same-origin" });
    let data;
    if ((response.headers.get("content-type") || "").includes("application/json")) {
      data = await response.json();
    } else if (!response.ok) {
      data = { error: `HTTP ${response.status}` };
    }
    if (!response.ok) {
      throw Object.assign(new Error(data?.error || `HTTP ${response.status}`), {
        status: response.status,
        data,
      });
    }
    return data;
  }

  function say(message) {
    toast.textContent = message;
    toast.style.display = "block";
    setTimeout(() => { toast.style.display = "none"; }, 3600);
  }

  function showLoadError(error) {
    app.replaceChildren(node(
      "div",
      `載入失敗：${error.message}。請確認本機服務仍在執行，然後重新整理。`,
      "error",
    ));
  }

  async function bootstrap() {
    try {
      if (token) {
        try {
          await api("/api/session", { method: "POST" });
        } catch (error) {
          if (error.status === 401) throw error;
        }
      }
      state.project = await api("/api/project");
      if (!currentEpisode()) state.episode = state.project.episodes?.[0]?.id ?? "";
      render();
    } catch (error) {
      showLoadError(error);
    }
  }

  function currentEpisode() {
    return state.project?.episodes?.find((episode) => String(episode.id) === String(state.episode)) || null;
  }

  function shots() {
    return currentEpisode()?.shots || [];
  }

  function valueText(value) {
    if (value == null) return "";
    const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
    return text.replace(/<br\s*\/?\s*>/gi, "\n");
  }

  function matchesSearch(value) {
    return !state.query || JSON.stringify(value).toLocaleLowerCase().includes(state.query.toLocaleLowerCase());
  }

  function filePath(file) {
    return typeof file === "string" ? file : file?.path;
  }

  function fileName(file) {
    return typeof file === "string" ? file : (file?.name || file?.path || "未命名文件");
  }

  function isReadableTextFile(file) {
    const path = filePath(file) || "";
    const kind = typeof file === "object" ? String(file.kind || "").toLowerCase() : "";
    if (["media", "grid", "package", "qc"].includes(kind)) return false;
    if (kind === "document") return true;
    return /\.(?:md|markdown|txt|csv)$/i.test(path);
  }

  function confirmDiscard() {
    return !state.unsaved || confirm("原文尚未儲存。繼續操作會放棄編輯內容，確定繼續？");
  }

  function render() {
    if (!state.project) return;
    const episode = currentEpisode();
    renderTopbar(episode);
    app.replaceChildren();

    const layout = node("div", undefined, "layout");
    const sidebar = node("aside", undefined, "sidebar");
    const content = node("section", undefined, "content");
    renderSidebar(sidebar, episode);
    renderOverview(content, episode);
    renderToolbar(content);

    if (state.file) {
      renderEditor(content);
    } else if (state.preview) {
      renderPreview(content);
    } else {
      renderShots(content);
    }
    layout.append(sidebar, content);
    app.append(layout);
  }

  function renderTopbar(episode) {
    topbar.replaceChildren();
    topbar.append(node("div", state.project.name || "八欄創作台", "brand"));
    const actions = node("div", undefined, "top-actions");
    const select = document.createElement("select");
    select.setAttribute("aria-label", "選擇集數");

    for (const item of state.project.episodes || []) {
      const option = node("option", item.name || item.id);
      option.value = item.id;
      option.selected = String(item.id) === String(state.episode);
      select.append(option);
    }
    select.addEventListener("change", () => {
      if (!confirmDiscard()) {
        select.value = state.episode;
        return;
      }
      state.episode = select.value;
      closeFileState();
      state.selected = null;
      render();
    });
    actions.append(select, button("文件", openFiles));
    topbar.append(actions);
  }

  function renderSidebar(sidebar, episode) {
    sidebar.append(node("div", "集數與文件", "side-title"));
    for (const item of state.project.episodes || []) {
      const active = episode && String(episode.id) === String(item.id);
      const control = button(
        `${item.name || item.id} · ${(item.shots || []).length} 鏡`,
        () => {
          if (!confirmDiscard()) return;
          state.episode = item.id;
          closeFileState();
          state.selected = null;
          render();
        },
        `navitem ${active ? "active" : ""}`,
      );
      sidebar.append(control);
    }

    sidebar.append(node("div", "分鏡宮格", "side-title"));
    for (const grid of episode?.grids || []) {
      const control = button(fileName(grid), () => openMedia(grid, true), "navitem");
      control.title = filePath(grid) || "";
      sidebar.append(control);
    }

    sidebar.append(node("div", "資料文件", "side-title"));
    const episodeId = episode ? String(episode.id) : "";
    const projectFiles = (state.project.files || []).filter((file) => {
      if (typeof file !== "object" || !file.episode) return true;
      const fileEpisode = String(file.episode);
      return fileEpisode === "project" || fileEpisode === episodeId;
    });
    const allFiles = [...projectFiles, ...(episode?.files || [])];
    const files = allFiles
      .filter((file, index, list) => list.findIndex((item) => filePath(item) === filePath(file)) === index)
      .filter(matchesSearch);
    for (const file of files) {
      const path = filePath(file);
      const control = button(fileName(file), () => openFileOrMedia(file), "navitem");
      control.title = path || "";
      sidebar.append(control);
    }
  }

  function renderOverview(content, episode) {
    const head = node("div", undefined, "overview");
    const title = node("div");
    title.append(
      node("h1", episode?.name || "專案總覽"),
      node("div", `共 ${shots().length} 個鏡頭 · ${episode?.files?.length || 0} 份文件`, "muted"),
    );
    const stats = node("div", undefined, "stats");
    const issues = (episode?.issues || []).length
      + (state.project.issues || []).length
      + shots().reduce((count, shot) => count + (shot.issues || []).length, 0);
    stats.append(
      node("span", `鏡頭 ${shots().length}`, "stat"),
      node("span", `待補 ${issues}`, "stat"),
      node("span", `文件 ${episode?.files?.length ?? (state.project.files || []).length}`, "stat"),
    );
    head.append(title, stats);
    content.append(head);
    if (episode) content.append(renderProgress(episode));

    for (const issue of [...(state.project.issues || []), ...(episode?.issues || [])]) {
      content.append(node("div", valueText(issue), "notice"));
    }
  }

  function renderProgress(episode) {
    const files = [
      ...(episode.files || []),
      ...(state.project.files || []).filter((file) => typeof file !== "object" || !file.episode || String(file.episode) === String(episode.id)),
    ];
    const uniqueFiles = files.filter((file, index, list) =>
      list.findIndex((item) => filePath(item) === filePath(file)) === index,
    );
    const hasDocument = (pattern) => uniqueFiles.some((file) => pattern.test(fileName(file)));
    const assets = shots().reduce((count, shot) => count + (shot.assets || []).length, 0);
    const reviews = shots().reduce((count, shot) => count + (shot.reviews || []).length, 0);
    const progress = node("section", undefined, "progress");
    progress.append(node("div", "分集進度", "side-title"));
    const items = [
      ["劇本", hasDocument(/劇本|腳本|script/i) ? "已有文件" : "未找到"],
      ["資產／QC登錄", `登錄${assets}筆`],
      ["分鏡", `${shots().length}鏡`],
      ["提示詞", hasDocument(/提示詞|prompt/i) ? "已有文件" : "未找到"],
      ["草圖", `${(episode.grids || []).length}張`],
      ["QA登錄", `登錄${reviews}筆`],
    ];
    for (const [label, status] of items) {
      const item = node("div", undefined, "progress-item");
      item.append(node("span", label), node("b", status));
      progress.append(item);
    }
    return progress;
  }

  function renderToolbar(content) {
    const toolbar = node("div", undefined, "toolbar");
    const search = document.createElement("input");
    search.type = "search";
    search.placeholder = "搜尋鏡頭或文件…";
    search.setAttribute("aria-label", "搜尋鏡頭或文件");
    search.value = state.query;
    search.addEventListener("input", () => {
      state.query = search.value;
      render();
      const nextSearch = $("input[type=search]");
      nextSearch?.focus();
      nextSearch?.setSelectionRange(nextSearch.value.length, nextSearch.value.length);
    });
    toolbar.append(
      search,
      button(state.view === "table" ? "卡片檢視" : "八欄表格", () => {
        state.view = state.view === "table" ? "cards" : "table";
        render();
      }),
      button("編輯目前文件…", openFiles),
    );
    content.append(toolbar);
  }

  function renderShots(content) {
    const filtered = shots().filter(matchesSearch);
    if (!filtered.length) {
      content.append(node(
        "div",
        shots().length ? "找不到符合的鏡頭。" : "目前沒有可顯示的鏡頭。",
        "empty",
      ));
      return;
    }
    content.append(state.view === "table" ? makeTable(filtered) : makeCards(filtered));
  }

  function makeTable(items) {
    const wrap = node("div", undefined, "table-wrap");
    const table = document.createElement("table");
    const header = document.createElement("thead");
    const headerRow = document.createElement("tr");
    for (const column of state.project.columns || []) headerRow.append(node("th", column));
    header.append(headerRow);
    table.append(header);

    const body = document.createElement("tbody");
    for (const shot of items) {
      const row = document.createElement("tr");
      row.tabIndex = 0;
      row.setAttribute("aria-label", `檢視鏡頭 ${shot.fields?.[state.project.columns?.[0]] || shot.id}`);
      row.addEventListener("click", () => showShot(shot));
      row.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          showShot(shot);
        }
      });
      for (const column of state.project.columns || []) {
        row.append(node("td", valueText(shot.fields?.[column])));
      }
      body.append(row);
    }
    table.append(body);
    wrap.append(table);
    return wrap;
  }

  function makeCards(items) {
    const grid = node("div", undefined, "cards");
    const columns = state.project.columns || [];
    for (const shot of items) {
      const card = button("", () => showShot(shot), "shotcard");
      card.append(node("strong", valueText(shot.fields?.[columns[0]] || shot.id)));
      for (const column of columns.slice(1)) {
        const line = node("p");
        line.append(node("b", `${column}：`), document.createTextNode(valueText(shot.fields?.[column])));
        card.append(line);
      }
      grid.append(card);
    }
    return grid;
  }

  function appendGroup(parent, title, items) {
    const section = node("section", undefined, "group");
    section.append(node("h3", `${title}（${items?.length || 0}）`));
    if (title.includes("QA")) {
      section.append(node("div", "以下為檔案中的登錄紀錄；此畫面不代表目前素材已通過驗證。", "muted"));
    }
    if (!items?.length) section.append(node("div", "沒有登錄資料。", "muted"));
    for (const item of items || []) {
      const record = node("div", undefined, "record");
      record.textContent = typeof item === "string" ? item : JSON.stringify(item, null, 2);
      section.append(record);
    }
    parent.append(section);
  }

  function mediaPath(path) {
    return `/api/media?${new URLSearchParams({ path: String(path || "") })}`;
  }

  function appendMedia(parent, item, isGrid = false) {
    const path = typeof item === "string" ? item : (item.path || item.file || item.png || item.source);
    if (!path) return;
    const extension = path.split(".").pop().toLowerCase();
    const source = mediaPath(path);
    let media;
    if (["png", "jpg", "jpeg", "webp", "gif"].includes(extension)) {
      media = node("img");
      media.src = source;
      media.alt = isGrid ? "分鏡 25 宮格預覽" : "專案圖片預覽";
      media.className = isGrid ? "grid-media" : "media";
    } else if (["mp4", "webm", "mov"].includes(extension)) {
      media = node("video");
      media.src = source;
      media.controls = true;
      media.className = "media";
    } else if (["wav", "mp3", "m4a", "aac", "flac", "opus"].includes(extension)) {
      media = node("audio");
      media.src = source;
      media.controls = true;
      media.className = "media";
    }
    if (media) parent.append(media);
  }

  function showShot(shot) {
    state.selected = shot;
    state.selectedKey = `${shot.source || ""}:${shot.row_index ?? ""}`;
    detail.replaceChildren();
    detail.hidden = false;
    const head = node("div", undefined, "detail-head");
    const firstColumn = state.project.columns?.[0];
    head.append(
      node("h2", `鏡頭 · ${valueText(shot.fields?.[firstColumn] || shot.id)}`),
      button("關閉", () => { detail.hidden = true; }),
    );
    detail.append(head);

    const source = node("div", undefined, "field");
    source.append(node("b", "來源文件"), node("span", shot.source || "未提供來源"));
    detail.append(source, button("開啟原文", () => loadFile(shot.source)));
    for (const column of state.project.columns || []) {
      const field = node("div", undefined, "field");
      field.append(node("b", column), node("div", valueText(shot.fields?.[column]), "text"));
      detail.append(field);
    }
    appendGroup(detail, "缺項／問題", shot.issues);
    appendGroup(detail, "資產登錄", shot.assets);
    appendGroup(detail, "生成群組登錄", shot.generations);
    appendGroup(detail, "QA 登錄紀錄", shot.reviews);

    for (const grid of currentEpisode()?.grids || []) {
      const section = node("section", undefined, "group");
      section.append(node("h3", "分鏡 25 宮格"));
      appendMedia(section, grid, true);
      detail.append(section);
    }
    for (const asset of shot.assets || []) appendMedia(detail, asset);
    for (const generation of shot.generations || []) appendMedia(detail, generation);
  }

  async function loadFile(path) {
    if (!path) {
      say("沒有來源文件路徑");
      return;
    }
    if (!confirmDiscard()) return;
    try {
      state.preview = null;
      state.file = await api(`/api/file?${new URLSearchParams({ path })}`);
      state.draft = state.file.content || "";
      state.unsaved = false;
      state.conflict = "";
      state.selected = null;
      state.selectedKey = null;
      detail.hidden = true;
      render();
    } catch (error) {
      say(`無法讀取文件：${error.message}`);
    }
  }

  function openFileOrMedia(file) {
    const path = filePath(file);
    const kind = typeof file === "object" ? String(file.kind || "").toLowerCase() : "";
    const ext = (path || "").split(".").pop().toLowerCase();
    if (kind === "media" || kind === "grid" || ["png", "jpg", "jpeg", "webp", "gif", "mp4", "webm", "mov", "wav", "mp3", "m4a", "aac", "flac", "opus"].includes(ext)) {
      openMedia(file, kind === "grid");
    } else {
      loadFile(path);
    }
  }

  function openMedia(file, isGrid = false) {
    if (!confirmDiscard()) return;
    closeFileState();
    state.preview = { file, isGrid };
    state.selected = null;
    state.selectedKey = null;
    detail.hidden = true;
    render();
  }

  function renderPreview(content) {
    const file = state.preview.file;
    const path = filePath(file);
    const heading = node("div", undefined, "overview");
    const info = node("div");
    info.append(node("h1", fileName(file)), node("div", path || "", "muted"));
    heading.append(info, button("關閉預覽", () => { state.preview = null; render(); }));
    content.append(heading);
    const frame = node("section", undefined, "panel");
    frame.style.padding = "16px";
    appendMedia(frame, file, state.preview.isGrid);
    content.append(frame);
  }

  function openFiles() {
    if (state.file) return;
    const episode = currentEpisode();
    const selectedSource = state.selected?.source;
    const tableSource = shots().find((shot) => shot.source)?.source;
    const source = selectedSource || tableSource;
    if (source) {
      loadFile(source);
      return;
    }

    const episodeId = episode ? String(episode.id) : "";
    const projectFiles = (state.project.files || []).filter((file) => {
      if (typeof file !== "object" || !file.episode) return true;
      const fileEpisode = String(file.episode);
      return fileEpisode === "project" || fileEpisode === episodeId;
    });
    const files = [...(episode?.files || []), ...projectFiles]
      .filter((file, index, list) => list.findIndex((item) => filePath(item) === filePath(file)) === index)
      .filter(isReadableTextFile)
      .filter(matchesSearch);
    if (files.length) loadFile(filePath(files[0]));
    else say("目前集數沒有符合搜尋的可讀文字文件");
  }

  function closeFileState() {
    state.preview = null;
    state.file = null;
    state.draft = null;
    state.unsaved = false;
    state.conflict = "";
  }

  function renderEditor(content) {
    const heading = node("div", undefined, "overview");
    const info = node("div");
    info.append(
      node("h1", state.file.path),
      node("div", state.file.editable ? "文字原文，可編輯" : "唯讀文件", "muted"),
    );
    heading.append(info);
    content.append(heading);
    if (state.conflict) content.append(node("div", state.conflict, "error"));

    const editor = document.createElement("textarea");
    editor.className = "editor";
    editor.setAttribute("aria-label", "文件原文");
    editor.readOnly = !state.file.editable;
    editor.value = state.draft ?? state.file.content ?? "";
    editor.addEventListener("input", () => {
      state.draft = editor.value;
      state.unsaved = state.draft !== state.file.content;
      saveState.textContent = state.unsaved ? "尚未儲存" : "已同步";
    });

    const saveState = node("span", state.unsaved ? "尚未儲存" : "", "notice");
    const savebar = node("div", undefined, "savebar");
    const save = button("儲存", () => saveFile(editor, save), "");
    save.disabled = !state.file.editable;
    savebar.append(
      save,
      button("關閉文件", () => {
        if (!confirmDiscard()) return;
        closeFileState();
        render();
      }),
      saveState,
    );
    content.append(editor, savebar);
  }

  async function saveFile(editor, saveButton) {
    saveButton.disabled = true;
    state.draft = editor.value;
    try {
      const result = await api("/api/file", {
        method: "PUT",
        body: JSON.stringify({
          path: state.file.path,
          content: state.draft,
          expected_version: state.file.version,
        }),
      });
      state.file.version = result.version;
      state.file.content = state.draft;
      state.unsaved = false;
      state.conflict = "";
      try {
        state.project = await api("/api/project");
      } catch (refreshError) {
        say(`原文已儲存，但無法更新專案資料：${refreshError.message}`);
        render();
        return;
      }
      say("原文已儲存；這不代表已生成或完成 QA。");
      render();
    } catch (error) {
      saveButton.disabled = false;
      if (error.status === 409) {
        state.conflict = "版本衝突：文件在開啟後已被其他修改更新。草稿已保留；請複製草稿、重新載入並整合變更。";
        say("儲存衝突，未覆寫較新的文件版本；草稿仍保留。");
        render();
      } else {
        say(`儲存失敗：${error.message}`);
      }
    }
  }

  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s" && state.file) {
      event.preventDefault();
      const editor = $(".editor");
      const saveButton = $(".savebar button");
      if (editor && saveButton && !saveButton.disabled) saveButton.click();
    }
  });

  window.addEventListener("beforeunload", (event) => {
    if (state.unsaved) {
      event.preventDefault();
      event.returnValue = "";
    }
  });

  window.addEventListener("hashchange", () => {
    const nextToken = new URLSearchParams(location.hash.slice(1)).get("token");
    if (!nextToken || nextToken === token) return;
    token = nextToken;
    sessionStorage.setItem("film.token", token);
    history.replaceState(null, "", location.pathname + location.search);
    bootstrap();
  });

  bootstrap();
})();
