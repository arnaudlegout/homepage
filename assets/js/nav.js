/* Navigation des pages.
   - Menu burger (sous 800px) : ouverture et fermeture par le bouton ; à l'ouverture le
     focus entre dans le menu (le menu précède le bouton dans le code, Tab le sauterait),
     Échap le referme et rend le focus au bouton ; un clic sur un lien le referme.
   - Sous-menus de la barre (800px et plus), ouverts au survol ou au focus : Échap les
     referme sans déplacer le pointeur ni le focus (WCAG 1.4.13). */
(function () {
  var btn = document.querySelector('.nav__burger');
  var menu = document.getElementById('nav-menu');
  if (!btn || !menu) return;

  function isOpen() { return btn.getAttribute('aria-expanded') === 'true'; }

  function setOpen(open) {
    btn.setAttribute('aria-expanded', String(open));
    btn.setAttribute('aria-label', open ? 'Fermer le menu de navigation' : 'Ouvrir le menu de navigation');
    menu.classList.toggle('is-open', open);
  }

  btn.addEventListener('click', function () {
    var open = !isOpen();
    setOpen(open);
    if (open) {
      var first = menu.querySelector('a');
      if (first) first.focus();
    }
  });
  menu.addEventListener('click', function (e) {
    if (e.target.closest('a')) setOpen(false);
  });

  var items = document.querySelectorAll('.nav__item--has-dropdown');
  items.forEach(function (item) {
    item.addEventListener('mouseleave', function () { item.classList.remove('is-dismissed'); });
    item.addEventListener('focusout', function (e) {
      if (!item.contains(e.relatedTarget)) item.classList.remove('is-dismissed');
    });
  });

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    if (isOpen()) {
      setOpen(false);
      btn.focus();
      return;
    }
    items.forEach(function (item) {
      if (item.matches(':hover') || item.contains(document.activeElement)) item.classList.add('is-dismissed');
    });
  });
})();
