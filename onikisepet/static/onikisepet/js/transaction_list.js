(function () {
    "use strict";

    function normalizeSearch(value) {
        return value.trim().toLocaleLowerCase("tr-TR");
    }

    function setActiveTransactionFilter() {
        var bar = document.querySelector("[data-transaction-filter-bar]");
        if (!bar) {
            return;
        }

        var params = new URLSearchParams(window.location.search);
        var status = params.get("status") || "";
        var mine = params.get("mine") === "1";

        bar.querySelectorAll("[data-status-filter]").forEach(function (button) {
            button.classList.toggle(
                "filter-btn--active",
                button.dataset.statusFilter === status
            );
        });

        var mineButton = bar.querySelector("[data-mine-filter]");
        if (mineButton) {
            mineButton.classList.toggle("filter-btn--active", mine);
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

    function initBulkApprove(root) {
        var form = root.querySelector("#transaction-bulk-approve-form");
        if (!form || form.dataset.bound === "true") {
            return;
        }
        form.dataset.bound = "true";

        function visiblePendingCheckboxes() {
            return Array.prototype.filter.call(
                root.querySelectorAll("[data-pending-select]"),
                function (checkbox) {
                    var rowGroup = checkbox.closest("[data-transaction-row-group]");
                    return (
                        !rowGroup
                        || !rowGroup.classList.contains("transaction-row-group--hidden")
                    );
                }
            );
        }

        function updateBulkApproveState() {
            var submitButton = form.querySelector("[data-bulk-approve-submit]");
            var countLabel = form.querySelector("[data-bulk-approve-count]");
            var selectAll = form.querySelector("[data-select-all-pending]");
            var visible = visiblePendingCheckboxes();
            var selected = visible.filter(function (checkbox) {
                return checkbox.checked;
            });

            if (submitButton) {
                submitButton.disabled = selected.length === 0;
            }
            if (countLabel) {
                countLabel.textContent = selected.length
                    ? selected.length + " işlem seçildi"
                    : "";
            }
            if (selectAll) {
                selectAll.checked = visible.length > 0 && selected.length === visible.length;
                selectAll.indeterminate = (
                    selected.length > 0 && selected.length < visible.length
                );
            }
        }

        var selectAll = form.querySelector("[data-select-all-pending]");
        if (selectAll) {
            selectAll.addEventListener("change", function () {
                visiblePendingCheckboxes().forEach(function (checkbox) {
                    checkbox.checked = selectAll.checked;
                });
                updateBulkApproveState();
            });
        }

        root.querySelectorAll("[data-pending-select]").forEach(function (checkbox) {
            checkbox.addEventListener("change", updateBulkApproveState);
        });

        root.updateBulkApproveState = updateBulkApproveState;
        updateBulkApproveState();
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
                if (typeof root.updateBulkApproveState === "function") {
                    root.updateBulkApproveState();
                }
            });
        }

        initBulkApprove(root);

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
            setActiveTransactionFilter();
        }
    });

    document.body.addEventListener("htmx:pushedIntoHistory", function () {
        setActiveTransactionFilter();
    });
})();
