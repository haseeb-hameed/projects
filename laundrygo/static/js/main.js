document.addEventListener("DOMContentLoaded", () => {
  const nav = document.querySelector(".nav-public");
  if (nav) {
    const onScroll = () => nav.classList.toggle("scrolled", window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  const toggle = document.querySelector("[data-sidebar-toggle]");
  const sidebar = document.querySelector(".sidebar");
  if (toggle && sidebar) {
    toggle.addEventListener("click", () => sidebar.classList.toggle("open"));
  }

  document.querySelectorAll("[data-qty]").forEach((wrap) => {
    const input = wrap.querySelector("input");
    wrap.querySelectorAll("button").forEach((btn) => {
      btn.addEventListener("click", () => {
        const step = parseFloat(btn.dataset.step);
        const min = parseFloat(input.min || "0");
        const next = Math.max(min, (parseFloat(input.value || "0") + step));
        input.value = Number.isInteger(next) ? next : next.toFixed(1);
        input.dispatchEvent(new Event("input", { bubbles: true }));
      });
    });
  });

  const bookForm = document.getElementById("book-form");
  if (bookForm) calcBooking();
});

function calcBooking() {
  const form = document.getElementById("book-form");
  if (!form) return;
  const freeMin = parseFloat(form.dataset.freeMin || "250");
  const pickupFee = parseFloat(form.dataset.pickupFee || "40");
  const expressFee = parseFloat(form.dataset.expressFee || "80");

  const update = () => {
    let sub = 0;
    form.querySelectorAll("[data-price]").forEach((row) => {
      const price = parseFloat(row.dataset.price);
      const qty = parseFloat(row.querySelector("input").value || "0");
      const line = price * qty;
      sub += line;
      const lineEl = row.querySelector("[data-line]");
      if (lineEl) lineEl.textContent = line > 0 ? "₹" + line.toFixed(0) : "—";
    });
    const express = form.querySelector("#is_express")?.checked;
    const pFee = sub >= freeMin || sub === 0 ? 0 : pickupFee;
    const eFee = express && sub > 0 ? expressFee : 0;
    const total = sub + pFee + eFee;
    setText("sum-sub", sub);
    setText("sum-pickup", pFee);
    setText("sum-express", eFee);
    setText("sum-total", total);
    const hint = document.getElementById("pickup-hint");
    if (hint) {
      hint.textContent =
        sub >= freeMin
          ? "Free pickup unlocked"
          : sub === 0
          ? "Add items to see fees"
          : "₹" + (freeMin - sub).toFixed(0) + " more for free pickup";
    }
  };

  form.addEventListener("input", update);
  form.addEventListener("change", update);
  update();
}

function setText(id, n) {
  const el = document.getElementById(id);
  if (el) el.textContent = "₹" + Number(n).toFixed(0);
}
