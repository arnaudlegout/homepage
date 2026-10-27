/* Questionnaire « Cinq questions avant de me contacter ».
   Sans dépendance, sans stockage, sans envoi réseau.
   Le bouton de résultat n'apparaît que si ce script s'exécute : sans
   JavaScript, les questions restent lisibles et le bouton reste masqué. */
(function () {
  'use strict';

  // Textes dans la langue de la page (<html lang>) ; les valeurs des réponses
  // (oui, non, nsp) restent les mêmes dans les deux langues.
  var EN = document.documentElement.lang === 'en';
  var RESULTS = EN ? [
    { max: 1, text: "Your situation seems under control. If you would still like an outside opinion, describe it to me." },
    { max: 3, text: "Two or three points deserve an outside look. A one-day diagnostic is usually enough to assess them." },
    { max: 5, text: "These are the answers of most of the teams I meet. This is exactly what the preliminary diagnostic helps clarify." }
  ] : [
    { max: 1, text: "Votre situation semble maîtrisée. Si vous voulez tout de même un avis extérieur, décrivez-la-moi." },
    { max: 3, text: "Deux ou trois points méritent un regard extérieur. Un diagnostic d'une journée suffit généralement à les qualifier." },
    { max: 5, text: "Ces réponses sont celles de la plupart des équipes que je rencontre. C'est exactement ce que le diagnostic préalable permet de clarifier." }
  ];
  var CTA = EN ? 'Describe your situation' : 'Décrivez-moi votre situation';

  function textFor(score) {
    for (var i = 0; i < RESULTS.length; i++) {
      if (score <= RESULTS[i].max) return RESULTS[i].text;
    }
    return RESULTS[RESULTS.length - 1].text;
  }

  function setup(quiz) {
    var actions = quiz.querySelector('[data-quiz-actions]');
    var button = quiz.querySelector('[data-quiz-submit]');
    var result = quiz.querySelector('[data-quiz-result]');
    if (!actions || !button || !result) return;

    actions.hidden = false;

    button.addEventListener('click', function () {
      var checked = quiz.querySelectorAll('.quiz__radio:checked');
      var score = 0;
      for (var i = 0; i < checked.length; i++) {
        if (checked[i].value === 'non' || checked[i].value === 'nsp') score++;
      }

      while (result.firstChild) result.removeChild(result.firstChild);

      var p = document.createElement('p');
      p.textContent = textFor(score);
      result.appendChild(p);

      var link = document.createElement('a');
      link.href = 'contact.html';
      link.className = 'btn btn--primary';
      link.textContent = CTA;
      result.appendChild(link);
    });
  }

  var quizzes = document.querySelectorAll('[data-quiz]');
  for (var i = 0; i < quizzes.length; i++) setup(quizzes[i]);
})();
