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

    function parseLooseMoneyInput(raw) {
        var text = String(raw || "").trim();
        if (!text) {
            return null;
        }

        text = text.replace(/\s*(?:TL|TRY|USD|EUR)\s*$/i, "");
        text = text.replace(/\s/g, "");

        var normalized = text;
        if (text.indexOf(",") >= 0 && text.indexOf(".") >= 0) {
            if (text.lastIndexOf(",") > text.lastIndexOf(".")) {
                normalized = text.replace(/\./g, "").replace(",", ".");
            } else {
                normalized = text.replace(/,/g, "");
            }
        } else if (text.indexOf(",") >= 0) {
            normalized = text.replace(",", ".");
        }

        var amount = Number(normalized);
        if (!isFinite(amount)) {
            return null;
        }
        return amount;
    }

    function formatTurkishMoney(raw) {
        var amount = parseLooseMoneyInput(raw);
        if (amount === null) {
            return raw;
        }

        var fixed = amount.toFixed(2);
        var parts = fixed.split(".");
        var intPart = parts[0];
        var fracPart = parts[1];
        var sign = "";

        if (intPart.charAt(0) === "-") {
            sign = "-";
            intPart = intPart.slice(1);
        }

        intPart = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
        return sign + intPart + "," + fracPart;
    }

    function initTransactionFormAmountInput(root) {
        root = root || document;
        var form = root.querySelector("[data-transaction-form]");
        if (!form || form.dataset.amountFormatBound === "true") {
            return;
        }

        form.dataset.amountFormatBound = "true";
        var input = form.querySelector("[data-transaction-amount-input]");
        if (!input) {
            return;
        }

        function formatInputValue() {
            if (input.value.trim()) {
                input.value = formatTurkishMoney(input.value);
            }
        }

        input.addEventListener("blur", formatInputValue);
        form.formatTransactionAmountInput = formatInputValue;
        formatInputValue();
    }

    function initTransactionFormCurrency(root) {
        root = root || document;
        var form = root.querySelector("[data-transaction-form]");
        var dataEl = root.getElementById("transaction-form-currency-data");
        if (!form || !dataEl) {
            return;
        }

        if (form.dataset.currencyBound === "true") {
            return;
        }
        form.dataset.currencyBound = "true";

        var config = JSON.parse(dataEl.textContent);
        var amountLabel = form.querySelector("[data-transaction-amount-label]");
        if (!amountLabel) {
            return;
        }

        var baseLabel = amountLabel.dataset.transactionAmountLabelBase || amountLabel.textContent.trim();

        function resolveCurrency() {
            var fieldName = config.primary_account_field;
            if (!fieldName) {
                return "";
            }
            var select = form.elements.namedItem(fieldName);
            if (!select || !select.value) {
                return "";
            }
            return config.currencies_by_account_id[select.value] || "";
        }

        function updateAmountLabel() {
            var currency = resolveCurrency();
            amountLabel.textContent = currency
                ? baseLabel + " (" + currency + ")"
                : baseLabel;
        }

        (config.account_fields || []).forEach(function (fieldName) {
            var select = form.elements.namedItem(fieldName);
            if (select) {
                select.addEventListener("change", updateAmountLabel);
            }
        });

        updateAmountLabel();
        form.updateTransactionAmountLabel = updateAmountLabel;
    }

    function initTransactionFormExample(root) {
        root = root || document;
        var dataEl = root.getElementById("transaction-form-example-data");
        var form = root.querySelector("[data-transaction-form]");
        var button = root.querySelector("[data-fill-form-example]");
        if (!dataEl || !form || !button || button.dataset.exampleBound === "true") {
            return;
        }

        button.dataset.exampleBound = "true";
        var exampleValues = JSON.parse(dataEl.textContent);

        button.addEventListener("click", function () {
            Object.keys(exampleValues).forEach(function (fieldName) {
                var field = form.elements.namedItem(fieldName);
                if (!field || field.type === "file") {
                    return;
                }
                field.value = exampleValues[fieldName];
            });
            if (typeof form.updateTransactionAmountLabel === "function") {
                form.updateTransactionAmountLabel();
            }
            if (typeof form.formatTransactionAmountInput === "function") {
                form.formatTransactionAmountInput();
            }
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
        initTransactionFormCurrency(document);
        initTransactionFormAmountInput(document);
        initTransactionFormExample(document);
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
