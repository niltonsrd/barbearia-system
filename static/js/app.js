// Fade-in global
document.addEventListener("DOMContentLoaded", () => {
  const steps = document.querySelectorAll(".step");
  const nextButtons = document.querySelectorAll(".next");

  let currentStep = 0;

  nextButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const inputs = steps[currentStep].querySelectorAll("select, input");
      let valid = true;

      inputs.forEach(i => {
        if (!i.value) valid = false;
      });

      if (!valid) {
        alert("Preencha antes de continuar");
        return;
      }

      steps[currentStep].classList.remove("active");
      currentStep++;
      steps[currentStep].classList.add("active");
    });
  });
});


// Botão loading
document.querySelectorAll("form").forEach(form => {
  form.addEventListener("submit", () => {
    const btn = form.querySelector("button");
    if (btn) {
      btn.innerText = "Processando...";
      btn.disabled = true;
    }
  });
});

// Fade on scroll
const observer = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if (e.isIntersecting) e.target.classList.add("fade-up");
  });
});

document.querySelectorAll(".card").forEach(el => observer.observe(el));

// Button loading
document.querySelectorAll("form").forEach(form => {
  form.addEventListener("submit", () => {
    const btn = form.querySelector("button");
    if (btn) {
      btn.innerHTML = "⏳ Processando...";
      btn.disabled = true;
    }
  });
});

// subtle floating animation
document.querySelectorAll(".card").forEach(card => {
  card.animate(
    [
      { transform: "translateY(0px)" },
      { transform: "translateY(-4px)" },
      { transform: "translateY(0px)" }
    ],
    {
      duration: 6000,
      iterations: Infinity,
      easing: "ease-in-out"
    }
  );
});

// ---------- TOAST ----------
function showToast(message, type = "success") {
  const toast = document.getElementById("toast");
  toast.innerText = message;
  toast.className = `toast show ${type}`;

  setTimeout(() => {
    toast.classList.remove("show");
  }, 2500);
}

// ---------- BUTTON LOADING ----------
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form").forEach(form => {
    form.addEventListener("submit", e => {
      const btn = form.querySelector("button[type='submit']");
      if (btn) {
        btn.classList.add("btn-loading");
        btn.innerText = "";
      }
    });
  });
});


document.querySelectorAll('.service-card').forEach(card => {
    const img = card.dataset.image;
  if (img) {
    card.style.backgroundImage =
    `url('/static/uploads/servicos/${img}')`;
    }
  });
