(function () {
    "use strict";

    function normalizeSearch(value) {
        return value.trim().toLocaleLowerCase("tr-TR");
    }

    function setActiveTransactionFilter(trigger) {
        var bar = document.querySelector("[data-transaction-filter-bar]");
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
        var status = params.get("status");
        var buttons = bar.querySelectorAll(".filter-btn");
        if (status === "pending" && buttons[1]) {
            buttons[1].classList.add("filter-btn--active");
        } else if (status === "approved" && buttons[2]) {
            buttons[2].classList.add("filter-btn--active");
        } else if (buttons[0]) {
            buttons[0].classList.add("filter-btn--active");
        }
    }

    function getTransactionListRoot(eventTarget) {
        if (!eventTarget) {
            return null;
        }
        if (eventTarget.id === "transaction-table") {
            return eventTarget;
        }
        var rowGroup = eventTarget.closest("[data-transaction-row-group]");
        if (rowGroup) {
            return document.getElementById("transaction-table");
        }
        return null;
    }

    function initTransactionList(root) {
        var searchInput = document.getElementById("transaction-search");
        if (searchInput && searchInput.dataset.bound !== "true") {
            searchInput.dataset.bound = "true";
            var rows = root.querySelectorAll("[data-transaction-row]");

            searchInput.addEventListener("input", function () {
                var query = normalizeSearch(searchInput.value);
                rows.forEach(function (row) {
                    var text = normalizeSearch(row.dataset.searchText || "");
                    var match = !query || text.indexOf(query) !== -1;
                    var rowGroup = row.closest("[data-transaction-row-group]");
                    if (rowGroup) {
                        rowGroup.classList.toggle("transaction-row-group--hidden", !match);
                    } else {
                        row.classList.toggle("transaction-row--hidden", !match);
                    }

                    var detailId = row.getAttribute("aria-controls");
                    var detailRow = detailId ? document.getElementById(detailId) : null;
                    if (detailRow && !match) {
                        detailRow.setAttribute("hidden", "");
                        row.setAttribute("aria-expanded", "false");
                    }
                });
            });
        }

        root.querySelectorAll("[data-transaction-row]").forEach(function (row) {
            if (row.dataset.expandBound === "true") {
                return;
            }
            row.dataset.expandBound = "true";

            function toggleDetailRow() {
                var detailId = row.getAttribute("aria-controls");
                var detailRow = detailId ? document.getElementById(detailId) : null;
                if (!detailRow) {
                    return;
                }

                var expanded = row.getAttribute("aria-expanded") === "true";
                if (expanded) {
                    detailRow.setAttribute("hidden", "");
                    row.setAttribute("aria-expanded", "false");
                } else {
                    detailRow.removeAttribute("hidden");
                    row.setAttribute("aria-expanded", "true");
                }
            }

            row.addEventListener("click", function (event) {
                if (event.target.closest("a, button, form, input, select, textarea, label")) {
                    return;
                }
                toggleDetailRow();
            });

            row.addEventListener("keydown", function (event) {
                if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    toggleDetailRow();
                }
            });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        initTransactionList(document);
        setActiveTransactionFilter();
    });

    document.body.addEventListener("htmx:afterSwap", function (event) {
        var listRoot = getTransactionListRoot(event.target);
        if (!listRoot) {
            return;
        }

        var searchInput = document.getElementById("transaction-search");
        if (searchInput) {
            delete searchInput.dataset.bound;
        }

        initTransactionList(listRoot);

        if (event.target.id === "transaction-table") {
            setActiveTransactionFilter(event.detail.requestConfig.elt);
        }
    });

    document.body.addEventListener("htmx:pushedIntoHistory", function () {
        setActiveTransactionFilter();
    });
})();
