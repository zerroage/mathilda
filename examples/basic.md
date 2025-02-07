# Basic math

1. Open a new tab in Sublime Text editor
2. Copy and paste the following code into the editor
3. Press `Ctrl+Shift+P` and select _Set syntax: Mathilda_ in the menu
4. Press `F5`

```
#Basic math

1 + 2
1/9
Ans ** 2
pi * 5**2
1e6 + 1e7

#Basic complex math

; Imaginable part should be suffixed with 'j' symbol
1 + 2j
Ans / 2

#Math functions

; All python built-in math functions are supported (see https://docs.python.org/3.6/library/math.html)

log10(100)
sin(pi/2)
degrees(pi)
27! ; or factorial(27)

#Percent arithmetic

100 + 17%
117 - 17%
25 * 20%
1 / 10% ; 10% of what number will be 1?

#Rational arithmetic

; Rationals can be represented in the a:b form
1:2

; Basic arithmetic operations are supported
Ans + 3:8
Ans * 2

; Convert decimal value to rational
::.125
::3.14159265358979323
pi -  3126535/995207 

1:3 + 1:3**2 + 1:3**3 + 1:3**4

; Back to decimals
Ans + 0.0
```