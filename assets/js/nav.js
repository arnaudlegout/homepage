/* Navigation des pages.
   - Menu burger (sous 900px) : ouverture et fermeture par le bouton ; à l'ouverture le
     focus entre dans le menu (le menu précède le bouton dans le code, Tab le sauterait),
     Échap le referme et rend le focus au bouton ; un clic sur un lien le referme.
   - Sous-menus de la barre (900px et plus), ouverts au survol ou au focus : Échap les
     referme sans déplacer le pointeur ni le focus (WCAG 1.4.13). */
(function () {
  // 404.html, la même page pour toutes les URL manquantes, porte la barre et le pied de
  // page anglais dans des <template> : pour une URL anglaise (son script de <head> a mis
  // <html lang="en">), on les met à la place des français avant de brancher le menu.
  if (document.documentElement.lang === 'en') {
    ['header', 'footer'].forEach(function (part) {
      var tpl = document.querySelector('template[data-chrome="' + part + '-en"]');
      var current = document.querySelector('.' + part);
      if (tpl && current) current.replaceWith(tpl.content.cloneNode(true));
    });
  }

  var btn = document.querySelector('.nav__burger');
  var menu = document.getElementById('nav-menu');
  if (!btn || !menu) return;
  var LABELS = document.documentElement.lang === 'en'
    ? { open: 'Open the navigation menu', close: 'Close the navigation menu' }
    : { open: 'Ouvrir le menu de navigation', close: 'Fermer le menu de navigation' };

  function isOpen() { return btn.getAttribute('aria-expanded') === 'true'; }

  function setOpen(open) {
    btn.setAttribute('aria-expanded', String(open));
    btn.setAttribute('aria-label', open ? LABELS.close : LABELS.open);
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
