(function () {
    "use strict";

    window.kutApp = window.kutApp || {};

    window.kutApp.getCsrfToken = function () {
        var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : "";
    };

    function initCollapsibleToggles(root) {
        root.querySelectorAll("[data-collapsible-toggle]").forEach(function (button) {
            if (button.dataset.collapsibleBound === "true") {
                return;
            }
            button.dataset.collapsibleBound = "true";

            button.addEventListener("click", function () {
                var panelId = button.getAttribute("aria-controls");
                var panel = panelId ? document.getElementById(panelId) : null;
                if (!panel) {
                    return;
                }

                var isHidden = panel.hasAttribute("hidden");
                if (isHidden) {
                    panel.removeAttribute("hidden");
                    button.setAttribute("aria-expanded", "true");
                    if (button.dataset.labelHide) {
                        button.textContent = button.dataset.labelHide;
                    }
                } else {
                    panel.setAttribute("hidden", "");
                    button.setAttribute("aria-expanded", "false");
                    if (button.dataset.labelShow) {
                        button.textContent = button.dataset.labelShow;
                    }
                }
            });
        });
    }

    function setActiveReportFilter(trigger) {
        var bar = document.querySelector("[data-report-filter-bar]");
        if (!bar) {
            return;
        }

        bar.querySelectorAll(".filter-btn").forEach(function (button) {
            button.classList.remove("filter-btn--active");
        });

        if (trigger && trigger.classList.contains("filter-btn")) {
            trigger.classList.add("filter-btn--active");
            return;
        }

        var params = new URLSearchParams(window.location.search);
        var period = params.get("period");
        if (period) {
            var match = bar.querySelector('[data-report-period="' + period + '"]');
            if (match) {
                match.classList.add("filter-btn--active");
            }
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        initCollapsibleToggles(document);
        setActiveReportFilter();
    });

    document.body.addEventListener("htmx:afterSwap", function (event) {
        if (event.target && event.target.id === "report-content") {
            initCollapsibleToggles(event.target);
            setActiveReportFilter(event.detail.requestConfig.elt);
        }
    });

    document.body.addEventListener("htmx:pushedIntoHistory", function () {
        setActiveReportFilter();
    });
})();
