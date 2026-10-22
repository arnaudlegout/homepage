/* Menu burger des pages : ouverture, fermeture au clic sur un lien et à Échap. */
(function () {
  var btn = document.querySelector('.nav__burger');
  var menu = document.getElementById('nav-menu');
  if (!btn || !menu) return;
  function closeMenu() {
    btn.setAttribute('aria-expanded', 'false');
    btn.setAttribute('aria-label', 'Ouvrir le menu de navigation');
    menu.classList.remove('is-open');
  }
  btn.addEventListener('click', function () {
    var open = btn.getAttribute('aria-expanded') === 'true';
    btn.setAttribute('aria-expanded', String(!open));
    btn.setAttribute('aria-label', open ? 'Ouvrir le menu de navigation' : 'Fermer le menu de navigation');
    menu.classList.toggle('is-open', !open);
  });
  menu.addEventListener('click', function (e) {
    if (e.target.tagName === 'A') closeMenu();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeMenu();
  });
})();
