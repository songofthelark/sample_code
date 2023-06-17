    
# Command line Wordle solver
    
At each prompt you can exclude letters, or enter letters that wordle says are present in
a different position, or the pattern of the letters you do know.

Enter ! followed by letters to exclude words containing those letters, e.g. !abc

Enter ? and letters for letters that are there but you don't know the position of e.g. ?def

Otherwise enter the "mask" pattern of the letters you do know, with dots as the unknown letters
for example: 

    ..a.. (matches beach, brang, etc)
    sh... (matches shoot, shire etc)

Excluded and unknown position letters are persisted across guesses

You get a list words back with scores, try a word with a high ranking.

Enter "quit" to quit 
