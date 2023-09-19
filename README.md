## KindleVocabToAnki
Done:
* don't forget to update version
* change statistics
* add info that google translate is used
* don't keep header
* reorder default columns
* add link to github

To do:
* update all texts
* update readme
* check if I can translate providing context (GoogleTranslator(source='en', target='ru').translate('This <b>is</b> a dog'))
* add context to google translate

TWO IDEAS:
* use sidebar
* hide elements

Пара идей:
использовать with с placeholder
делать отдельные функции с cache
пример из try_placeholder https://discuss.streamlit.io/t/how-to-clear-screen-make-blank-again/30971/2

This is an app to convert Kindle vocab file so that it can be imported into Anki. There are some alternatives, but this is the only Web-based version. There is no need to install anything. And it should be usable from the Kindle itself.

https://github.com/prz3m/kind2anki https://ankiweb.net/shared/info/1621749993
good: it is an anki-addon
bad: not-customizable

* select desk to import
* select target language
* translate words
* no possibility to use stem instead of word as the key

https://fluentcards.com/kindle
good: nice interface, split by books, can export base sentence or cloze deletion
bad: not all words are translated

https://github.com/NdYAG/Kindle2Anki
need to install npm


https://github.com/wzyboy/kindle_vocab_anki
good: templates
bad: too many actions
https://github.com/wzyboy/kindle_vocab_anki/blob/master/convert_vocab.py - create anki cards


GOOGLE HOW TO PUT PROGRESSBAR LOWER



Kindlemate
good:
bad: windows only

dictionaries
https://en.pons.com/p/online-dictionary/developers/api ?

https://dictionaryapi.com/products/api-spanish-dictionary ?

ADD bold highlight

==

links:
* https://github.com/prz3m/kind2anki
* https://addon-docs.ankiweb.net/qt.html
* https://github.com/ankitects/anki/blob/main/docs/architecture.md
* https://www.reddit.com/r/Anki/comments/961cj8/documentation_for_creating_addons/
* https://github.com/users/Erlemar/projects/1/views/1?filterQuery=-status%3ADone
*

    * Kindle Mate - an awesome app, but it works for Windows only;
    * Several repositories on GitHub, requiring installing them;
    * Anki addon - great
    * flashcards
