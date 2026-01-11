GOTOWIEC: GitHub Pages + auto-aktualizacja terminarza/wyników z plk.pl

1) Wrzuć wszystko z ZIP do repo PLK_PRO (ROOT).
2) Włącz GitHub Pages: Settings → Pages → Deploy from branch → main / (root).
3) Wejdź w Actions i uruchom ręcznie:
   Actions → "Update matches.json from plk.pl" → Run workflow
   (pierwsze wypełnienie matches.json od razu)

Potem workflow poleci codziennie i będzie dopisywać wyniki / statusy "played".

Link do apki:
https://allegromatti14.github.io/PLK_PRO/plk_pro.html
