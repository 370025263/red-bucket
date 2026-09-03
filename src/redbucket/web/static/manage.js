(function () {
  var tokenKey = "rb_token";
  var userKey = "rb_user";
  var strings = window.RB_UI || {};

  document.documentElement.classList.add("js");

  function label(key, fallback) {
    return strings[key] || fallback;
  }

  function token() {
    return sessionStorage.getItem(tokenKey);
  }

  function user() {
    var raw = sessionStorage.getItem(userKey);
    return raw ? JSON.parse(raw) : null;
  }

  function headers() {
    var out = { "Content-Type": "application/json" };
    if (token()) {
      out.Authorization = "Bearer " + token();
    }
    return out;
  }

  function toast(text) {
    var box = document.getElementById("toast");
    if (!box) {
      return;
    }
    box.textContent = text;
    box.classList.add("is-on");
    setTimeout(function () {
      box.classList.remove("is-on");
    }, 2200);
  }

  function showAuth() {
    var signed = Boolean(token());
    var me = user();
    document.querySelectorAll("[data-auth=anon]").forEach(function (node) {
      node.classList.toggle("hidden", signed);
    });
    document.querySelectorAll("[data-auth=user]").forEach(function (node) {
      node.classList.toggle("hidden", !signed);
    });
    var who = document.getElementById("whoami");
    if (who && me) {
      who.textContent = me.username;
      who.setAttribute("href", "/" + me.username);
    }
    var owner = Boolean(window.RB_BUCKET && me && me.username === window.RB_BUCKET.username);
    document.querySelectorAll("[data-owner-only]").forEach(function (node) {
      node.classList.toggle("hidden", !owner);
    });
  }

  function api(path, method, body) {
    return fetch(path, {
      method: method,
      headers: headers(),
      body: body ? JSON.stringify(body) : undefined
    }).then(function (res) {
      if (res.status === 204) {
        return {};
      }
      return res.json().then(function (data) {
        if (!res.ok) {
          throw data;
        }
        return data;
      });
    });
  }

  function setError(err) {
    var box = document.getElementById("form-error");
    if (!box) {
      return;
    }
    if (err && err.error) {
      box.textContent = err.error.message || err.error.code;
    } else {
      box.textContent = "request failed";
    }
  }

  function clearError() {
    var box = document.getElementById("form-error");
    if (box) {
      box.textContent = "";
    }
  }

  /* Keeps a submit button honest while its request is in flight, so a
     double click cannot post the same asset or comment twice. */
  function busy(form, state) {
    var button = form.querySelector("button[type=submit]");
    if (!button) {
      return;
    }
    button.disabled = state;
    if (state) {
      button.setAttribute("aria-busy", "true");
    } else {
      button.removeAttribute("aria-busy");
    }
  }

  function submits(form, build) {
    if (!form) {
      return;
    }
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var plan = build();
      if (!plan) {
        return;
      }
      clearError();
      busy(form, true);
      api(plan.path, plan.method, plan.body)
        .then(plan.done)
        .catch(function (err) {
          busy(form, false);
          setError(err);
        });
    });
  }

  function bucketPath() {
    var bucket = window.RB_BUCKET;
    return "/api/v1/users/" + bucket.username + "/buckets/" + bucket.name;
  }

  function initSettings() {
    var settingsForm = document.getElementById("settings-form");
    if (!settingsForm || !window.RB_BUCKET) {
      return;
    }
    var bucket = window.RB_BUCKET;
    var me = user();
    var unauth = document.getElementById("settings-unauthorized");
    var panel = document.getElementById("settings-owner-panel");

    function deny() {
      if (panel) {
        panel.classList.add("hidden");
      }
      if (unauth) {
        unauth.classList.remove("hidden");
      }
    }

    if (!me || me.username !== bucket.username) {
      deny();
      return;
    }

    api(bucketPath(), "GET")
      .then(function (data) {
        window.RB_BUCKET = data;
        if (settingsForm.visibility) {
          settingsForm.visibility.value = data.visibility;
        }
        if (settingsForm.description) {
          settingsForm.description.value = data.description || "";
        }
        var usageEl = document.getElementById("settings-usage");
        if (usageEl) {
          var bytes = data.usage_bytes;
          var used = bytes < 1024
            ? bytes + " B"
            : bytes < 1048576
              ? (bytes / 1024).toFixed(1) + " KB"
              : (bytes / 1048576).toFixed(1) + " MB";
          usageEl.textContent = label("usage", "Usage") + ": " + used +
            " / " + (data.limit_bytes / 1048576).toFixed(1) + " MB";
        }
        if (panel) {
          panel.classList.remove("hidden");
        }
        if (unauth) {
          unauth.classList.add("hidden");
        }
      })
      .catch(deny);
  }

  var loginForm = document.getElementById("login-form");
  submits(loginForm, function () {
    return {
      path: "/api/v1/auth/login",
      method: "POST",
      body: {
        email: loginForm.email.value,
        password: loginForm.password.value
      },
      done: function (data) {
        sessionStorage.setItem(tokenKey, data.token);
        sessionStorage.setItem(userKey, JSON.stringify(data.user));
        window.location.href = "/" + data.user.username;
      }
    };
  });

  var registerForm = document.getElementById("register-form");
  submits(registerForm, function () {
    return {
      path: "/api/v1/auth/register",
      method: "POST",
      body: {
        username: registerForm.username.value,
        email: registerForm.email.value,
        password: registerForm.password.value
      },
      done: function () {
        window.location.href = "/login";
      }
    };
  });

  var logoutLink = document.getElementById("logout-link");
  if (logoutLink) {
    logoutLink.addEventListener("click", function (event) {
      event.preventDefault();
      api("/api/v1/auth/logout", "POST", {}).finally(function () {
        sessionStorage.removeItem(tokenKey);
        sessionStorage.removeItem(userKey);
        window.location.href = "/";
      });
    });
  }

  var newBucket = document.getElementById("new-bucket-form");
  submits(newBucket, function () {
    var me = user();
    if (!me) {
      window.location.href = "/login";
      return null;
    }
    var template = newBucket.template.value;
    return {
      path: "/api/v1/users/" + me.username + "/buckets",
      method: "POST",
      body: {
        name: newBucket.name.value,
        visibility: newBucket.visibility.value,
        description: newBucket.description.value,
        template: template === "" ? null : template
      },
      done: function (data) {
        window.location.href = "/" + data.username + "/" + data.name;
      }
    };
  });

  /* Each asset type has a file the validator insists on, and for
     instructions the name also depends on the source harness. Filling
     it in keeps a first upload from bouncing off the validator. */
  var assetShapes = {
    skill: {
      file: "SKILL.md",
      dir: "skills/my-skill",
      body: "---\nname: my-skill\ndescription: What it does, and when an agent should reach for it.\n---\n\n# my-skill\n\nSteps go here.\n"
    },
    mcp: {
      file: ".mcp.json",
      dir: "mcp/my-server",
      body: "{\n  \"mcpServers\": {\n    \"my-server\": {\n      \"command\": \"npx\",\n      \"args\": [\"-y\", \"my-mcp-server\"]\n    }\n  }\n}\n"
    },
    instructions: {
      file: "AGENTS.md",
      dir: "instructions/house-style",
      body: "# House style\n\nShort sentences. Cite sources.\n"
    },
    subagent: {
      file: "reviewer.md",
      dir: "agents/reviewer",
      body: "---\nname: reviewer\ndescription: What it does, and when an agent should reach for it.\n---\n\n# reviewer\n"
    },
    plugin: {
      file: "plugin.json",
      dir: "plugins/my-plugin",
      body: "{\n  \"name\": \"my-plugin\",\n  \"version\": \"0.1.0\"\n}\n"
    }
  };

  function shapeFor(type, harness) {
    var shape = assetShapes[type] || assetShapes.skill;
    if (type !== "instructions") {
      return shape;
    }
    var named = harness === "claude" ? "CLAUDE.md" : "AGENTS.md";
    return { file: named, dir: shape.dir, body: shape.body };
  }

  function isUntouched(field, key) {
    if (!field.value) {
      return true;
    }
    for (var name in assetShapes) {
      if (assetShapes[name][key] === field.value) {
        return true;
      }
    }
    return field.value === "CLAUDE.md" || field.value === "AGENTS.md";
  }

  function trackAssetShape(form) {
    var typeField = form.elements.namedItem("type");
    var sourceField = form.elements.namedItem("source_harness");
    var pathField = form.elements.namedItem("path");
    var fileField = form.elements.namedItem("file_path");
    var contentField = form.elements.namedItem("content_text");

    function apply() {
      var shape = shapeFor(typeField.value, sourceField.value);
      if (isUntouched(fileField, "file")) {
        fileField.value = shape.file;
      }
      pathField.setAttribute("placeholder", shape.dir);
      contentField.setAttribute("placeholder", shape.body);
    }

    typeField.addEventListener("change", apply);
    sourceField.addEventListener("change", apply);
    apply();
  }

  var upload = document.getElementById("upload-form");
  if (upload && window.RB_BUCKET) {
    trackAssetShape(upload);
    submits(upload, function () {
      return {
        path: bucketPath() + "/assets",
        method: "POST",
        body: {
          type: upload.type.value,
          source_harness: upload.source_harness.value,
          path: upload.path.value,
          files: [{ path: upload.file_path.value, content_text: upload.content_text.value }]
        },
        done: function () {
          window.location.reload();
        }
      };
    });
  }

  var issueForm = document.getElementById("issue-form");
  if (issueForm && window.RB_BUCKET) {
    submits(issueForm, function () {
      var bucket = window.RB_BUCKET;
      return {
        path: bucketPath() + "/issues",
        method: "POST",
        body: { title: issueForm.title.value, body: issueForm.body.value },
        done: function (data) {
          window.location.href = "/" + bucket.username + "/" + bucket.name + "/issues/" + data.number;
        }
      };
    });
  }

  var commentForm = document.getElementById("comment-form");
  if (commentForm && window.RB_BUCKET) {
    submits(commentForm, function () {
      return {
        path: bucketPath() + "/issues/" + window.RB_ISSUE + "/comments",
        method: "POST",
        body: { body: commentForm.body.value },
        done: function () {
          window.location.reload();
        }
      };
    });
  }

  var pullForm = document.getElementById("pull-form");
  if (pullForm && window.RB_BUCKET) {
    submits(pullForm, function () {
      var bucket = window.RB_BUCKET;
      return {
        path: bucketPath() + "/pulls",
        method: "POST",
        body: {
          title: pullForm.title.value,
          body: pullForm.body.value,
          files: [{ path: pullForm.file_path.value, content_text: pullForm.content_text.value }]
        },
        done: function (data) {
          window.location.href = "/" + bucket.username + "/" + bucket.name + "/pulls/" + data.number;
        }
      };
    });
  }

  var mergeForm = document.getElementById("merge-form");
  if (mergeForm && window.RB_BUCKET) {
    submits(mergeForm, function () {
      return {
        path: bucketPath() + "/pulls/" + window.RB_PULL + "/merge",
        method: "POST",
        body: {},
        done: function () {
          window.location.reload();
        }
      };
    });
  }

  var rejectForm = document.getElementById("reject-form");
  if (rejectForm && window.RB_BUCKET) {
    submits(rejectForm, function () {
      return {
        path: bucketPath() + "/pulls/" + window.RB_PULL + "/reject",
        method: "POST",
        body: {},
        done: function () {
          window.location.reload();
        }
      };
    });
  }

  var settingsForm = document.getElementById("settings-form");
  if (settingsForm && window.RB_BUCKET) {
    submits(settingsForm, function () {
      return {
        path: bucketPath(),
        method: "PATCH",
        body: {
          visibility: settingsForm.visibility.value,
          description: settingsForm.description.value
        },
        done: function (data) {
          busy(settingsForm, false);
          document.querySelectorAll(".vis-badge").forEach(function (node) {
            node.textContent = data.visibility;
          });
          toast(label("saved", "Saved"));
        }
      };
    });
  }

  var deleteForm = document.getElementById("delete-bucket-form");
  if (deleteForm && window.RB_BUCKET) {
    deleteForm.addEventListener("submit", function (event) {
      event.preventDefault();
      var bucket = window.RB_BUCKET;
      var asked = deleteForm.getAttribute("data-confirm-prompt") || "";
      var typed = window.prompt(asked + " " + bucket.name);
      if (typed !== bucket.name) {
        return;
      }
      api(bucketPath(), "DELETE", null)
        .then(function () {
          window.location.href = "/" + bucket.username;
        })
        .catch(setError);
    });
  }

  document.querySelectorAll(".copy-btn[data-copy]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var pre = document.getElementById(btn.getAttribute("data-copy"));
      if (!pre) {
        return;
      }
      var text = pre.textContent.replace(/^\$\s*/, "");
      if (!navigator.clipboard || !navigator.clipboard.writeText) {
        return;
      }
      navigator.clipboard.writeText(text).then(function () {
        var original = btn.textContent;
        btn.textContent = label("copied", "Copied");
        btn.classList.add("is-done");
        setTimeout(function () {
          btn.textContent = original;
          btn.classList.remove("is-done");
        }, 1800);
      });
    });
  });

  var installMenu = document.querySelector(".install-details");
  if (installMenu) {
    document.addEventListener("click", function (event) {
      if (installMenu.open && !installMenu.contains(event.target)) {
        installMenu.open = false;
      }
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && installMenu.open) {
        installMenu.open = false;
      }
    });
  }

  /* The approval page. The browser holds the human's session; the agent
     never sees it. All we do here is turn a signed-in human's yes or no
     into one call, then tell them to go back to their agent. */
  function initLink() {
    var panel = document.getElementById("decide-panel");
    if (!panel || !window.RB_USER_CODE) {
      return;
    }
    var code = window.RB_USER_CODE;
    var signin = document.getElementById("decide-signin");
    var done = document.getElementById("decide-done");
    var me = user();
    if (!me) {
      if (signin) {
        signin.classList.remove("hidden");
      }
      return;
    }
    var whoBox = document.getElementById("decide-user");
    if (whoBox) {
      whoBox.textContent = me.username;
    }
    api("/api/v1/auth/device/" + encodeURIComponent(code), "GET")
      .then(function (data) {
        var clientBox = document.getElementById("decide-client");
        if (clientBox) {
          clientBox.textContent = data.client || "an agent";
        }
        panel.classList.remove("hidden");
      })
      .catch(setError);

    function decide(approve) {
      api(
        "/api/v1/auth/device/" + encodeURIComponent(code) + "/decision",
        "POST",
        { approve: approve }
      ).then(function () {
        panel.classList.add("hidden");
        var head = document.getElementById("decide-head");
        var sub = document.getElementById("decide-sub");
        var note = document.getElementById("decide-done-note");
        if (note) {
          note.textContent = approve
            ? label("link_done", "Done. Go back to your agent.")
            : label("link_refused", "Refused. Nothing was shared.");
        }
        if (head) {
          head.textContent = approve
            ? label("link_approve", "Authorize")
            : label("link_deny", "Refuse");
        }
        if (sub) {
          sub.textContent = "";
        }
        if (done) {
          done.classList.remove("hidden");
        }
      }).catch(setError);
    }

    var yes = document.getElementById("decide-approve");
    if (yes) {
      yes.addEventListener("click", function () { decide(true); });
    }
    var no = document.getElementById("decide-deny");
    if (no) {
      no.addEventListener("click", function () { decide(false); });
    }
  }

  showAuth();
  initSettings();
  initLink();
})();
