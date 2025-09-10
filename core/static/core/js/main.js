// ----------------------------
// Common Helpers
// ----------------------------
let token = localStorage.getItem("accessToken");
let currentUser = "";
let currentRole = "";
let _allIdentities = [];
let _rendered = [];
let currentPreferredIdentityId = null;

function pad2(n) {
  return String(n).padStart(2, "0");
}
function formatDateISO(s) {
  if (!s) return "-";
  const d = new Date(s);
  if (isNaN(d)) return s; // fallback
  const y = d.getFullYear();
  const m = pad2(d.getMonth() + 1);
  const day = pad2(d.getDate());
  const hh = pad2(d.getHours());
  const mm = pad2(d.getMinutes());
  return `${y}-${m}-${day} ${hh}:${mm}`;
}

function requireAuth() {
  if (!token) {
    window.location.href = "/api/login/";
    return false;
  }
  return true;
}

function logout() {
  localStorage.removeItem("accessToken");
  window.location.href = "/api/login/";
}

async function authFetch(url, options = {}) {
  // tiny wrapper to auto-attach token + redirect on 401
  const opts = {
    ...options,
    headers: {
      ...(options.headers || {}),
      Authorization: "Bearer " + token,
    },
  };
  const res = await fetch(url, opts);
  if (res.status === 401) {
    logout();
    return res;
  }
  return res;
}

// ----------------------------
// Login Page
// ----------------------------
async function login() {
  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;
  const statusElem = document.getElementById("status");

  if (statusElem) statusElem.style.display = "none";

  const response = await fetch("/api/token/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  const data = await response.json();
  if (data.access) {
    localStorage.setItem("accessToken", data.access);
    token = data.access;
    window.location.href = "/api/home/";
  } else {
    if (statusElem) {
      statusElem.innerText = "Login failed.";
      statusElem.style.display = "block";
    }
  }
}

// ----------------------------
// Register Page
// ----------------------------
async function registerUser() {
  const response = await fetch("/api/register/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: document.getElementById("username").value,
      email: document.getElementById("email").value,
      password: document.getElementById("password").value,
    }),
  });

  const data = await response.text();
  if (response.ok) {
    document.getElementById("status").innerText =
      "✅ Registration successful! Redirecting to login...";
    setTimeout(() => {
      window.location.href = "/api/login/";
    }, 2000);
  } else {
    document.getElementById("status").innerText = "❌ " + data;
  }
}

// ----------------------------
// Home Page
// ----------------------------

function titleCase(s) {
  return (s || "")
    .toString()
    .replace(/\w\S*/g, (t) => t[0].toUpperCase() + t.slice(1).toLowerCase());
}

