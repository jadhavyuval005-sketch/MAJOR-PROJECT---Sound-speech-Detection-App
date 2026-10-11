(function () {
  var TOKEN_KEY = "ssd_token";
  var APP_URL = "/";            
  var mode = "login";           

  var $ = function (id) { return document.getElementById(id); };
  var form = $("auth-form"), errorBox = $("error"), submitBtn = $("submit");

  function setToken(t) { try { localStorage.setItem(TOKEN_KEY, t); } catch (e) { /* private mode */ } }
  function hasToken() { try { return !!localStorage.getItem(TOKEN_KEY); } catch (e) { return false; } }

  function showError(msg) { errorBox.textContent = msg; errorBox.hidden = !msg; }

  function render() {
    var login = mode === "login";
    $("title").textContent = login ? "Welcome back" : "Create your account";
    $("subtitle").textContent = login ? "Sign in to continue your child's screening." : "It takes less than a minute.";
    $("register-fields").hidden = login;
    $("submit").textContent = login ? "Sign in" : "Create account";
    $("switch-text").textContent = login ? "New to vaaniAI?" : "Already have an account?";
    $("switch").textContent = login ? "Create an account" : "Sign in";
    $("password").autocomplete = login ? "current-password" : "new-password";
    $("password").placeholder = login ? "" : "At least 8 characters";
    showError("");
  }

  $("switch").addEventListener("click", function () {
    mode = mode === "login" ? "register" : "login";
    render();
  });

  $("toggle-pw").addEventListener("click", function () {
    var pw = $("password"), show = pw.type === "password";
    pw.type = show ? "text" : "password";
    this.textContent = show ? "Hide" : "Show";
    this.setAttribute("aria-label", show ? "Hide password" : "Show password");
  });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var email = $("email").value.trim(), password = $("password").value, name = $("name").value.trim();

    // Client-side checks mirror the server's rules; the server still validates.
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return showError("Enter a valid email address");
    if (mode === "register" && !name) return showError("Name is required");
    if (mode === "register" && password.length < 8) return showError("Password must be at least 8 characters");
    if (!password) return showError("Enter your password");

    var body = mode === "login" ? { email: email, password: password }
                                 : { email: email, password: password, name: name, role: $("role").value };
    showError("");
    submitBtn.disabled = true;
    submitBtn.textContent = "Please wait…";

    fetch("/api/auth/" + mode, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    })
      .then(function (res) {
        return res.json().catch(function () { return {}; }).then(function (data) {
          if (!res.ok) throw new Error(data.error || "Request failed (" + res.status + ")");
          return data;
        });
      })
      .then(function (data) {
        setToken(data.token);
        window.location.href = APP_URL;
      })
      .catch(function (err) {
        showError(err instanceof TypeError ? "Cannot reach the server. Check your connection and try again." : err.message);
        submitBtn.disabled = false;
        render_submit_label();
      });
  });

  function render_submit_label() { submitBtn.textContent = mode === "login" ? "Sign in" : "Create account"; }

  if (hasToken()) { /* already signed in: the main app will validate the token */ }
  render();
})();
