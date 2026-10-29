/* Executa antes da pintura: evita "piscar" ao restaurar o estado do menu lateral. */
(function () {
  var root = document.documentElement;
  root.classList.add("js");
  try {
    if (window.matchMedia("(min-width:1024px)").matches && localStorage.getItem("tccfh.sb") === "min") {
      root.classList.add("sb-collapsed");
    }
  } catch (e) { /* armazenamento indisponível: segue expandido */ }
})();