function renderIdentities(items) {
  const container = document.getElementById("identityList");
  if (!container) return;

  container.innerHTML = "";

  if (!items || items.length === 0) {
    container.innerHTML = `
      <div class="col-12">
        <div class="text-muted">No identities found.</div>
      </div>`;
    return;
  }

  items.forEach((identity) => {
    const ownerUsername =
      identity.username || identity.owner_username || "unknown";
    const ownerRole = identity.role || identity.owner_role || "user";
    const canModify = currentRole === "admin" || ownerUsername === currentUser;
    const isPreferred = identity.id === currentPreferredIdentityId;

    const col = document.createElement("div");
    col.className = "col-md-6 col-lg-4 mb-3";

    col.innerHTML = `
      <div class="card h-100 shadow-sm" id="card-${identity.id}">
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-start mb-2">
            <span class="fw-semibold">${titleCase(
              identity.context || ""
            )}</span>
            <span class="small text-muted">
              By: ${ownerUsername} (${ownerRole})
              ${
                isPreferred
                  ? ' · <span class="badge text-bg-success">Displayed</span>'
                  : ""
              }
            </span>
          </div>

          <div class="view-mode" id="view-${identity.id}">
            <div class="mb-1"><strong>Name:</strong> <span class="v-name">${
              identity.display_name
            }</span></div>
            <div class="mb-1"><strong>Language:</strong> <span class="v-lang">${
              identity.language || "-"
            }</span></div>
            <div class="mb-2 text-muted small">
              Last updated: ${formatDateISO(identity.updated_at)}
              <span class="ms-2">•</span> Created: ${formatDateISO(
                identity.created_at
              )}
            </div>

            ${
              canModify
                ? `
              <div class="d-flex gap-2">
                <button class="btn btn-sm btn-primary" onclick="enterEditMode(${
                  identity.id
                })">Edit</button>
                <button class="btn btn-sm btn-danger" data-id="${
                  identity.id
                }" onclick="deleteIdentity(event)">Delete</button>
                ${
                  isPreferred
                    ? `<button class="btn btn-sm btn-outline-secondary" onclick="clearDisplayed()">Unselect</button>`
                    : `<button class="btn btn-sm btn-outline-success" onclick="setAsDisplayed(${identity.id})">Display</button>`
                }
              </div>`
                : ``
            }
          </div>

          <!-- EDIT MODE (hidden by default) -->
          <form class="edit-mode d-none" id="edit-${
            identity.id
          }" onsubmit="return false;">
            <div class="mb-2">
              <label class="form-label small">Name</label>
              <input id="e-name-${
                identity.id
              }" class="form-control form-control-sm" value="${
      identity.display_name
    }">
            </div>
            <div class="mb-2">
              <label class="form-label small">Context</label>
              <input id="e-ctx-${
                identity.id
              }" class="form-control form-control-sm" value="${
      identity.context || ""
    }">
            </div>
            <div class="mb-3">
              <label class="form-label small">Language</label>
              <input id="e-lang-${
                identity.id
              }" class="form-control form-control-sm" value="${
      identity.language || ""
    }">
            </div>

            <div class="d-flex gap-2">
              <button class="btn btn-sm btn-success" onclick="saveEdit(${
                identity.id
              })">Save</button>
              <button class="btn btn-sm btn-outline-secondary" onclick="cancelEdit(${
                identity.id
              })">Cancel</button>
            </div>
          </form>
        </div>
      </div>
    `;
    container.appendChild(col);
  });

  _rendered = items;
}

async function fetchUserInfo() {
  if (!requireAuth()) return;

  const response = await authFetch("/api/user-info/");
  if (response.ok) {
    const data = await response.json();
    currentUser = data.username;
    currentRole = data.role;

    const usernameSpan = document.getElementById("username");
    const roleSpan = document.getElementById("role");
    if (usernameSpan) usernameSpan.innerText = currentUser;
    if (roleSpan) roleSpan.innerText = currentRole;

    const adminPanel = document.getElementById("admin_lookup_panel");
    if (adminPanel) {
      if (currentRole === "admin") adminPanel.classList.remove("d-none");
      else adminPanel.classList.add("d-none");
    }
    const btnPub = document.getElementById("btn_public_profile");
    if (btnPub) {
      btnPub.href = `/api/profile-page/${encodeURIComponent(currentUser)}/`;
    }
  }
}

async function fetchIdentities() {
  if (!requireAuth()) return;

  const container = document.getElementById("identityList");
  if (container) {
    container.innerHTML = `
      <div class="col-12 text-center py-4">
        <div class="spinner-border" role="status"></div>
      </div>`;
  }

  const response = await authFetch("/api/identities/");
  if (!response.ok) {
    if (container) {
      container.innerHTML =
        "<div class='col-12 text-danger'>Failed to load identities.</div>";
    }
    return;
  }

  _allIdentities = await response.json(); // cache full list from server
  applyFilters(); // initial render with current UI values
}
function getFilterValues() {
  const q =
    (document.getElementById("flt_q") || {}).value?.trim().toLowerCase() || "";
  const ctx =
    (document.getElementById("flt_context") || {}).value
      ?.trim()
      .toLowerCase() || "";
  const lng =
    (document.getElementById("flt_lang") || {}).value?.trim().toLowerCase() ||
    "";
  const sort = (document.getElementById("flt_sort") || {}).value || "recent";
  return { q, ctx, lng, sort };
}

async function setAsDisplayed(id) {
  if (!requireAuth()) return;
  const res = await authFetch("/api/me/profile/", {
    method: "PATCH",
    body: (() => {
      const fd = new FormData();
      fd.append("preferred_identity", id);
      return fd;
    })(),
  });
  if (!res.ok) {
    alert("Failed to set as displayed.");
    return;
  }
  // refresh the cached preferred id and re-render
  const prof = await res.json();
  currentPreferredIdentityId = prof.preferred_identity || null;
  applyFilters();
}

