/**
 * RZMT Website Interactive Behaviors
 * Multi-Page SPA Navigation & Left/Right Combine Transitions
 */

(function() {
  'use strict';

  // 1. Multi-Page Navigation Router
  var pages = document.querySelectorAll(".site-page");
  var desktopNavLinks = document.querySelectorAll(".header-center-nav a");
  var mobileNavLinks = document.querySelectorAll(".mobile-nav-link");
  var footerNavLinks = document.querySelectorAll(".footer-nav a");
  var animObserver = null;

  function setActiveNav(target) {
    desktopNavLinks.forEach(function(a) {
      var navTarget = a.getAttribute("data-nav") || a.getAttribute("href").replace(/^#/, "");
      a.classList.toggle("active", navTarget === target);
    });

    mobileNavLinks.forEach(function(a) {
      var navTarget = a.getAttribute("data-nav") || a.getAttribute("href").replace(/^#/, "");
      a.classList.toggle("active", navTarget === target);
    });

    footerNavLinks.forEach(function(a) {
      var navTarget = a.getAttribute("data-nav") || a.getAttribute("href").replace(/^#/, "");
      a.classList.toggle("active", navTarget === target);
    });
  }

  function initScrollObserver() {
    var allAnimated = document.querySelectorAll(
      ".reveal-on-scroll, .reveal-from-left, .reveal-from-right, .reveal-up, .reveal-words, .cap-feature-card, .caps-closing-card, .step-card"
    );

    if ("IntersectionObserver" in window) {
      if (animObserver) {
        animObserver.disconnect();
      }
      animObserver = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("revealed");
            entry.target.classList.remove("scrolled-out");
          } else {
            // Re-arm when scrolled well outside of viewport so user can re-experience the left-right integration
            var rect = entry.boundingClientRect;
            var vh = window.innerHeight || document.documentElement.clientHeight;
            if (rect.top > vh + 60 || rect.bottom < -180) {
              entry.target.classList.remove("revealed");
            }
          }
        });
      }, {
        threshold: 0.10,
        rootMargin: "0px 0px -40px 0px"
      });

      allAnimated.forEach(function(el) {
        animObserver.observe(el);
      });
    } else {
      allAnimated.forEach(function(el) {
        el.classList.add("revealed");
      });
    }
  }

  function triggerPageAnimations(activePage) {
    if (!activePage) return;
    var animElements = activePage.querySelectorAll(
      ".reveal-on-scroll, .reveal-from-left, .reveal-from-right, .reveal-up, .reveal-words, .cap-feature-card, .caps-closing-card, .step-card"
    );
    var vh = window.innerHeight || document.documentElement.clientHeight;

    animElements.forEach(function(el) {
      var rect = el.getBoundingClientRect();
      // Only reveal elements already in the top viewport area
      if (rect.top < vh * 0.85 && rect.bottom > 0) {
        setTimeout(function() {
          el.classList.add("revealed");
        }, 50);
      } else {
        // Below the fold: remove revealed so IntersectionObserver triggers on scroll down!
        el.classList.remove("revealed");
      }
    });

    // Re-bind observer to ensure new/fresh observation
    initScrollObserver();
  }

  function navigateTo(hash) {
    if (!hash || hash === "#") {
      hash = "#home";
    }
    var route = hash.replace(/^#/, "");
    var targetPage = document.getElementById("page-" + route);

    if (!targetPage) {
      route = "home";
      targetPage = document.getElementById("page-home");
    }

    // Toggle pages
    pages.forEach(function(page) {
      if (page.id === "page-" + route) {
        page.classList.add("active");
        triggerPageAnimations(page);
      } else {
        page.classList.remove("active");
      }
    });

    // Update active nav indicators (respecting open career slide panel)
    var isCareerOpen = careerPanel && careerPanel.classList.contains("open");
    setActiveNav(isCareerOpen ? "careers" : route);

    // Set body data-route for CSS-based WhatsApp visibility guard
    document.body.setAttribute("data-route", route);

    // Elfsight WhatsApp — inject script only once when Contact is first visited
    if (route === "contact" && !document.getElementById("elfsight-platform-js")) {
      var efScript = document.createElement("script");
      efScript.id = "elfsight-platform-js";
      efScript.src = "https://elfsightcdn.com/platform.js";
      efScript.async = true;
      document.head.appendChild(efScript);
    }

    // Scroll cleanly to top of newly opened page
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // 0. Premium Logo Splash Preloader
  var splash = document.getElementById("splash-loader");
  if (splash) {
    document.body.style.overflow = "hidden";
    var splashDismissed = false;

    var dismissSplash = function() {
      if (splashDismissed) return;
      splashDismissed = true;
      splash.classList.add("loaded");
      document.body.style.overflow = "";
      var curHash = window.location.hash || "#home";
      navigateTo(curHash);
      setTimeout(function() {
        if (splash && splash.parentNode) {
          splash.parentNode.removeChild(splash);
        }
      }, 900);
    };

    var pageReady = false;
    var timerDone = false;

    var tryDismiss = function() {
      if (pageReady && timerDone) dismissSplash();
    };

    setTimeout(function() {
      timerDone = true;
      tryDismiss();
    }, 3000);

    if (document.readyState === "complete") {
      pageReady = true;
      tryDismiss();
    } else {
      window.addEventListener("load", function() {
        pageReady = true;
        tryDismiss();
      }, { once: true });
    }

    setTimeout(function() {
      pageReady = true;
      timerDone = true;
      tryDismiss();
    }, 6000);

    splash.addEventListener("click", dismissSplash);
  }

  window.addEventListener("hashchange", function() {
    navigateTo(window.location.hash);
  });

  document.addEventListener("click", function(e) {
    var anchor = e.target.closest("a[href^='#']");
    if (!anchor) return;

    if (anchor.dataset && anchor.dataset.action === "open-careers") {
      e.preventDefault();
      var drawer = document.getElementById("mobile-drawer");
      var menuBtnEl = document.getElementById("menu-btn");
      if (drawer)    { drawer.classList.remove("open"); }
      if (menuBtnEl) { menuBtnEl.setAttribute("aria-expanded", "false"); }
      setActiveNav("careers");
      navigateTo("#contact");
      window.location.hash = "#contact";
      setTimeout(openCareerPanel, 350);
      return;
    }

    var hash = anchor.getAttribute("href");
    if (hash && hash !== "#") {
      if (hash === "#privacy" || hash === "#terms") return;
      if (document.getElementById("page-" + hash.replace(/^#/, ""))) {
        e.preventDefault();
        window.location.hash = hash;
        navigateTo(hash);
      }
    }
  });

  // Initial Route Load
  var bodyInitialPage = document.body.getAttribute("data-initial-page");
  var initialRoute = window.location.hash || (bodyInitialPage ? "#" + bodyInitialPage : "#home");
  navigateTo(initialRoute);

  // 2. Mobile Nav Drawer Toggle
  var menuBtn = document.getElementById("menu-btn");
  var mobileDrawer = document.getElementById("mobile-drawer");
  if (menuBtn && mobileDrawer) {
    menuBtn.addEventListener("click", function() {
      var isOpen = mobileDrawer.classList.toggle("open");
      menuBtn.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });

    document.querySelectorAll(".mobile-nav-link").forEach(function(link) {
      link.addEventListener("click", function() {
        mobileDrawer.classList.remove("open");
        menuBtn.setAttribute("aria-expanded", "false");
      });
    });
  }

  // 3. Header Shadow on Scroll
  var siteHeader = document.getElementById("site-header");
  function handleScroll() {
    var scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    if (siteHeader) {
      siteHeader.classList.toggle("scrolled", scrollTop > 15);
    }
  }
  window.addEventListener("scroll", handleScroll, { passive: true });

  // 4. Initial Scroll Observer
  initScrollObserver();

  // =========================================================
  // 5. CONTACT FORM — Submit to Flask backend
  // =========================================================
  var enquiryForm  = document.getElementById("enquiry-form");
  var statusEl     = document.getElementById("enquiry-status");
  var submitBtn    = document.getElementById("btn-get-started");
  var btnText      = document.getElementById("btn-get-started-text");

  var FLASK_ENDPOINT = "/submit-contact";

  function setButtonLoading(loading) {
    if (!submitBtn) return;
    submitBtn.setAttribute("data-loading", loading ? "true" : "false");
    submitBtn.disabled = loading;
    if (btnText) btnText.textContent = loading ? "Sending…" : "Send Message";
  }

  function showStatus(msg, type) {
    if (!statusEl) return;
    statusEl.textContent = msg;
    statusEl.className = "form-status " + (type || "");
  }

  function showSuccess() {
    var form = document.getElementById("enquiry-form");
    var successEl = document.getElementById("form-success");
    if (form) form.style.display = "none";
    if (successEl) successEl.classList.add("visible");
  }

  function getFormData() {
    var name      = ((document.getElementById("f-name")      || {}).value || "").trim();
    var email     = ((document.getElementById("f-email")     || {}).value || "").trim();
    var company   = ((document.getElementById("f-company")   || {}).value || "").trim();
    var topic     = ((document.getElementById("f-topic")     || {}).value || "").trim();
    var message   = ((document.getElementById("f-challenge") || {}).value || "").trim();
    return { name: name, email: email, company: company, topic: topic, message: message };
  }

  function validateForm(data) {
    if (!data.name || !data.email || !data.message) {
      showStatus("Please fill in your Name, Email and Message.", "error");
      return false;
    }
    if (!/^\S+@\S+\.\S+$/.test(data.email)) {
      showStatus("Please enter a valid email address.", "error");
      return false;
    }
    return true;
  }

  if (enquiryForm) {
    enquiryForm.addEventListener("submit", function(e) {
      e.preventDefault();
      var data = getFormData();
      if (!validateForm(data)) return;

      setButtonLoading(true);
      showStatus("", "");

      fetch(FLASK_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
      })
      .then(function(res) {
        return res.json().then(function(json) {
          return { ok: res.ok, json: json };
        });
      })
      .then(function(result) {
        setButtonLoading(false);
        if (result.ok && result.json.ok) {
          showSuccess();
        } else {
          showStatus(result.json.error || "Something went wrong. Please try again.", "error");
        }
      })
      .catch(function(err) {
        setButtonLoading(false);
        showStatus("Could not reach the server. Please ensure the app is running or contact us directly at rzmt.2025@gmail.com", "error");
        console.error("Submit error:", err);
      });
    });
  }

  // "Send Another Enquiry" → reset form
  document.addEventListener("click", function(e) {
    if (e.target && e.target.id === "btn-send-another") {
      var form = document.getElementById("enquiry-form");
      var successEl = document.getElementById("form-success");
      if (form) { form.reset(); form.style.display = ""; }
      if (successEl) successEl.classList.remove("visible");
      var st = document.getElementById("enquiry-status");
      if (st) { st.textContent = ""; st.className = "form-status"; }
    }
  });

  // "Job Opening" dropdown → auto-open career panel
  var topicSelect = document.getElementById("f-topic");
  if (topicSelect) {
    topicSelect.addEventListener("change", function() {
      if (this.value === "Job Opening") {
        openCareerPanel();
      }
    });
  }

    // 6. CAREER SLIDE PANEL & APPLICANT MANAGEMENT SYSTEM
  var careerPanel           = document.getElementById("careerPanel");
  var careerBackdrop        = document.getElementById("careerBackdrop");
  var careerClose           = document.getElementById("careerPanelClose");
  var careerInfoBtn         = document.getElementById("btn-career-info");

  var applicationPanel      = document.getElementById("applicationPanel");
  var applicationPanelClose = document.getElementById("applicationPanelClose");
  var btnBackToOpenings     = document.getElementById("btnBackToOpenings");

  var candidateAuthModal    = document.getElementById("candidateAuthModal");
  var btnCloseAuthModal     = document.getElementById("btnCloseAuthModal");
  var btnOpenCandidateAuth  = document.getElementById("btnOpenCandidateAuth");
  var tabAuthSignIn         = document.getElementById("tabAuthSignIn");
  var tabAuthRegister       = document.getElementById("tabAuthRegister");
  var formCandidateSignIn   = document.getElementById("formCandidateSignIn");
  var formCandidateRegister = document.getElementById("formCandidateRegister");
  var authAlertError        = document.getElementById("authAlertError");

  var candidateGuestRow     = document.getElementById("candidateGuestRow");
  var candidateActiveRow    = document.getElementById("candidateActiveRow");
  var careerSubnavTabs      = document.getElementById("careerSubnavTabs");
  var candidateNameBadge    = document.getElementById("candidateNameBadge");
  var candidateEmailBadge   = document.getElementById("candidateEmailBadge");
  var candidateAvatarInit   = document.getElementById("candidateAvatarInitials");
  var btnCandidateLogout    = document.getElementById("btnCandidateLogout");

  var tabOpeningsBtn        = document.getElementById("tabOpeningsBtn");
  var tabMyAppsBtn          = document.getElementById("tabMyAppsBtn");
  var careerViewOpenings    = document.getElementById("careerViewOpenings");
  var careerViewMyApps      = document.getElementById("careerViewMyApps");
  var openingsListCont      = document.getElementById("openingsListContainer");
  var myAppsListCont        = document.getElementById("myAppsListContainer");
  var panelOpeningsCount    = document.getElementById("panelOpeningsCount");
  var panelMyAppsCount      = document.getElementById("panelMyAppsCount");

  var candidateState = {
    isLoggedIn: false,
    user: null,
    openings: [],
    myApplications: [],
    pendingOpening: null
  };

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function openCareerPanel() {
    if (!careerPanel) return;
    careerPanel.classList.add("open");
    if (careerBackdrop) careerBackdrop.classList.add("open");
    document.body.style.overflow = "hidden";
    setActiveNav("careers");
    careerPanel.focus && careerPanel.focus();
    loadOpenings();
    checkCandidateAuth();
  }

  function closeCareerPanel() {
    if (!careerPanel) return;
    careerPanel.classList.remove("open");
    closeApplicationPanel();
    closeCandidateAuthModal();
    if (careerBackdrop) careerBackdrop.classList.remove("open");
    document.body.style.overflow = "";
    setActiveNav("contact");
  }

  function openApplicationPanel(op) {
    if (!applicationPanel) return;
    document.getElementById("appOpeningId").value = op.id;
    document.getElementById("appTargetJobTitle").textContent = op.title;
    document.getElementById("appTargetJobDept").textContent = (op.department || "") + (op.location ? " · " + op.location : "");
    
    // Automatically fill required user details (from user state or local storage cache)
    var userName = "";
    var userEmail = "";
    var userPhone = "";

    if (candidateState.user) {
      userName = candidateState.user.name || "";
      userEmail = candidateState.user.email || "";
      userPhone = candidateState.user.phone || "";
    } else {
      try {
        var cached = JSON.parse(localStorage.getItem("rzmt_applicant_details") || "{}");
        userName = cached.name || "";
        userEmail = cached.email || "";
        userPhone = cached.phone || "";
      } catch (e) {}
    }

    if (userName) document.getElementById("appCandidateName").value = userName;
    if (userEmail) document.getElementById("appCandidateEmail").value = userEmail;
    if (userPhone) document.getElementById("appCandidatePhone").value = userPhone;
    
    var errBox = document.getElementById("applicationErrorAlert");
    if (errBox) errBox.style.display = "none";

    // Close careers panel so only application panel is open from the left
    if (careerPanel) careerPanel.classList.remove("open");

    applicationPanel.classList.add("open");
    if (careerBackdrop) careerBackdrop.classList.add("open");
    document.body.style.overflow = "hidden";
  }

  function closeApplicationPanel() {
    if (!applicationPanel) return;
    applicationPanel.classList.remove("open");
  }

  function openCandidateAuthModal(promptMsg) {
    if (!candidateAuthModal) return;
    // Directly go to sign in view
    if (formCandidateSignIn) formCandidateSignIn.style.display = "block";
    if (formCandidateRegister) formCandidateRegister.style.display = "none";
    var h = document.getElementById("authModalHeading");
    if (h) h.textContent = "Candidate Sign In";

    if (authAlertError) {
      if (promptMsg) {
        authAlertError.textContent = promptMsg;
        authAlertError.style.display = "block";
        authAlertError.style.background = "#EFF6FF";
        authAlertError.style.color = "#2563EB";
        authAlertError.style.borderColor = "#DBEAFE";
      } else {
        authAlertError.style.display = "none";
      }
    }
    candidateAuthModal.classList.add("open");
  }

  function closeCandidateAuthModal() {
    if (!candidateAuthModal) return;
    candidateAuthModal.classList.remove("open");
  }

  // --- API Integrations ---

  async function checkCandidateAuth() {
    try {
      var res = await fetch("/api/candidate/me");
      var data = await res.json();
      if (data.ok && data.logged_in) {
        candidateState.isLoggedIn = true;
        candidateState.user = data.candidate;
        renderCandidateBar();
        loadCandidateApplications();
      } else {
        candidateState.isLoggedIn = false;
        candidateState.user = null;
        renderCandidateBar();
      }
    } catch (err) {
      console.warn("Candidate auth check error", err);
    }
  }

  function renderCandidateBar() {
    if (candidateState.isLoggedIn && candidateState.user) {
      if (candidateGuestRow) candidateGuestRow.style.display = "none";
      if (candidateActiveRow) candidateActiveRow.style.display = "flex";
      if (careerSubnavTabs) careerSubnavTabs.style.display = "flex";

      if (candidateNameBadge) candidateNameBadge.textContent = candidateState.user.name;
      if (candidateEmailBadge) candidateEmailBadge.textContent = candidateState.user.email;
      if (candidateAvatarInit) {
        var initial = (candidateState.user.name || "U").charAt(0).toUpperCase();
        candidateAvatarInit.textContent = initial;
      }
    } else {
      if (candidateGuestRow) candidateGuestRow.style.display = "flex";
      if (candidateActiveRow) candidateActiveRow.style.display = "none";
      if (careerSubnavTabs) careerSubnavTabs.style.display = "none";
    }
  }

  async function loadOpenings() {
    try {
      var res = await fetch("/api/openings");
      var data = await res.json();
      if (data.ok) {
        candidateState.openings = data.openings || [];
        renderOpenings();
      }
    } catch (err) {
      console.error("Failed to load openings", err);
      if (openingsListCont) {
        openingsListCont.innerHTML = '<p class="career-panel-empty">Failed to load openings. Please try again.</p>';
      }
    }
  }

  function renderOpenings() {
    if (!openingsListCont) return;
    var ops = candidateState.openings;
    if (panelOpeningsCount) panelOpeningsCount.textContent = ops.length;

    if (!ops.length) {
      openingsListCont.innerHTML = '<p class="career-panel-empty">No openings are currently listed. Check back soon or reach out directly.</p>';
      return;
    }

    openingsListCont.innerHTML = ops.map(function(op) {
      return (
        '<div class="career-opening-card">' +
          '<div class="career-opening-header">' +
            '<h4 class="career-opening-title">' + escapeHtml(op.title) + '</h4>' +
            '<div class="career-tags-wrap">' +
              '<span class="career-tag career-tag-highlight">' + escapeHtml(op.department) + '</span>' +
              '<span class="career-tag">' + escapeHtml(op.location) + '</span>' +
              '<span class="career-tag">' + escapeHtml(op.job_type) + '</span>' +
              (op.experience ? '<span class="career-tag">' + escapeHtml(op.experience) + '</span>' : '') +
            '</div>' +
          '</div>' +
          '<p class="career-opening-desc">' + escapeHtml(op.description) + '</p>' +
          (op.requirements ? '<div class="career-opening-reqs"><strong>Key Requirements:</strong> ' + escapeHtml(op.requirements) + '</div>' : '') +
          '<div class="career-opening-footer">' +
            '<button type="button" class="btn-apply-job" data-id="' + op.id + '">' +
              '<span>Apply Now</span>' +
              '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>' +
            '</button>' +
          '</div>' +
        '</div>'
      );
    }).join("");

    // Wire up Apply buttons (directly opens application form from the left panel)
    openingsListCont.querySelectorAll(".btn-apply-job").forEach(function(btn) {
      btn.addEventListener("click", function() {
        var opId = btn.getAttribute("data-id");
        var op = candidateState.openings.find(function(o) { return String(o.id) === String(opId); });
        if (!op) return;

        openApplicationPanel(op);
      });
    });
  }

  async function loadCandidateApplications() {
    if (!candidateState.isLoggedIn) return;
    try {
      var res = await fetch("/api/candidate/my-applications");
      var data = await res.json();
      if (data.ok) {
        candidateState.myApplications = data.applications || [];
        renderCandidateApplications();
      }
    } catch (err) {
      console.warn("Failed loading candidate applications", err);
    }
  }

  function renderCandidateApplications() {
    if (!myAppsListCont) return;
    var apps = candidateState.myApplications;
    if (panelMyAppsCount) panelMyAppsCount.textContent = apps.length;

    if (!apps.length) {
      myAppsListCont.innerHTML = '<p class="career-panel-empty">You haven\'t submitted any applications yet. View our open roles above to apply.</p>';
      return;
    }

    myAppsListCont.innerHTML = apps.map(function(app) {
      var pillClass = "status-badge-submitted";
      var step1Done = true, step2Done = false, step3Done = false, step4Done = false;
      var step2Active = false, step3Active = false, step4Active = false;

      if (app.status === "Under Review") {
        pillClass = "status-badge-review";
        step2Active = true;
      } else if (app.status === "Shortlisted") {
        pillClass = "status-badge-shortlisted";
        step2Done = true;
        step3Active = true;
      } else if (app.status === "Interview Scheduled") {
        pillClass = "status-badge-interview";
        step2Done = true;
        step3Done = true;
        step4Active = true;
      } else if (app.status === "Offer Extended") {
        pillClass = "status-badge-offer";
        step2Done = true;
        step3Done = true;
        step4Done = true;
      } else if (app.status === "Rejected") {
        pillClass = "status-badge-rejected";
      }

      var dateStr = new Date(app.created_at).toLocaleDateString("en-US", {
        month: "short", day: "numeric", year: "numeric"
      });

      return (
        '<div class="candidate-app-item">' +
          '<div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px;">' +
            '<div>' +
              '<h5 class="candidate-app-title">' + escapeHtml(app.opening_title) + '</h5>' +
              '<div class="candidate-app-meta">Applied on ' + dateStr + (app.department ? ' · ' + escapeHtml(app.department) : '') + '</div>' +
            '</div>' +
            '<span class="candidate-status-badge ' + pillClass + '">' + escapeHtml(app.status) + '</span>' +
          '</div>' +
          '<div class="candidate-tracker-steps">' +
            '<div class="step-node ' + (step1Done ? 'done' : '') + '">' +
              '<div class="step-dot">' + (step1Done ? '✓' : '1') + '</div>' +
              '<span class="step-label">Submitted</span>' +
            '</div>' +
            '<div class="step-node ' + (step2Done ? 'done' : (step2Active ? 'active' : '')) + '">' +
              '<div class="step-dot">' + (step2Done ? '✓' : '2') + '</div>' +
              '<span class="step-label">Review</span>' +
            '</div>' +
            '<div class="step-node ' + (step3Done ? 'done' : (step3Active ? 'active' : '')) + '">' +
              '<div class="step-dot">' + (step3Done ? '✓' : '3') + '</div>' +
              '<span class="step-label">Interview</span>' +
            '</div>' +
            '<div class="step-node ' + (step4Done ? 'done' : (step4Active ? 'active' : '')) + '">' +
              '<div class="step-dot">' + (step4Done ? '✓' : '4') + '</div>' +
              '<span class="step-label">Decision</span>' +
            '</div>' +
          '</div>' +
        '</div>'
      );
    }).join("");
  }

  // Subnav tab listeners
  if (tabOpeningsBtn) {
    tabOpeningsBtn.addEventListener("click", function() {
      tabOpeningsBtn.classList.add("active");
      if (tabMyAppsBtn) tabMyAppsBtn.classList.remove("active");
      if (careerViewOpenings) careerViewOpenings.style.display = "block";
      if (careerViewMyApps) careerViewMyApps.style.display = "none";
    });
  }

  if (tabMyAppsBtn) {
    tabMyAppsBtn.addEventListener("click", function() {
      tabMyAppsBtn.classList.add("active");
      if (tabOpeningsBtn) tabOpeningsBtn.classList.remove("active");
      if (careerViewOpenings) careerViewOpenings.style.display = "none";
      if (careerViewMyApps) careerViewMyApps.style.display = "block";
      loadCandidateApplications();
    });
  }

  // Candidate logout
  if (btnCandidateLogout) {
    btnCandidateLogout.addEventListener("click", async function() {
      await fetch("/api/candidate/logout", { method: "POST" });
      candidateState.isLoggedIn = false;
      candidateState.user = null;
      renderCandidateBar();
      if (tabOpeningsBtn) tabOpeningsBtn.click();
    });
  }

  // Auth Modal switch via hover links
  var linkToRegister = document.getElementById("linkToRegister");
  if (linkToRegister) {
    linkToRegister.addEventListener("click", function(e) {
      e.preventDefault();
      if (formCandidateSignIn) formCandidateSignIn.style.display = "none";
      if (formCandidateRegister) formCandidateRegister.style.display = "block";
      var h = document.getElementById("authModalHeading");
      if (h) h.textContent = "Candidate Registration";
      if (authAlertError) authAlertError.style.display = "none";
    });
  }

  var linkToSignIn = document.getElementById("linkToSignIn");
  if (linkToSignIn) {
    linkToSignIn.addEventListener("click", function(e) {
      e.preventDefault();
      if (formCandidateRegister) formCandidateRegister.style.display = "none";
      if (formCandidateSignIn) formCandidateSignIn.style.display = "block";
      var h = document.getElementById("authModalHeading");
      if (h) h.textContent = "Candidate Sign In";
      if (authAlertError) authAlertError.style.display = "none";
    });
  }

  // Open / Close Auth Modal
  if (btnOpenCandidateAuth) {
    btnOpenCandidateAuth.addEventListener("click", function() {
      openCandidateAuthModal();
    });
  }
  if (btnCloseAuthModal) {
    btnCloseAuthModal.addEventListener("click", closeCandidateAuthModal);
  }

  // Submit Sign In
  if (formCandidateSignIn) {
    formCandidateSignIn.addEventListener("submit", async function(e) {
      e.preventDefault();
      var email = document.getElementById("txtSignInEmail").value.trim();
      var password = document.getElementById("txtSignInPassword").value.trim();

      try {
        var res = await fetch("/api/candidate/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: email, password: password })
        });
        var data = await res.json();
        if (data.ok) {
          candidateState.isLoggedIn = true;
          candidateState.user = data.candidate;
          renderCandidateBar();
          loadCandidateApplications();
          closeCandidateAuthModal();

          if (candidateState.pendingOpening) {
            var targetOp = candidateState.pendingOpening;
            candidateState.pendingOpening = null;
            openApplicationPanel(targetOp);
          } else {
            // If user has applied previously, switch directly to their status
            setTimeout(function() {
              if (candidateState.myApplications && candidateState.myApplications.length && tabMyAppsBtn) {
                tabMyAppsBtn.click();
              }
            }, 300);
          }
        } else {
          if (authAlertError) {
            authAlertError.textContent = data.error || "Login failed.";
            authAlertError.style.display = "block";
            authAlertError.style.background = "#FEF2F2";
            authAlertError.style.color = "#EF4444";
            authAlertError.style.borderColor = "#FECACA";
          }
        }
      } catch (err) {
        if (authAlertError) {
          authAlertError.textContent = "Server error. Please try again.";
          authAlertError.style.display = "block";
        }
      }
    });
  }

  // Submit Register
  if (formCandidateRegister) {
    formCandidateRegister.addEventListener("submit", async function(e) {
      e.preventDefault();
      var name = document.getElementById("txtRegName").value.trim();
      var email = document.getElementById("txtRegEmail").value.trim();
      var phone = document.getElementById("txtRegPhone").value.trim();
      var password = document.getElementById("txtRegPassword").value.trim();

      try {
        var res = await fetch("/api/candidate/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: name, email: email, phone: phone, password: password })
        });
        var data = await res.json();
        if (data.ok) {
          candidateState.isLoggedIn = true;
          candidateState.user = data.candidate;
          renderCandidateBar();
          loadCandidateApplications();
          closeCandidateAuthModal();

          if (candidateState.pendingOpening) {
            var targetOp = candidateState.pendingOpening;
            candidateState.pendingOpening = null;
            openApplicationPanel(targetOp);
          }
        } else {
          if (authAlertError) {
            authAlertError.textContent = data.error || "Registration failed.";
            authAlertError.style.display = "block";
            authAlertError.style.background = "#FEF2F2";
            authAlertError.style.color = "#EF4444";
            authAlertError.style.borderColor = "#FECACA";
          }
        }
      } catch (err) {
        if (authAlertError) {
          authAlertError.textContent = "Server error during registration.";
          authAlertError.style.display = "block";
        }
      }
    });
  }

  // Resume File Selection Feedback
  var resumeInput = document.getElementById("appCandidateResume");
  var fileUploadName = document.getElementById("fileUploadName");
  var dropAreaResume = document.getElementById("dropAreaResume");

  if (resumeInput) {
    resumeInput.addEventListener("change", function() {
      if (resumeInput.files && resumeInput.files[0]) {
        var file = resumeInput.files[0];
        var sizeKb = Math.round(file.size / 1024);
        var sizeStr = sizeKb > 1024 ? (sizeKb / 1024).toFixed(1) + " MB" : sizeKb + " KB";
        if (fileUploadName) {
          fileUploadName.textContent = "✓ " + file.name + " (" + sizeStr + ")";
        }
        if (dropAreaResume) {
          dropAreaResume.classList.add("has-file");
        }
      } else {
        if (fileUploadName) {
          fileUploadName.textContent = "Upload Resume (PDF / DOC)";
        }
        if (dropAreaResume) {
          dropAreaResume.classList.remove("has-file");
        }
      }
    });
  }

  // Application Form Submit
  var candidateAppForm = document.getElementById("candidateApplicationForm");
  if (candidateAppForm) {
    candidateAppForm.addEventListener("submit", async function(e) {
      e.preventDefault();
      var errAlert = document.getElementById("applicationErrorAlert");
      if (errAlert) errAlert.style.display = "none";

      var openingId = document.getElementById("appOpeningId").value;
      var name = document.getElementById("appCandidateName").value.trim();
      var email = document.getElementById("appCandidateEmail").value.trim();
      var phone = document.getElementById("appCandidatePhone").value.trim();
      var exp = document.getElementById("appCandidateExp").value.trim();
      var portfolio = document.getElementById("appCandidatePortfolio").value.trim();
      var notes = document.getElementById("appCandidateNotes").value.trim();

      var resumeFile = resumeInput && resumeInput.files ? resumeInput.files[0] : null;
      if (!resumeFile) {
        if (errAlert) {
          errAlert.textContent = "Please attach your Resume / CV (PDF or DOC).";
          errAlert.style.display = "block";
        }
        return;
      }

      var submitBtn = document.getElementById("btnSubmitApplication");
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = "<span>Submitting...</span>";
      }

      var formData = new FormData();
      formData.append("opening_id", openingId);
      formData.append("name", name);
      formData.append("email", email);
      formData.append("phone", phone);
      formData.append("experience", exp);
      formData.append("portfolio", portfolio);
      formData.append("notes", notes);
      formData.append("resume", resumeFile);

      try {
        var res = await fetch("/api/candidate/apply", {
          method: "POST",
          body: formData
        });
        var data = await res.json();
        if (data.ok) {
          // Cache user details so they are auto-filled for future applications
          try {
            localStorage.setItem("rzmt_applicant_details", JSON.stringify({
              name: name,
              email: email,
              phone: phone
            }));
          } catch (e) {}

          if (data.candidate) {
            candidateState.isLoggedIn = true;
            candidateState.user = data.candidate;
            renderCandidateBar();
            loadCandidateApplications();
          }

          closeApplicationPanel();
          candidateAppForm.reset();
          if (fileUploadName) fileUploadName.textContent = "Upload Resume (PDF / DOC)";
          if (dropAreaResume) dropAreaResume.classList.remove("has-file");
          
          openCareerPanel();
          if (tabMyAppsBtn) tabMyAppsBtn.click();
          alert("Application submitted successfully! Stored in database & confirmation email sent.");
        } else {
          if (errAlert) {
            errAlert.textContent = data.error || "Failed to submit application.";
            errAlert.style.display = "block";
          }
        }
      } catch (err) {
        if (errAlert) {
          errAlert.textContent = "Server error while submitting application.";
          errAlert.style.display = "block";
        }
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<span>Submit</span><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>';
        }
      }
    });
  }

  // Panel triggers
  if (careerInfoBtn) {
    careerInfoBtn.addEventListener("click", function() {
      setActiveNav("careers");
      navigateTo("#contact");
      window.location.hash = "#contact";
      setTimeout(openCareerPanel, 300);
    });
  }

  if (careerClose) {
    careerClose.addEventListener("click", closeCareerPanel);
  }

  if (careerBackdrop) {
    careerBackdrop.addEventListener("click", function() {
      if (applicationPanel && applicationPanel.classList.contains("open")) {
        closeApplicationPanel();
      } else {
        closeCareerPanel();
      }
    });
  }

  if (applicationPanelClose) {
    applicationPanelClose.addEventListener("click", closeApplicationPanel);
  }

  if (btnBackToOpenings) {
    btnBackToOpenings.addEventListener("click", function() {
      closeApplicationPanel();
      openCareerPanel();
    });
  }

  // Check auth and openings on initial load
  checkCandidateAuth();
  loadOpenings();

  document.addEventListener("keydown", function(e) {
    if (e.key === "Escape") {
      if (candidateAuthModal && candidateAuthModal.classList.contains("open")) {
        closeCandidateAuthModal();
      } else if (applicationPanel && applicationPanel.classList.contains("open")) {
        closeApplicationPanel();
      } else if (careerPanel && careerPanel.classList.contains("open")) {
        closeCareerPanel();
      }
    }
  });


  // 7. ACCESSIBLE MODALS FOR PRIVACY & TERMS
  var privacyModal = document.getElementById("privacy-modal");
  var termsModal = document.getElementById("terms-modal");
  var openPrivacyBtn = document.getElementById("open-privacy-btn");
  var openTermsBtn = document.getElementById("open-terms-btn");
  var closePrivacyBtn = document.getElementById("close-privacy-btn");
  var closeTermsBtn = document.getElementById("close-terms-btn");

  function openModal(modal) {
    if (modal) {
      modal.classList.add("open");
      document.body.style.overflow = "hidden";
    }
  }

  function closeModal(modal) {
    if (modal) {
      modal.classList.remove("open");
      document.body.style.overflow = "";
    }
  }

  if (openPrivacyBtn) {
    openPrivacyBtn.addEventListener("click", function() { openModal(privacyModal); });
  }
  if (closePrivacyBtn) {
    closePrivacyBtn.addEventListener("click", function() { closeModal(privacyModal); });
  }

  if (openTermsBtn) {
    openTermsBtn.addEventListener("click", function() { openModal(termsModal); });
  }
  if (closeTermsBtn) {
    closeTermsBtn.addEventListener("click", function() { closeModal(termsModal); });
  }

  [privacyModal, termsModal].forEach(function(modal) {
    if (modal) {
      modal.addEventListener("click", function(e) {
        if (e.target === modal) {
          closeModal(modal);
        }
      });
    }
  });

  window.addEventListener("keydown", function(e) {
    if (e.key === "Escape") {
      closeModal(privacyModal);
      closeModal(termsModal);
    }
  });

  // 8. Step Cards Interactive Details Uncover
  var stepCards = document.querySelectorAll(".step-card");
  stepCards.forEach(function(card) {
    var btn = card.querySelector(".step-expand-btn");
    var hint = card.querySelector(".step-action-hint");

    function toggleDetails(e) {
      if (e) { e.stopPropagation(); }
      var isExpanded = card.classList.toggle("expanded");
      if (btn) {
        btn.setAttribute("aria-expanded", isExpanded ? "true" : "false");
      }
      if (hint) {
        hint.textContent = isExpanded ? "Hide details" : "Service details";
      }
    }

    if (btn) {
      btn.addEventListener("click", toggleDetails);
    }
    card.addEventListener("click", function(e) {
      if (e.target.closest("button") === btn) return;
      toggleDetails(e);
    });
  });

  // =========================================================
  // CAPABILITIES — SCROLL-DRIVEN PHOTO ALBUM (Our Work page)
  // =========================================================
  (function initCapsAlbum() {
    var wrapper = document.getElementById("capsAlbumWrapper");
    var stage   = document.getElementById("capsAlbumStage");
    var cards   = Array.prototype.slice.call(
      document.querySelectorAll(".caps-album-card")
    );
    var dots    = Array.prototype.slice.call(
      document.querySelectorAll(".caps-dot")
    );
    var scrollLabel = document.getElementById("capsScrollLabel");

    if (!wrapper || !cards.length) return;

    var TOTAL    = cards.length;
    var current  = -1;

    function showCard(idx) {
      idx = Math.max(0, Math.min(TOTAL - 1, idx));
      if (idx === current) return;
      current = idx;

      cards.forEach(function(card, i) {
        card.classList.remove("is-active", "is-prev");
        if (i < idx)      card.classList.add("is-prev");
        else if (i === idx) card.classList.add("is-active");
      });

      dots.forEach(function(dot, i) {
        dot.classList.toggle("is-active", i === idx);
      });

      if (scrollLabel) {
        scrollLabel.classList.toggle("hidden", idx === TOTAL - 1);
      }
    }

    function onScroll() {
      var rect       = wrapper.getBoundingClientRect();
      var wrapperH   = wrapper.offsetHeight;
      var viewH      = window.innerHeight;
      var scrolled   = -rect.top;
      var scrollable = wrapperH - viewH;
      var progress   = Math.max(0, Math.min(1, scrolled / scrollable));
      var idx = Math.min(TOTAL - 1, Math.floor(progress * TOTAL));
      showCard(idx);
    }

    dots.forEach(function(dot) {
      dot.addEventListener("click", function() {
        var idx = parseInt(this.getAttribute("data-idx"), 10);
        var wrapperH   = wrapper.offsetHeight;
        var viewH      = window.innerHeight;
        var scrollable = wrapperH - viewH;
        var targetProgress = idx / TOTAL + 0.01;
        var targetTop  = wrapper.offsetTop + targetProgress * scrollable;
        window.scrollTo({ top: targetTop, behavior: "smooth" });
      });
    });

    var touchStartX = 0;
    var touchStartY = 0;

    if (stage) {
      stage.addEventListener("touchstart", function(e) {
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
      }, { passive: true });

      stage.addEventListener("touchend", function(e) {
        var dx = e.changedTouches[0].clientX - touchStartX;
        var dy = e.changedTouches[0].clientY - touchStartY;
        if (Math.abs(dx) < 40 || Math.abs(dx) < Math.abs(dy)) return;
        var target = dx < 0
          ? Math.min(TOTAL - 1, current + 1)
          : Math.max(0, current - 1);
        if (target === current) return;
        var wrapperH   = wrapper.offsetHeight;
        var viewH      = window.innerHeight;
        var scrollable = wrapperH - viewH;
        var targetProgress = target / TOTAL + 0.01;
        var targetTop  = wrapper.offsetTop + targetProgress * scrollable;
        window.scrollTo({ top: targetTop, behavior: "smooth" });
      }, { passive: true });
    }

    showCard(0);
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  })();

  // ── VISITOR TELEMETRY, REAL-TIME IP FETCH & ATTRACTION TRACKER ──
  (function initVisitorTracker() {
    try {
      var storageKey = "rzmt_vid";
      var vid = localStorage.getItem(storageKey);
      if (!vid) {
        vid = "vid_" + Math.random().toString(36).substring(2, 9) + "_" + Date.now().toString(36);
        localStorage.setItem(storageKey, vid);
      }

      var currentPath = window.location.pathname + (window.location.hash || "");
      var startTime = Date.now();
      var maxScrollPct = 0;
      var hasSentAttraction = false;

      // Function to post visit hit to backend
      function sendVisitHit(detectedIp, detectedLocation) {
        var payload = {
          visitor_id: vid,
          page: window.location.pathname + (window.location.hash || ""),
          referrer: document.referrer || "",
          screen_width: window.innerWidth || screen.width
        };
        if (detectedIp) payload.client_ip = detectedIp;
        if (detectedLocation) payload.location = detectedLocation;

        fetch("/api/telemetry/visit", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        }).catch(function() {});
      }

      // 1. Initial immediate visit hit
      sendVisitHit();

      // 2. Client-side public IP & Geolocation fetch
      (function fetchClientIp() {
        var cachedNet = sessionStorage.getItem("rzmt_client_net");
        if (cachedNet) {
          try {
            var parsed = JSON.parse(cachedNet);
            if (parsed && parsed.ip) {
              sendVisitHit(parsed.ip, parsed.location);
              return;
            }
          } catch(e) {}
        }

        // Fast IP lookup (timeout 4s to never block page performance)
        fetch("https://api64.ipify.org?format=json")
          .then(function(res) { return res.json(); })
          .then(function(data) {
            if (data && data.ip) {
              var clientIp = data.ip;
              // Secondary location lookup
              fetch("https://ipapi.co/" + clientIp + "/json/")
                .then(function(gr) { return gr.json(); })
                .then(function(gd) {
                  var parts = [];
                  if (gd.city) parts.push(gd.city);
                  if (gd.region) parts.push(gd.region);
                  if (gd.country_name || gd.country) parts.push(gd.country_name || gd.country);
                  if (gd.org) parts.push("(" + gd.org + ")");
                  var locStr = parts.join(", ");
                  sessionStorage.setItem("rzmt_client_net", JSON.stringify({ ip: clientIp, location: locStr }));
                  sendVisitHit(clientIp, locStr);
                })
                .catch(function() {
                  sessionStorage.setItem("rzmt_client_net", JSON.stringify({ ip: clientIp, location: "" }));
                  sendVisitHit(clientIp, "");
                });
            }
          })
          .catch(function() {});
      })();

      // 3. Track scroll depth
      function checkScroll() {
        var h = document.documentElement;
        var b = document.body;
        var st = h.scrollTop || b.scrollTop;
        var sh = h.scrollHeight || b.scrollHeight;
        var ch = h.clientHeight;
        if (sh > ch) {
          var pct = Math.round((st / (sh - ch)) * 100);
          if (pct > maxScrollPct) maxScrollPct = Math.min(100, pct);
          if (maxScrollPct >= 60 && !hasSentAttraction) {
            triggerAttraction("Deep page scroll (60%+)");
          }
        }
      }
      window.addEventListener("scroll", checkScroll, { passive: true });

      // 4. Track interactive attraction events
      function triggerAttraction(interactionName) {
        var elapsed = Math.round((Date.now() - startTime) / 1000);
        fetch("/api/telemetry/engage", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            visitor_id: vid,
            duration_seconds: elapsed,
            scroll_percent: maxScrollPct,
            interaction: interactionName
          })
        }).catch(function() {});
        hasSentAttraction = true;
      }

      // Time-based attraction (spending >= 30 seconds on site)
      setTimeout(function() {
        triggerAttraction("Spent 30s+ actively on site");
      }, 30000);

      // Heartbeat every 15 seconds to keep "Online Now" status live
      setInterval(function() {
        if (document.visibilityState === "visible") {
          var elapsed = Math.round((Date.now() - startTime) / 1000);
          fetch("/api/telemetry/engage", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              visitor_id: vid,
              duration_seconds: elapsed,
              scroll_percent: maxScrollPct,
              interaction: ""
            })
          }).catch(function() {});
        }
      }, 15000);

      // Listen for interactive engagement clicks
      document.addEventListener("click", function(e) {
        var target = e.target;
        if (!target) return;
        if (target.closest("#careerInfoBtn") || target.closest(".btn-apply-job") || target.closest("#tabOpeningsBtn") || target.closest("#btnOpenCandidateAuth")) {
          triggerAttraction("Explored Careers & Openings");
        } else if (target.closest(".step-node") || target.closest(".cap-nav-btn") || target.closest(".cap-card")) {
          triggerAttraction("Explored Hardware Container Telemetry Specs");
        } else if (target.closest('a[href*="contact"]') || target.closest("#careerContactLink")) {
          triggerAttraction("Explored Contact & Chennai Office");
        }
      });

      // Track hash changes (SPA Navigation)
      window.addEventListener("hashchange", function() {
        sendVisitHit();
      });

      // Send beacon on page exit / unload
      function onPageExit() {
        var elapsed = Math.round((Date.now() - startTime) / 1000);
        var payload = JSON.stringify({
          visitor_id: vid,
          duration_seconds: elapsed,
          scroll_percent: maxScrollPct
        });
        if (navigator.sendBeacon) {
          navigator.sendBeacon("/api/telemetry/engage", new Blob([payload], { type: "application/json" }));
        }
      }
      window.addEventListener("pagehide", onPageExit);
      document.addEventListener("visibilitychange", function() {
        if (document.visibilityState === "hidden") onPageExit();
      });
    } catch (e) {}
  })();

})();