function applyFilters() {
  const { q, ctx, lng, sort } = getFilterValues();
  let list = [..._allIdentities];

  if (q)
    list = list.filter((i) => (i.display_name || "").toLowerCase().includes(q));
  if (ctx)
    list = list.filter((i) => (i.context || "").toLowerCase().includes(ctx));
  if (lng)
    list = list.filter((i) => (i.language || "").toLowerCase().includes(lng));

  function toTime(s) {
    const d = new Date(s);
    return isNaN(d) ? 0 : d.getTime();
  }

  switch (sort) {
    case "name_asc":
      list.sort((a, b) =>
        (a.display_name || "").localeCompare(b.display_name || "")
      );
      break;
    case "name_desc":
      list.sort((a, b) =>
        (b.display_name || "").localeCompare(a.display_name || "")
      );
      break;
    case "context_asc":
      list.sort((a, b) => (a.context || "").localeCompare(b.context || ""));
      break;
    case "created_new":
      list.sort((a, b) => toTime(b.created_at) - toTime(a.created_at));
      break;
    case "created_old":
      list.sort((a, b) => toTime(a.created_at) - toTime(b.created_at));
      break;
    case "recent": // default: most recently updated first
    default:
      list.sort((a, b) => toTime(b.updated_at) - toTime(a.updated_at));
      break;
  }

  renderIdentities(list);
}

async function fetchPreferredIdentity() {
  const res = await authFetch("/api/me/profile/");
  if (res.ok) {
    const prof = await res.json();
    currentPreferredIdentityId = prof.preferred_identity || null;
  }
}

function clearFilters() {
  ["flt_q", "flt_context", "flt_lang"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.value = "";
  });
  const sort = document.getElementById("flt_sort");
  if (sort) sort.value = "recent";
  applyFilters();
}

async function initHomePage() {
  await fetchUserInfo();
  await fetchPreferredIdentity();
  await fetchIdentities();
}

document.addEventListener("DOMContentLoaded", () => {
  // live search is handled directly via oninput/onchange in HTML
  // but keep Enter-to-apply as a convenience (optional)
  const q = document.getElementById("flt_q");
  if (q)
    q.addEventListener("keyup", (e) => {
      if (e.key === "Enter") applyFilters();
    });
});

// ----------------------------
// Add Identity Page
// ----------------------------
async function addIdentity() {
  if (!requireAuth()) return;

  const body = {
    display_name: document.getElementById("display_name").value,
    context: document.getElementById("context").value,
    language: document.getElementById("language").value,
  };

  try {
    const response = await authFetch("/api/identities/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const text = await response.text();
    if (response.ok) {
      document.getElementById("result").innerText =
        "✅ Identity added successfully! Redirecting...";
      setTimeout(() => {
        window.location.href = "/api/home/";
      }, 1500);
    } else {
      document.getElementById("result").innerText = "❌ Error: " + text;
    }
  } catch (err) {
    document.getElementById("result").innerText = "Error: " + err.message;
  }
}

// ----------------------------
// Edit & Delete Identity
// ----------------------------
async function deleteIdentity(ev) {
  if (!requireAuth()) return;

  const id = ev.currentTarget.getAttribute("data-id");
  if (!id) return;

  if (!confirm("Are you sure you want to delete this identity?")) return;

  const res = await authFetch(`/api/identities/${id}/`, {
    method: "DELETE",
  });

  if (res.status === 204) {
    // No content
    await fetchIdentities();
  } else {
    const msg = await res.text();
    alert("Failed to delete identity.\n" + msg);
  }
}

function toggleModes(id, editing) {
  const view = document.getElementById(`view-${id}`);
  const edit = document.getElementById(`edit-${id}`);
  if (!view || !edit) return;
  if (editing) {
    view.classList.add("d-none");
    edit.classList.remove("d-none");
  } else {
    edit.classList.add("d-none");
    view.classList.remove("d-none");
  }
}

function enterEditMode(id) {
  toggleModes(id, true);
}

function cancelEdit(id) {
  // optional: reset fields to current view text
  const viewName =
    document.querySelector(`#view-${id} .v-name`)?.textContent || "";
  const viewLang =
    document.querySelector(`#view-${id} .v-lang`)?.textContent || "";
  const ctxText =
    document.querySelector(`#card-${id} .fw-semibold`)?.textContent || "";

  const nameInput = document.getElementById(`e-name-${id}`);
  const langInput = document.getElementById(`e-lang-${id}`);
  const ctxInput = document.getElementById(`e-ctx-${id}`);

  if (nameInput) nameInput.value = viewName;
  if (langInput) langInput.value = viewLang;
  if (ctxInput) ctxInput.value = ctxText;

  toggleModes(id, false);
}

async function saveEdit(id) {
  if (!requireAuth()) return;

  const name = document.getElementById(`e-name-${id}`)?.value.trim() || "";
  const ctx = document.getElementById(`e-ctx-${id}`)?.value.trim() || "";
  const lang = document.getElementById(`e-lang-${id}`)?.value.trim() || "";

  if (!name) {
    alert("Name is required.");
    return;
  }

  const res = await authFetch(`/api/identities/${id}/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ display_name: name, context: ctx, language: lang }),
  });

  if (!res.ok) {
    const msg = await res.text();
    alert("Failed to update identity.\n" + msg);
    return;
  }

  // Update local cache & re-render under current filters
  const updated = await res.json().catch(() => null); // DRF usually returns the object
  if (updated) {
    const idx = _allIdentities.findIndex((i) => i.id === id);
    if (idx >= 0) _allIdentities[idx] = { ..._allIdentities[idx], ...updated };
  } else {
    // if your API doesn't return body on PUT, fallback to full refresh
    await fetchIdentities();
    return;
  }

  applyFilters(); // keep current search/sort
  toggleModes(id, false); // back to view-mode
}

// --------- My Profile page ----------
async function initMyProfilePage() {
  if (!requireAuth()) return;
  const [infoRes, profRes] = await Promise.all([
    authFetch("/api/user-info/"),
    authFetch("/api/me/profile/"),
  ]);
  if (!infoRes.ok || !profRes.ok) {
    window.location.href = "/api/login/";
    return;
  }

  const me = await infoRes.json();
  const prof = await profRes.json();

  document.getElementById("pf_username").textContent = me.username;
  document.getElementById("pf_role").textContent = me.role;
  document.getElementById("pf_label").value = prof.display_label || "";
  document.getElementById("pf_bio").value = prof.bio || "";
  document.getElementById("pf_label").value = prof.display_label || "";
  document.getElementById("pf_bio").value = prof.bio || "";
  document.getElementById("pf_gender").value = prof.gender_identity || "";
  document.getElementById("pf_pronouns").value = prof.pronouns || "";
  document.getElementById("pf_website").value = prof.website || "";
  document.getElementById("pf_github").value = prof.github || "";
  document.getElementById("pf_twitter").value = prof.twitter || "";
  document.getElementById("pf_linkedin").value = prof.linkedin || "";

  const img = document.getElementById("pf_avatar");
  img.src = prof.avatar_url || "";
}

async function saveMyProfile(e) {
  e.preventDefault();
  const form = new FormData();
  form.append("display_label", document.getElementById("pf_label").value);
  form.append("bio", document.getElementById("pf_bio").value);
  form.append("display_label", document.getElementById("pf_label").value);
  form.append("bio", document.getElementById("pf_bio").value);
  form.append("gender_identity", document.getElementById("pf_gender").value);
  form.append("pronouns", document.getElementById("pf_pronouns").value);
  form.append("website", document.getElementById("pf_website").value);
  form.append("github", document.getElementById("pf_github").value);
  form.append("twitter", document.getElementById("pf_twitter").value);
  form.append("linkedin", document.getElementById("pf_linkedin").value);
  const file = document.getElementById("pf_avatar_file").files[0];
  if (file) form.append("avatar", file);

  const res = await authFetch("/api/me/profile/", {
    method: "PATCH",
    body: form,
  });
  const status = document.getElementById("pf_status");
  if (res.ok) {
    const data = await res.json();
    status.textContent = "Saved!";
    document.getElementById("pf_avatar").src = data.avatar_url || "";
    setTimeout(() => (status.textContent = ""), 1500);
  } else {
    status.textContent = "Save failed.";
  }
}

async function exportIdentities() {
  if (!requireAuth()) return;
  try {
    const res = await authFetch("/api/identities/export/");
    if (!res.ok) {
      const t = await res.text().catch(() => "");
      alert("Export failed: " + t);
      return;
    }
    const data = await res.json();
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `identities_export_${new Date()
      .toISOString()
      .slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (e) {
    console.error(e);
    alert("Export failed.");
  }
}

async function importIdentitiesFromFile(ev) {
  if (!requireAuth()) return;
  const file = ev.target.files?.[0];
  if (!file) return;

  try {
    const text = await file.text();
    const payload = JSON.parse(text);

    const res = await authFetch("/api/identities/import/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const resp = await res.json().catch(() => ({}));
    if (res.ok || res.status === 207) {
      const msg =
        `Imported ${resp.created_count || 0} item(s).` +
        (resp.errors?.length ? " Some rows had errors; open console." : "");
      alert(msg);
      if (resp.errors?.length) console.warn("Import errors:", resp.errors);
      await fetchIdentities(); // refresh the grid
    } else {
      alert("Import failed: " + (resp.error || res.status));
    }
  } catch (e) {
    console.error(e);
    alert("Invalid JSON file.");
  } finally {
    ev.target.value = ""; // reset file input so the same file can be selected again
  }
}

// --------- People search on Home ----------
let _userSearchAbort = null;
async function searchUsersLive() {
  const q = (document.getElementById("user_q").value || "").trim();
  const box = document.getElementById("user_results");
  if (!q) {
    box.innerHTML = "";
    return;
  }

  // abort previous request
  if (_userSearchAbort) _userSearchAbort.abort();
  _userSearchAbort = new AbortController();

  const res = await authFetch(`/api/users/search/?q=${encodeURIComponent(q)}`, {
    signal: _userSearchAbort.signal,
  }).catch(() => null);
  if (!res || !res.ok) {
    box.innerHTML = "";
    return;
  }

  const data = await res.json();
  box.innerHTML = (data.results || [])
    .map(
      (u) => `
    <a class="list-group-item list-group-item-action"
       href="/api/profile-page/${encodeURIComponent(u.username)}/">
       ${
         u.display_label ? `${u.display_label} ` : ""
       }<span class="text-muted">@${u.username}</span>
    </a>`
    )
    .join("");
}

async function clearDisplayed() {
  if (!requireAuth()) return;

  const fd = new FormData();
  // DRF will treat empty string as null for allow_null=True fields
  fd.append("preferred_identity", "");

  const res = await authFetch("/api/me/profile/", {
    method: "PATCH",
    body: fd,
  });

  if (!res.ok) {
    alert("Failed to clear displayed identity.");
    return;
  }
  const prof = await res.json();
  currentPreferredIdentityId = prof.preferred_identity || null;
  applyFilters();
}

// Jump straight to a user's public profile page when pressing Enter or clicking Search
async function searchUsersSubmit(e) {
  if (e) e.preventDefault();

  const qRaw = (document.getElementById("user_q").value || "").trim();
  if (!qRaw) return false;

  // Query backend
  const res = await authFetch(
    `/api/users/search/?q=${encodeURIComponent(qRaw)}`
  ).catch(() => null);
  if (!res || !res.ok) {
    alert("Search failed. Please try again.");
    return false;
  }

  const data = await res.json();
  const results = data.results || [];

  if (results.length === 0) {
    alert("No users found.");
    return false;
  }

  // Prefer an exact username match (case-insensitive); else take the first result
  const qLower = qRaw.toLowerCase();
  let pick =
    results.find((u) => (u.username || "").toLowerCase() === qLower) ||
    results[0];

  // Navigate to the PUBLIC PROFILE PAGE (HTML)
  window.location.href = `/api/profile-page/${encodeURIComponent(
    pick.username
  )}/`;
  return false; // prevent form reload
}

function openPublicLookup() {
  const u = (document.getElementById("lookup_username").value || "").trim();
  const ctx = (document.getElementById("lookup_context").value || "").trim();
  if (!u) {
    alert("Username is required");
    return;
  }
  const url = `/api/public/lookup-page/${encodeURIComponent(u)}/${
    ctx ? `?context=${encodeURIComponent(ctx)}` : ""
  }`;
  window.location.href = url;
}

// ----------------------------
// View Identity Page (Optional)
async function getIdentitiesFiltered() {
  if (!requireAuth()) return;

  const context = document.getElementById("context").value;
  const lang = document.getElementById("language").value;

  const response = await authFetch(
    `/api/identities/?context=${encodeURIComponent(context)}`,
    {
      headers: { "Accept-Language": lang },
    }
  );

  document.getElementById("result").innerText = await response.text();
}
